
"""Search Yandex Market with GigaChat API v2 web search.

GigaChat discovers URLs. The Yandex parser verifies product data.
No invented prices, images or sizes.
"""

import asyncio
import html
import logging
import re
import uuid
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.core.config import settings
from app.services.marketplaces.yandex_market import (
    YandexMarketMarketplace,
)

log = logging.getLogger(__name__)

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v2/chat/completions"
ALLOWED_HOSTS = {
    "market.yandex.ru",
    "www.market.yandex.ru",
}


def valid_card_url(raw):
    if not isinstance(raw, str):
        return None

    raw = html.unescape(raw.strip()).rstrip(".,;")
    raw = raw.replace("\\/", "/")

    try:
        parts = urlsplit(raw)
    except ValueError:
        return None

    if parts.scheme != "https":
        return None

    if (parts.hostname or "").lower() not in ALLOWED_HOSTS:
        return None

    if parts.username or parts.password or parts.port:
        return None

    if not (
        parts.path.startswith("/card/")
        or parts.path.startswith("/product/")
    ):
        return None

    return urlunsplit((
        "https",
        parts.hostname,
        parts.path,
        "",
        "",
    ))


def extract_links(payload):
    texts = []

    def visit(obj):
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
        elif isinstance(obj, dict):
            for value in obj.values():
                visit(value)

    visit(payload)

    combined = html.unescape("\n".join(texts))
    combined = combined.replace("\\/", "/")

    candidates = re.findall(
        r'https://[^\s<>"\x27\]\)}]+',
        combined,
        flags=re.I,
    )

    result = []
    seen = set()

    for candidate in candidates:
        url = valid_card_url(candidate)

        if url and url not in seen:
            seen.add(url)
            result.append(url)

    return result


def product_name(source):
    return str(
        getattr(source, "name", "")
        or getattr(source, "title", "")
        or ""
    ).strip()[:180]


async def gigachat_search(source):
    credentials = settings.gigachat_credentials

    if not credentials:
        raise RuntimeError("gigachat_credentials_missing")

    name = product_name(source)

    if not name:
        raise RuntimeError("source_product_name_missing")

    prompt = (
        "Найди реальные похожие товары на Яндекс Маркете. "
        "Исходная вещь: " + name + ". "
        "Используй встроенный веб-поиск. "
        "Подбирай ту же категорию, назначение, "
        "похожий фасон, цвет и материал. "
        "Верни до 8 прямых HTTPS-ссылок на карточки "
        "market.yandex.ru/card/ или "
        "market.yandex.ru/product/. "
        "Не возвращай ссылки на поиск, рекламу, "
        "Wildberries, Ozon или другие магазины. "
        "Не придумывай ссылки и цены."
    )

    import os
    import ssl
    import certifi

    ssl_context = ssl.create_default_context(
        cafile=certifi.where()
    )

    # Дополнительный доверенный CA-файл для GigaChat.
    ca_path = os.environ.get("GIGACHAT_CA_BUNDLE", "").strip()
    if ca_path:
        ssl_context.load_verify_locations(cafile=ca_path)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(70.0, connect=12.0),
        follow_redirects=False,
        trust_env=True,
        verify=ssl_context,
    ) as client:

        # Existing GigaChat credentials are the OAuth
        # authorization key. Never print the key or token.
        auth_response = await client.post(
            OAUTH_URL,
            headers={
                "Authorization": "Basic " + credentials,
                "RqUID": str(uuid.uuid4()),
                "Content-Type":
                    "application/x-www-form-urlencoded",
            },
            data={"scope": "GIGACHAT_API_PERS"},
        )

        if auth_response.status_code != 200:
            raise RuntimeError(
                "gigachat_oauth_http_"
                + str(auth_response.status_code)
            )

        token = auth_response.json().get("access_token")

        if not token:
            raise RuntimeError("gigachat_oauth_token_missing")

        response = await client.post(
            CHAT_URL,
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
            json={
                "model": settings.gigachat_model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "tools": [
                    {
                        "type": "web_search",
                        "web_search": {
                            "indexes": ["web"]
                        },
                    }
                ],
                "stream": False,
            },
        )

        if response.status_code != 200:
            raise RuntimeError(
                "gigachat_v2_http_"
                + str(response.status_code)
            )

        links = extract_links(response.json())

        log.info(
            "gigachat_yandex_links_found count=%s",
            len(links),
        )

        return links[:8]


async def verified_search(source, normalize_offer):
    links = await gigachat_search(source)

    if not links:
        return []

    parser = YandexMarketMarketplace()
    results = []
    seen = set()

    for url in links:
        try:
            page = await asyncio.wait_for(
                parser._get_html(url),
                timeout=28,
            )

            product = parser._parse_product_card(page)

            if not isinstance(product, dict):
                continue

            # Do not trust a URL supplied by model output
            # without validating the actual product data.
            if not product.get("name"):
                continue

            if not product.get("price"):
                continue

            product["product_url"] = url

            if not product.get("category"):
                product["category"] = getattr(
                    source, "category", None
                )

            offer = normalize_offer(
                product,
                "yandex_market",
                source,
            )

            if not isinstance(offer, dict):
                continue

            offer_url = (
                offer.get("product_url")
                or offer.get("url")
                or url
            )

            if offer_url in seen:
                continue

            seen.add(offer_url)
            results.append(offer)

        except Exception as exc:
            log.warning(
                "gigachat_yandex_card_failed type=%s",
                type(exc).__name__,
            )

    log.info(
        "gigachat_yandex_verified count=%s",
        len(results),
    )

    return results
