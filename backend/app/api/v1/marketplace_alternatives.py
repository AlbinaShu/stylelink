
import asyncio
import logging
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.generation import Generation
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem
from app.models.user import User
from app.services.marketplaces.providers import (
    BhapiWbCatalog,
    CallBudget,
    PaidTransport,
)
from app.services.marketplaces.yandex_market import (
    YandexMarketMarketplace,
)


# STYLELINK_YM_PERSISTENT_MATCH_V1
import json
from sqlalchemy import text as _ym_sql_text

_YM_MATCH_TABLE = """
CREATE TABLE IF NOT EXISTS stylelink_yandex_matches (
    source_marketplace VARCHAR(50) NOT NULL,
    source_external_id BIGINT NOT NULL,
    offer_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_marketplace, source_external_id)
)
"""

async def _ym_source_key(source, session):
    if source.product_id is None:
        return None

    from app.models.product import Product

    product = await session.get(Product, source.product_id)

    if product is None or product.external_id is None:
        return None

    return (
        marketplace_name(product.marketplace),
        int(product.external_id),
    )

async def _ym_load_match(session, key):
    if key is None:
        return None

    await session.execute(_ym_sql_text(_YM_MATCH_TABLE))

    result = await session.execute(
        _ym_sql_text("""
            SELECT offer_json
            FROM stylelink_yandex_matches
            WHERE source_marketplace = :marketplace
              AND source_external_id = :external_id
        """),
        {"marketplace": key[0], "external_id": key[1]},
    )

    row = result.first()

    if row is None:
        return None

    offer = row[0]

    if not isinstance(offer, dict):
        return None

    if not direct_product_url(
        offer.get("url"), "yandex_market"
    ):
        return None

    return offer

async def _ym_save_match(session, key, offer):
    if key is None or not offer:
        return

    if not direct_product_url(
        offer.get("url"), "yandex_market"
    ):
        return

    await session.execute(_ym_sql_text(_YM_MATCH_TABLE))

    await session.execute(
        _ym_sql_text("""
            INSERT INTO stylelink_yandex_matches (
                source_marketplace,
                source_external_id,
                offer_json
            )
            VALUES (
                :marketplace,
                :external_id,
                CAST(:offer_json AS JSONB)
            )
            ON CONFLICT (
                source_marketplace,
                source_external_id
            ) DO UPDATE SET
                offer_json = EXCLUDED.offer_json,
                created_at = NOW()
        """),
        {
            "marketplace": key[0],
            "external_id": key[1],
            "offer_json": json.dumps(
                offer, ensure_ascii=False
            ),
        },
    )

    await session.commit()

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_HOSTS = {
    "wildberries": {"wildberries.ru", "www.wildberries.ru"},
    "yandex_market": {"market.yandex.ru"},
}

STOPWORDS = {
    "женский", "женская", "женские",
    "мужской", "мужская", "мужские",
    "для", "из", "на", "по", "и", "в",
    "the", "new",
}


def marketplace_name(value):
    value = str(value or "").strip().lower()
    if value in ("wb", "bhapi_wb", "wildberries"):
        return "wildberries"
    if value in ("yandex_market", "yandex market"):
        return "yandex_market"
    return value


def words(value):
    return {
        word for word in re.findall(
            r"[a-zа-яё0-9]+", str(value or "").casefold()
        )
        if len(word) > 1 and word not in STOPWORDS
    }


def similarity(a, b):
    left, right = words(a), words(b)
    if not left or not right:
        return 0.0
    jaccard = len(left & right) / len(left | right)
    sequence = SequenceMatcher(
        None, " ".join(sorted(left)), " ".join(sorted(right))
    ).ratio()
    return round(0.7 * jaccard + 0.3 * sequence, 3)


def direct_product_url(url, marketplace):
    if not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme != "https":
        return False
    if parsed.hostname not in ALLOWED_HOSTS.get(marketplace, set()):
        return False

    path = parsed.path.lower()
    if marketplace == "wildberries":
        return bool(re.fullmatch(
            r"/catalog/\d+/detail\.aspx", path
        ))
    if marketplace == "yandex_market":
        return "/card/" in path or "/product/" in path
    return False


def sizes_from_card(value):
    result = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, str):
            size = item.strip()
        elif isinstance(item, dict):
            size = next((
                str(item[key]).strip()
                for key in (
                    "name", "origName", "size",
                    "label", "tech_size", "techSize"
                )
                if item.get(key) is not None
            ), "")
        else:
            size = ""

        if size and size not in result:
            result.append(size)
    return result



