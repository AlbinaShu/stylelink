"""
StyleLink: поиск идентичных товаров между маркетплейсами.

Принципы:
- цены, размеры, ссылки — только из парсера;
- GigaChat генерирует запросы и оценивает сходство;
- модель не может самостоятельно подтвердить идентичность;
- точное совпадение требует надёжного идентификатора;
- при ошибке GigaChat сохраняется обычный поиск.
"""

import asyncio
import json
import logging
import re
from urllib.parse import urlparse

from app.services.marketplaces.yandex_market import (
    YandexMarketMarketplace,
)

logger = logging.getLogger(__name__)


def field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def text(value):
    return str(value or "").strip()


def normalized(value):
    return re.sub(
        r"[^a-zа-яё0-9]+",
        "",
        text(value).casefold(),
    )


def manufacturer_codes(value):
    """
    Ищет артикулы производителя в структурированных
    полях и текстовом описании.

    Не считает ID Wildberries и Яндекс Маркета
    одним и тем же артикулом производителя.
    """
    codes = set()

    if isinstance(value, dict):
        keys = (
            "vendor_code",
            "manufacturer_sku",
            "manufacturer_article",
            "article",
            "supplier_article",
            "sku",
            "model_number",
            "mpn",
        )

        for key in keys:
            raw = value.get(key)
            if isinstance(raw, (str, int)):
                candidate = normalized(raw)
                if len(candidate) >= 6:
                    codes.add(candidate)

        for key in ("description", "name"):
            raw = text(value.get(key))
            patterns = (
                r"(?:артикул производителя|артикул модели|"
                r"модель|арт\.)\s*[:№#]?\s*"
                r"([A-Za-zА-Яа-я0-9_-]{6,40})",
            )
            for pattern in patterns:
                for match in re.findall(
                    pattern, raw, flags=re.I
                ):
                    codes.add(normalized(match))

    return codes


def source_data(source):
    raw = field(source, "raw_data")
    if not isinstance(raw, dict):
        raw = {}

    return {
        "name": text(field(source, "name")),
        "brand": text(field(source, "brand")),
        "category": text(field(source, "category")),
        "description": text(field(source, "description"))[:600],
        "colors": field(source, "colors")
                  or field(source, "color"),
        "price": field(source, "price"),
        "product_url": field(source, "product_url")
                       or field(source, "url"),
        "vendor_code": field(source, "vendor_code")
                       or field(source, "supplier_article"),
        "manufacturer_sku": field(source, "manufacturer_sku"),
        "raw_data": raw,
    }


def candidate_data(product):
    return {
        "name": product.get("name"),
        "brand": product.get("brand"),
        "category": product.get("category"),
        "description": product.get("description"),
        "colors": product.get("colors"),
        "price": product.get("price"),
        "sizes": product.get("sizes"),
        "product_url": product.get("product_url"),
        "vendor_code": product.get("vendor_code"),
        "manufacturer_sku": product.get("manufacturer_sku"),
        "raw_data": product.get("raw_data"),
    }


def valid_yandex_product(product):
    if not isinstance(product, dict):
        return False

    url = product.get("product_url")
    name = product.get("name")
    price = product.get("price")

    if not isinstance(url, str):
        return False

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname not in (
            "market.yandex.ru",
            "www.market.yandex.ru",
        )
        or not parsed.path.startswith(
            ("/card/", "/product/")
        )
    ):
        return False

    if not isinstance(name, str) or not name.strip():
        return False

    try:
        if isinstance(price, bool) or float(price) <= 0:
            return False
    except (TypeError, ValueError):
        return False

    return True


def exact_evidence(source, product):
    """
    Проверка подтверждённого совпадения.

    AI-оценка не является доказательством.
    """
    original = source_data(source)
    candidate = candidate_data(product)

    source_brand = normalized(original["brand"])
    target_brand = normalized(candidate["brand"])

    if source_brand and target_brand:
        if source_brand != target_brand:
            return False, "different_brand"

    source_codes = manufacturer_codes(original)
    target_codes = manufacturer_codes(candidate)

    source_raw = original.get("raw_data")
    target_raw = candidate.get("raw_data")

    if isinstance(source_raw, dict):
        source_codes.update(manufacturer_codes(source_raw))

    if isinstance(target_raw, dict):
        target_codes.update(manufacturer_codes(target_raw))

    common = source_codes & target_codes

    if not common:
        return False, "manufacturer_code_not_confirmed"

    if not source_brand or not target_brand:
        return False, "brand_not_confirmed"

    source_category = normalized(original["category"])
    target_category = normalized(candidate["category"])

    if (
        source_category
        and target_category
        and source_category != target_category
    ):
        return False, "different_category"

    return True, "matching_brand_and_manufacturer_code"


