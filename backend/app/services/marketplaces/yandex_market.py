import asyncio
import html
import json
import random
import re
import time
from typing import Any

import requests

from app.services.marketplaces.base import MarketplaceService


class YandexMarketMarketplace(MarketplaceService):
    MARKETPLACE = "yandex_market"
    BASE_URL = "https://market.yandex.ru"
    SEARCH_URL = "https://market.yandex.ru/search"

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )

    # Максимум 3 HTTP-запроса одновременно.
    MAX_CONCURRENT_REQUESTS = 3

    # Минимальный интервал между стартами HTTP-запросов.
    MIN_REQUEST_INTERVAL = 0.5

    # Первый запрос + максимум 3 повторные попытки.
    MAX_RETRIES = 3

    # Начальная задержка для exponential backoff.
    RETRY_BASE_DELAY = 1.0

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(
            self.MAX_CONCURRENT_REQUESTS
        )

        # Lock нужен, чтобы несколько async-задач не прошли
        # rate limiter одновременно.
        self._rate_lock = asyncio.Lock()

        self._last_request_started_at = 0.0

    async def _wait_for_rate_limit(self) -> None:
        """
        Не позволяет новым HTTP-запросам стартовать
        чаще MIN_REQUEST_INTERVAL.
        """

        async with self._rate_lock:
            now = time.monotonic()

            elapsed = now - self._last_request_started_at
            wait_time = self.MIN_REQUEST_INTERVAL - elapsed

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            self._last_request_started_at = time.monotonic()

    async def _get_html(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Получает HTML.

        Защита:
        - максимум 3 одновременных запроса;
        - минимальный интервал между запросами;
        - timeout;
        - retry сетевых ошибок;
        - retry 429;
        - retry 5xx;
        - exponential backoff + jitter.
        """

        async with self._semaphore:
            for attempt in range(self.MAX_RETRIES + 1):
                await self._wait_for_rate_limit()

                try:
                    response = await asyncio.to_thread(
                        requests.get,
                        url,
                        params=params,
                        headers={
                            "User-Agent": self.USER_AGENT,
                            "Accept-Language": "ru-RU,ru;q=0.9",
                        },
                        timeout=15,
                    )

                except requests.RequestException:
                    if attempt >= self.MAX_RETRIES:
                        raise

                    delay = (
                        self.RETRY_BASE_DELAY * (2 ** attempt)
                        + random.uniform(0, 0.5)
                    )

                    await asyncio.sleep(delay)
                    continue

                # Успешный HTTP-ответ.
                if response.status_code < 400:
                    return response.text

                # Too Many Requests.
                if response.status_code == 429:
                    if attempt >= self.MAX_RETRIES:
                        response.raise_for_status()

                    retry_after = response.headers.get("Retry-After")

                    try:
                        delay = (
                            float(retry_after)
                            if retry_after
                            else None
                        )
                    except ValueError:
                        delay = None

                    if delay is None:
                        delay = (
                            self.RETRY_BASE_DELAY * (2 ** attempt)
                            + random.uniform(0, 0.5)
                        )

                    await asyncio.sleep(delay)
                    continue

                # Временная ошибка сервера.
                if 500 <= response.status_code < 600:
                    if attempt >= self.MAX_RETRIES:
                        response.raise_for_status()

                    delay = (
                        self.RETRY_BASE_DELAY * (2 ** attempt)
                        + random.uniform(0, 0.5)
                    )

                    await asyncio.sleep(delay)
                    continue

                # 400 / 403 / 404 и остальные ошибки
                # повторно не запрашиваем.
                response.raise_for_status()

            raise RuntimeError(
                "Yandex Market request failed after retries"
            )

    def _parse_product_card(
        self,
        html_text: str,
    ) -> dict[str, Any]:
        """
        Парсит HTML карточки товара.

        Возвращает данные, необходимые до FashionCLIP:
        - external_id (OSKU);
        - name;
        - price;
        - sizes;
        - image_url;
        - product_url.

        Связь size -> OSKU сохраняется в raw_data.
        """

        text = html.unescape(html_text)

        # -------------------------------------------------
        # 1. Основные данные товара из JSON-LD
        # -------------------------------------------------

        scripts = re.findall(
            r'<script[^>]+type="application/ld\+json"[^>]*>'
            r'(.*?)'
            r'</script>',
            text,
            re.S,
        )

        product: dict[str, Any] | None = None

        for raw in scripts:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            objects = (
                data
                if isinstance(data, list)
                else [data]
            )

            for obj in objects:
                if (
                    isinstance(obj, dict)
                    and obj.get("@type") == "Product"
                ):
                    product = obj
                    break

            if product is not None:
                break

        if product is None:
            raise ValueError(
                "Yandex Market Product JSON-LD not found"
            )

        offer = product.get("offers") or {}

        # -------------------------------------------------
        # 2. Доступные размеры
        # -------------------------------------------------

        variants: list[dict[str, Any]] = []

        # Способ 1:
        # некоторые карточки отдают размеры через bundleValue.
        for match in re.finditer(
            r'data-zone-name="bundleValue"',
            text,
        ):
            chunk = text[
                match.start():
                match.start() + 3000
            ]

            osku = re.search(
                r'"oskuId"\s*:\s*(\d+)',
                chunk,
            )

            size = re.search(
                r'Размер:\s*([^<]+)',
                chunk,
            )

            if not osku or not size:
                continue

            variant = {
                "size": size.group(1).strip(),
                "osku_id": int(osku.group(1)),
            }

            if variant not in variants:
                variants.append(variant)

        # Способ 2:
        # часть карточек отдаёт варианты размера через
        # filterValue с filterId=74155816.
        #
        # Выполняем fallback только если bundleValue
        # не дал размеров.
        if not variants:
            product_url_for_id = (
                (product.get("offers") or {}).get("url")
            )

            current_osku_match = re.search(
                r'/(\d+)(?:\?|$)',
                product_url_for_id or "",
            )

            current_osku = (
                int(current_osku_match.group(1))
                if current_osku_match
                else None
            )

            size_filter_pattern = re.compile(
                r'valueId="([^"]+)"'
                r'[^>]*filterId="74155816"'
                r'[^>]*value="([^"]+)"'
                r'[^>]*pageHref="([^"]*)"'
            )

            for _, size, href in size_filter_pattern.findall(text):
                osku_id = None

                # "#" означает текущий выбранный вариант.
                if href == "#":
                    osku_id = current_osku

                else:
                    osku_match = re.search(
                        r'/(\d+)(?:\?|$)',
                        href,
                    )

                    if osku_match:
                        osku_id = int(
                            osku_match.group(1)
                        )

                if osku_id is None:
                    continue

                variant = {
                    "size": size.strip(),
                    "osku_id": osku_id,
                }

                if variant not in variants:
                    variants.append(variant)

        # -------------------------------------------------
        # 3. URL и OSKU текущей карточки
        # -------------------------------------------------

        product_url = offer.get("url")

        osku_match = re.search(
            r'/(\d+)(?:\?|$)',
            product_url or "",
        )

        external_id = (
            int(osku_match.group(1))
            if osku_match
            else None
        )

        # -------------------------------------------------
        # 4. Нормализованный товар
        # -------------------------------------------------

        return {
            "marketplace": self.MARKETPLACE,
            "external_id": external_id,
            "name": product.get("name"),
            "price": offer.get("price"),
            "sizes": [
                variant["size"]
                for variant in variants
            ],
            "image_url": product.get("image"),
            "product_url": product_url,
            "raw_data": {
                "variants": variants,
            },
        }

    async def search_products(
        self,
        search_query: str,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Ищет товары на Яндекс Маркете и загружает
        подробные данные карточек.
        """

        # 1. Получаем HTML страницы поиска.
        search_html = await self._get_html(
            self.SEARCH_URL,
            params={
                "text": search_query,
                "page": page,
            },
        )

        search_html = html.unescape(search_html)

        # 2. Извлекаем ссылки на карточки.
        pattern = re.compile(
            r'href="([^"]*/card/[^"]*/\d+(?:\?[^"]*)?)"'
        )

        card_urls: list[str] = []
        seen: set[str] = set()

        for href in pattern.findall(search_html):
            # Query-параметры карточки нам здесь не нужны.
            href = href.split("?", 1)[0]

            if href.startswith("http"):
                url = href
            else:
                url = f"{self.BASE_URL}{href}"

            if url in seen:
                continue

            seen.add(url)
            card_urls.append(url)

        # Пока ограничиваем количество карточек,
        # чтобы не делать лишние запросы.
        card_urls = card_urls[:20]

        # 3. Загружаем и парсим одну карточку.
        async def load_product(
            url: str,
        ) -> dict[str, Any] | None:
            try:
                card_html = await self._get_html(url)

                product = self._parse_product_card(
                    card_html
                )

                # До FashionCLIP нам нужны эти поля.
                required_fields = (
                    "external_id",
                    "name",
                    "price",
                    "image_url",
                    "product_url",
                )

                if any(
                    product.get(field) is None
                    for field in required_fields
                ):
                    return None

                # До FashionCLIP товар без доступных размеров
                # нам не подходит.
                sizes = product.get("sizes") or []

                if not sizes:
                    return None

                # Один размер может встречаться у нескольких OSKU
                # (например, разные цвета). Для общего списка размеров
                # оставляем каждое значение только один раз.
                product["sizes"] = list(dict.fromkeys(sizes))

                return product

            except (
                requests.RequestException,
                ValueError,
            ):
                # Одна проблемная карточка
                # не должна ронять весь поиск.
                return None

        # 4. Карточки запускаем конкурентно.
        # Реальную нагрузку всё равно контролируют
        # Semaphore(3) и rate limiter внутри _get_html().
        results = await asyncio.gather(
            *(
                load_product(url)
                for url in card_urls
            )
        )

        # 5. Убираем карточки, которые не удалось получить.
        return [
            product
            for product in results
            if product is not None
        ]