# STYLELINK_ALTERNATIVE_SIZE_V1
_SIZE_ONE = re.compile(r"^(?:RU\s*)?(\d{2})$", re.I)
_SIZE_RANGE = re.compile(r"^(?:RU\s*)?(\d{2})\s*[-–—]\s*(\d{2})$", re.I)
_SIZE_HEIGHT = re.compile(
    r"^(?:RU\s*)?(\d{2})\s*[-–—/]\s*(1\d{2}|2\d{2})$", re.I
)
_SIZE_SHOE = re.compile(r"^(\d{2})\s*[-–—]\s*\d+[.,]\d+\s*см$", re.I)


def _alternative_size_numbers(value):
    value = str(value or "").strip()

    shoe = _SIZE_SHOE.fullmatch(value)
    if shoe:
        return {int(shoe.group(1))}

    height = _SIZE_HEIGHT.fullmatch(value)
    if height:
        return {int(height.group(1))}

    single = _SIZE_ONE.fullmatch(value)
    if single:
        number = int(single.group(1))
        return {number} if 30 <= number <= 70 else None

    pair = _SIZE_RANGE.fullmatch(value)
    if pair:
        low, high = map(int, pair.groups())
        if 30 <= low <= high <= 70 and high - low <= 8:
            return set(range(low, high + 1, 2))

    return None


def _alternative_size_status(recommended, available):
    if not recommended or not available:
        return "unknown"

    target = _alternative_size_numbers(recommended)
    if target is None:
        return "unknown"

    recognized = 0
    for label in available:
        values = _alternative_size_numbers(label)
        if values is None:
            continue
        recognized += 1
        if target & values:
            return "match"

    return "mismatch" if recognized == len(available) else "unknown"


def _alternative_offer_status(offer, source):
    return _alternative_size_status(
        getattr(source, "recommended_size", None),
        offer.get("available_sizes") or [],
    )


def _alternative_offer_rank(offer):
    priority = {"match": 2, "unknown": 1, "mismatch": 0}
    return (
        priority.get(offer.get("size_match_status"), 1),
        float(offer.get("match_score") or 0),
    )


def normalize_offer(product, marketplace, source):
    if not isinstance(product, dict):
        return None

    name = product.get("name")
    url = product.get("product_url")
    image = product.get("image_url")

    if not isinstance(name, str) or not name.strip():
        return None
    if not direct_product_url(url, marketplace):
        return None
    if not isinstance(image, str) or not image.startswith("https://"):
        image = None

    try:
        price = float(product.get("price"))
    except (TypeError, ValueError):
        return None

    if not 0 < price < 100000000:
        return None

    source_category = str(source.category or "").strip().lower()
    candidate_category = str(
        product.get("category") or ""
    ).strip().lower()

    if marketplace != "yandex_market":
        if (
            source_category and candidate_category
            and source_category != candidate_category
        ):
            return None

    score = similarity(source.name, name)

    source_brand = str(source.brand or "").strip().casefold()
    candidate_brand = str(
        product.get("brand") or ""
    ).strip().casefold()

    unknown = {
        "unknown", "без бренда",
        "не указан", "не определён", "не определен"
    }

    if (
        source_brand and candidate_brand
        and source_brand not in unknown
        and candidate_brand not in unknown
        and source_brand != candidate_brand
    ):
        score *= 0.7

    score = round(score, 3)
    if marketplace != "yandex_market":
        if score < 0.22:
            return None

    offer = {
        "marketplace": marketplace,
        "name": name,
        "brand": product.get("brand"),
        "price": price,
        "currency": "RUB",
        "image": image,
        "url": url,
        "available_sizes": sizes_from_card(
            product.get("sizes")
        ),
        "match_type": "similar",
        "match_score": score,
    }
    offer["size_match_status"] = _alternative_offer_status(offer, source)
    if offer["size_match_status"] == "mismatch":
        return None
    return offer



def yandex_queries(source):
    name = str(source.name or "").lower()

    groups = [
        (("жакет", "пиджак"), "жакет женский"),
        (("костюм",), "костюм женский"),
        (("платье",), "платье женское"),
        (("юбка",), "юбка женская"),
        (("брюк", "брюки"), "брюки женские"),
        (("джинс",), "джинсы женские"),
        (("рубашк",), "рубашка женская"),
        (("блуз",), "блузка женская"),
        (("кардиган",), "кардиган женский"),
        (("свитер", "джемпер"), "джемпер женский"),
        (("куртк",), "куртка женская"),
        (("пальто",), "пальто женское"),
        (("кроссовк",), "кроссовки женские"),
        (("туфл",), "туфли женские"),
        (("сумк",), "сумка женская"),
    ]

    base = next(
        (
            query
            for keywords, query in groups
            if any(word in name for word in keywords)
        ),
        None,
    )

    if base is None:
        base = {
            "dress": "платье женское",
            "top": "одежда женская",
            "bottom": "брюки женские",
            "outerwear": "куртка женская",
            "shoes": "обувь женская",
            "accessory": "аксессуары женские",
        }.get(str(source.category or ""), "одежда женская")

    attributes = [
        word for word in (
            "укороченный", "твидовый", "сиреневый",
            "черный", "белый", "бежевый",
            "приталенный", "миди", "макси",
        )
        if word in name
    ]

    queries = []
    if attributes:
        queries.append(base + " " + " ".join(attributes[:2]))
    queries.append(base)

    return list(dict.fromkeys(queries))