def build_queries(source):
    data = source_data(source)
    queries = []

    brand = data["brand"]
    name = data["name"]

    codes = manufacturer_codes(data)

    raw = data.get("raw_data")
    if isinstance(raw, dict):
        codes.update(manufacturer_codes(raw))

    for code in sorted(codes):
        if brand:
            queries.append(f"{brand} {code}")
        queries.append(code)

    if brand and name:
        queries.append(f"{brand} {name}")

    if name:
        queries.append(name)

    return list(dict.fromkeys(
        q.strip()[:110]
        for q in queries
        if q and q.strip()
    ))[:5]


async def gigachat_queries(source):
    """
    Дополнительные запросы через существующий
    рабочий GigaChat API v1.

    Если GigaChat недоступен, используем
    обычные запросы.
    """
    try:
        from app.services.marketplaces.gigachat_yandex_stylist import (
            Stylist,
        )

        data = source_data(source)

        async with Stylist() as stylist:
            response = await asyncio.wait_for(
                stylist.ask_json(
                    "Ты ищешь ТОЧНО ТАКОЙ ЖЕ товар "
                    "на другом маркетплейсе.\n"
                    "Исходный товар:\n"
                    + json.dumps(
                        {
                            "name": data["name"],
                            "brand": data["brand"],
                            "category": data["category"],
                            "description": data["description"],
                            "colors": data["colors"],
                        },
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\nСоставь 2 точных поисковых запроса. "
                      "Сохрани бренд, цвет, фасон и принт. "
                      "Не выдумывай артикул производителя. "
                      "Верни JSON: "
                      '{"queries":["запрос 1","запрос 2"]}'
                ),
                timeout=18,
            )

        queries = response.get("queries", [])

        if not isinstance(queries, list):
            return []

        return [
            q.strip()[:110]
            for q in queries[:2]
            if isinstance(q, str) and q.strip()
        ]

    except Exception as exc:
        logger.warning(
            "exact_match_gigachat_error type=%s",
            type(exc).__name__,
        )
        return []


async def search_exact_products(source, query_offset=0):
    """
    Быстрый поиск реальных карточек Яндекс Маркета.

    Не запускает GigaChat до поиска и не делает
    повторных запросов ради ранжирования.

    Возвращает подтверждённые совпадения отдельно
    от остальных кандидатов.
    """
    import asyncio

    parser = YandexMarketMarketplace()
    queries = build_queries(source)

    # Максимум два запроса, чтобы уложиться
    # во внешний лимит API в 35 секунд.
    # STYLELINK_YM_SEARCH_COLOR_V1
    # Первый проход: 2 запроса; дополнительный: следующие 2.
    queries = queries[query_offset:query_offset + 2]

    logger.info(
        "exact_match_fast_queries count=%s",
        len(queries),
    )

    found = []
    seen = set()

    category = source_data(source)["category"] or None

    for query in queries:
        try:
            products = await asyncio.wait_for(
                parser.search_products(
                    query,
                    fallback_category=category,
                ),
                timeout=13,
            )
        except asyncio.TimeoutError:
            logger.warning("exact_match_query_timeout")
            continue
        except Exception as exc:
            logger.warning(
                "exact_match_query_error type=%s",
                type(exc).__name__,
            )
            continue

        for product in products or []:
            if not valid_yandex_product(product):
                continue

            url = product["product_url"].split("?", 1)[0]

            if url in seen:
                continue

            seen.add(url)
            found.append(product)

        if len(found) >= 16:
            break

    exact = []
    candidates = []

    for product in found:
        verified, reason = exact_evidence(source, product)

        item = dict(product)
        item["exact_match_verified"] = verified
        item["exact_match_reason"] = reason

        if verified:
            exact.append(item)
        else:
            candidates.append(item)

    logger.info(
        "exact_match_fast_result exact=%s candidates=%s",
        len(exact),
        len(candidates),
    )

    return {
        "exact": exact[:8],
        "candidates": candidates[:16],
    }