async def search_yandex_legacy(source):
    import html
    from urllib.parse import urljoin

    provider = YandexMarketMarketplace()
    found = []
    seen = set()
    errors = []

    for query in yandex_queries(source):
        if len(found) >= 8:
            break

        try:
            page = await asyncio.wait_for(
                provider._get_html(
                    provider.SEARCH_URL,
                    params={"text": query, "page": 1},
                ),
                timeout=30,
            )
            page = html.unescape(page)

            # Ссылки из HTML.
            hrefs = re.findall(
                r'href\\s*=\\s*["\\x27]([^"\\x27]+)["\\x27]',
                page,
                flags=re.I,
            )

            # Ссылки из встроенного JSON.
            hrefs += [
                value.replace("\\\\/", "/")
                for value in re.findall(
                    r'(?:https?:)?(?:\\\\/|/){2}'
                    r'market\\.yandex\\.ru'
                    r'(?:\\\\/|/)card'
                    r'(?:\\\\/|/)[^"\\s<>]+',
                    page,
                    flags=re.I,
                )
            ]

            urls = []
            for href in hrefs:
                href = href.replace("\\\\/", "/")
                url = urljoin(
                    provider.BASE_URL,
                    href.split("?", 1)[0],
                )

                if (
                    direct_product_url(url, "yandex_market")
                    and url not in seen
                ):
                    seen.add(url)
                    urls.append(url)

            logger.info(
                "yandex_alternatives_search "
                "query=%r html_length=%s urls=%s",
                query, len(page), len(urls),
            )

            for url in urls[:6]:
                try:
                    card_html = await asyncio.wait_for(
                        provider._get_html(url),
                        timeout=25,
                    )

                    product = provider._parse_product_card(
                        card_html
                    )

                    product["product_url"] = url

                    if not product.get("category"):
                        product["category"] = source.category

                    offer = normalize_offer(
                        product, "yandex_market", source
                    )

                    if offer is not None:
                        found.append(offer)

                except Exception as exc:
                    logger.warning(
                        "yandex_alternatives_card_failed "
                        "type=%s",
                        type(exc).__name__,
                    )

        except Exception as exc:
            errors.append(type(exc).__name__)
            logger.warning(
                "yandex_alternatives_query_failed "
                "query=%r type=%s",
                query, type(exc).__name__,
            )

    if not found and errors:
        raise RuntimeError(
            "Yandex search failed: " + ", ".join(errors)
        )

    logger.info(
        "yandex_alternatives_result found=%s",
        len(found),
    )

    return found


async def search_wildberries(source):
    token = settings.bhapi_wb_token.get_secret_value()
    if not token:
        return [], "not_configured"

    query = " ".join(
        str(part) for part in (source.brand, source.name)
        if part
    )[:160]

    async with httpx.AsyncClient(
        timeout=settings.marketplace_timeout_seconds,
        follow_redirects=False,
    ) as client:
        transport = PaidTransport(
            client, CallBudget(12)
        )
        provider = BhapiWbCatalog(
            transport,
            token,
            limit=5,
            pickup_point_id=settings.wb_pickup_point_id,
        )
        products = await provider.search_products(
            query,
            fallback_category=source.category,
        )

    offers = [
        offer
        for product in products
        if (offer := normalize_offer(
            product, "wildberries", source
        )) is not None
    ]
    return offers, "ok"


@router.get("/outfit-items/{item_id}/alternatives")
async def get_marketplace_alternatives(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(OutfitItem)
        .join(Outfit, Outfit.id == OutfitItem.outfit_id)
        .join(
            Generation,
            Generation.id == Outfit.generation_id,
        )
        .where(
            OutfitItem.id == item_id,
            Generation.user_id == current_user.id,
        )
    )

    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Outfit item not found",
        )

    primary = marketplace_name(source.marketplace)
    offers = []
    statuses = {}

    if primary != "yandex_market":
        try:
            ym_key = await _ym_source_key(source, session)
            cached = await _ym_load_match(session, ym_key)

            if (
                cached is not None
                and _alternative_offer_status(cached, source) != "mismatch"
            ):
                cached = dict(cached)
                cached["size_match_status"] = _alternative_offer_status(
                    cached, source
                )
                found = [cached]
                logger.info(
                    "STYLELINK_YM_PERSISTENT_MATCH_V1 hit item=%s",
                    source.id,
                )
            else:
                found = await asyncio.wait_for(
                    search_yandex(source),
                    timeout=85,
                )

                if found:
                    await _ym_save_match(
                        session, ym_key, found[0]
                    )

            offers.extend(found)
            statuses["yandex_market"] = (
                "ok" if found else "no_matches"
            )
        except Exception:
            logger.exception(
                "Yandex alternatives lookup failed"
            )
            statuses["yandex_market"] = "unavailable"

    if primary != "wildberries":
        try:
            found, status = await asyncio.wait_for(
                search_wildberries(source),
                timeout=50,
            )
            offers.extend(found)
            statuses["wildberries"] = (
                status if status != "ok"
                else ("ok" if found else "no_matches")
            )
        except Exception:
            logger.exception(
                "Wildberries alternatives lookup failed"
            )
            statuses["wildberries"] = "unavailable"

    seen = set()
    unique = []

    for offer in sorted(
        offers,
        key=_alternative_offer_rank,
        reverse=True,
    ):
        if offer["url"] in seen:
            continue
        seen.add(offer["url"])
        unique.append(offer)


    # STYLELINK_SIZE_FIX_V2
    # Получаем мерки исходной генерации для независимой проверки.
    generation_result = await session.execute(
        select(Generation)
        .join(Outfit, Outfit.generation_id == Generation.id)
        .where(
            Outfit.id == source.outfit_id,
            Generation.user_id == current_user.id,
        )
    )
    source_generation = generation_result.scalar_one_or_none()

    target_recommended_size = None

    if source_generation is not None:
        from app.services.size_recommendation_service import (
            SizeRecommendationService,
        )

        if source.category not in {"accessory", "shoes"}:
            target_recommended_size = (
                SizeRecommendationService.recommend_size(
                    available_sizes=[
                        str(n) for n in range(36, 72, 2)
                    ],
                    category=source.category,
                    gender=source_generation.gender,
                    chest=source_generation.chest,
                    waist=source_generation.waist,
                    hips=source_generation.hips,
                )
            )

    if target_recommended_size is None:
        target_recommended_size = source.recommended_size

    checked_offers = []

    # STYLELINK_UNIVERSAL_SIZE_FILTER_V1
    from app.services.size_recommendation_service import (
        SizeRecommendationService,
    )

    source_category = (source.category or "").lower()
    is_shoes = source_category in {
        "shoes", "shoe", "footwear", "обувь"
    }
    is_accessory = source_category in {
        "accessory", "accessories", "аксессуары"
    }

    if source_generation is not None and is_shoes:
        profile_shoe_size = getattr(
            source_generation, "shoe_size", None
        )
        required_size = (
            str(profile_shoe_size).removesuffix(".0")
            if profile_shoe_size is not None
            else None
        )
    elif is_accessory:
        required_size = None
    else:
        required_size = target_recommended_size

    for offer in unique:
        available = offer.get("available_sizes") or []

        if source_generation is not None:
            selected = SizeRecommendationService.recommend_for_offer(
                available_sizes=available,
                category=source.category,
                gender=source_generation.gender,
                chest=source_generation.chest,
                waist=source_generation.waist,
                hips=source_generation.hips,
                shoe_size=getattr(
                    source_generation, "shoe_size", None
                ),
            )
        else:
            selected = SizeRecommendationService.select_available_size(
                required_size, available
            )

        # Если размер пользователя известен, предложение
        # без подтвержденного совпадения не показываем.
        if required_size is not None and selected is None:
            continue

        checked_offer = dict(offer)
        checked_offer["recommended_size"] = selected
        checked_offer["size_match_status"] = (
            "match" if selected is not None else "unknown"
        )
        checked_offers.append(checked_offer)

    unique = checked_offers

    return {
        "source_marketplace": primary,
        "offers": unique[:8],
        "marketplace_status": statuses,
    }


# STYLELINK_GIGACHAT_HTTP_V2


# AI-стилист: поисковые запросы и ранжирование через GigaChat API v1.
# Фактические данные товаров получаем только из парсера Яндекс Маркета.
async def search_yandex(source):
    """
    Единый быстрый поиск.

    Использует карточки первого прохода.
    Не запускает второй полный поиск GigaChat.
    """
    import asyncio
    import logging

    from app.services.marketplaces.exact_product_match import (
        search_exact_products,
    )

    log = logging.getLogger(__name__)


    # STYLELINK_YM_ITEM_TRACE_V1
    trace_item_id = getattr(source, "id", None)
    trace_raw = getattr(source, "raw_data", None)
    trace_wb_id = None

    if isinstance(trace_raw, dict):
        trace_wb_id = (
            trace_raw.get("nm_id")
            or trace_raw.get("nmId")
            or trace_raw.get("product_id")
        )

    log.info(
        "STYLELINK_YM_TRACE item_id=%s wb_id=%s event=start",
        trace_item_id,
        trace_wb_id,
    )

    result = await search_exact_products(source)
    log.info(
        "STYLELINK_YM_TRACE item_id=%s wb_id=%s "
        "event=search_done exact=%s candidates=%s",
        trace_item_id,
        trace_wb_id,
        len(result.get("exact", [])),
        len(result.get("candidates", [])),
    )


    offers = []
    seen = set()

    for verified, products in (
        (True, result.get("exact", [])),
        (False, result.get("candidates", [])),
    ):
        for product in products:
            try:
                offer = normalize_offer(
                    product, "yandex_market", source
                )

                if offer is None:
                    continue

                url = offer.get("url")
                if not url or url in seen:
                    continue

                seen.add(url)

                if verified:
                    offer["match_type"] = "exact"
                    offer["match_score"] = 1.0
                    offer["exact_match_verified"] = True
                    offer["exact_match_reason"] = (
                        product.get("exact_match_reason")
                    )
                else:
                    offer["match_type"] = "similar"
                    offer["exact_match_verified"] = False

                offers.append(offer)

            except Exception as exc:
                log.warning(
                    "yandex_offer_error type=%s",
                    type(exc).__name__,
                )

    log.info(
        "yandex_fast_offers count=%s",
        len(offers),
    )

    from app.services.marketplaces.gigachat_vision_match import rank_offers_vision
    offers = await rank_offers_vision(source, offers)
    log.info(
        "STYLELINK_YM_TRACE item_id=%s wb_id=%s "
        "event=vision_done selected=%s",
        trace_item_id,
        trace_wb_id,
        len(offers),
    )


    # STYLELINK_YM_SEARCH_COLOR_V1
    # Если первый проход ничего не подтвердил, пробуем другие запросы.
    if not offers:
        log.info("yandex_retry reason=no_verified_offer")
        extra = await search_exact_products(source, query_offset=2)
        log.info(
            "STYLELINK_YM_TRACE item_id=%s wb_id=%s "
            "event=retry_search_done exact=%s candidates=%s",
            trace_item_id,
            trace_wb_id,
            len(extra.get("exact", [])),
            len(extra.get("candidates", [])),
        )

        retry_offers = []
        retry_seen = set(seen)

        for verified, products in (
            (True, extra.get("exact", [])),
            (False, extra.get("candidates", [])),
        ):
            for product in products:
                try:
                    offer = normalize_offer(
                        product, "yandex_market", source
                    )
                    if not offer:
                        continue

                    url = offer.get("url")
                    if not url or url in retry_seen:
                        continue
                    retry_seen.add(url)

                    if verified:
                        offer["match_type"] = "exact"
                        offer["match_score"] = 1.0
                        offer["exact_match_verified"] = True
                        offer["exact_match_reason"] = product.get(
                            "exact_match_reason"
                        )
                    else:
                        offer["match_type"] = "similar"
                        offer["exact_match_verified"] = False

                    retry_offers.append(offer)
                except Exception as exc:
                    log.warning(
                        "yandex_retry_offer_error type=%s",
                        type(exc).__name__,
                    )

        if retry_offers:
            offers = await rank_offers_vision(source, retry_offers)

        log.info(
            "yandex_retry_result candidates=%s selected=%s",
            len(retry_offers),
            len(offers),
        )


    for trace_offer in offers[:1]:
        log.info(
            "STYLELINK_YM_TRACE item_id=%s wb_id=%s "
            "event=final url=%s score=%s match_type=%s",
            trace_item_id,
            trace_wb_id,
            trace_offer.get("url"),
            trace_offer.get("match_score"),
            trace_offer.get("match_type"),
        )

    if not offers:
        log.info(
            "STYLELINK_YM_TRACE item_id=%s wb_id=%s event=final_empty",
            trace_item_id,
            trace_wb_id,
        )

    return offers[:1]  # STYLELINK_VISION_BEST_AUTO_V1

