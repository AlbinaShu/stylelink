
"""Визуальное сравнение товаров через GigaChat API v1."""

import asyncio
import json
import logging
import re
from urllib.parse import urlparse

import httpx

from app.services.marketplaces.gigachat_yandex_stylist import Stylist

logger = logging.getLogger(__name__)

API = "https://api.giga.chat/v1"
MODEL = "GigaChat-2-Pro"

ALLOWED_IMAGE_DOMAINS = (
    "wbbasket.ru",
    "wb.ru",
    "wildberries.ru",
    "yandex.net",
    "yandex.ru",
    "yandex.com",
    "yandexcdn.com",
    "avatars.mds.yandex.net",
)

def safe_image_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        return None
    if not any(
        host == domain or host.endswith("." + domain)
        for domain in ALLOWED_IMAGE_DOMAINS
    ):
        return None
    return value

def get_image(obj):
    if isinstance(obj, dict):
        values = [
            obj.get("image"),
            obj.get("image_url"),
            obj.get("photo_url"),
            obj.get("thumbnail"),
        ]
    else:
        values = [
            getattr(obj, "image", None),
            getattr(obj, "image_url", None),
            getattr(obj, "photo_url", None),
            getattr(obj, "thumbnail", None),
        ]

    for value in values:
        if isinstance(value, dict):
            value = value.get("url")
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        result = safe_image_url(value)
        if result:
            return result
    return None

async def download_image(client, url):
    logger.info("vision_stage=download_start")
    response = await client.get(
        url,
        follow_redirects=False,
        timeout=httpx.Timeout(12.0, connect=10.0),
    )
    response.raise_for_status()
    data = response.content
    content_type = response.headers.get(
        "content-type", ""
    ).split(";")[0].lower()

    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise ValueError("unsupported_image_type")

    if not data or len(data) > 5_000_000:
        raise ValueError("invalid_image_size")

    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[content_type]

    if content_type == "image/webp":
        from io import BytesIO
        from PIL import Image

        with Image.open(BytesIO(data)) as img:
            output = BytesIO()
            img.convert("RGB").save(
                output, format="JPEG", quality=88
            )
            data = output.getvalue()

        content_type = "image/jpeg"
        extension = "jpg"

    logger.info(
        "vision_image_prepared mime=%s bytes=%s",
        content_type, len(data),
    )
    return data, content_type, extension

async def upload_image(client, token, data, mime, extension):
    logger.info("vision_stage=upload_start")
    response = await client.post(
        API + "/files",
        headers={"Authorization": "Bearer " + token},
        data={"purpose": "general"},
        files={
            "file": (
                "stylelink-image." + extension,
                data,
                mime,
            )
        },
        timeout=httpx.Timeout(15.0, connect=12.0),
    )
    response.raise_for_status()
    file_id = response.json().get("id")
    if not file_id:
        raise ValueError("missing_gigachat_file_id")
    return file_id

def parse_response(content):
    if not isinstance(content, str):
        return []

    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        return []

    data = json.loads(match.group())
    results = data.get("results", [])
    return results if isinstance(results, list) else []

async def compare_images(source_url, candidates):
    """
    Возвращает оценки только для реально проверенных изображений.
    Использует существующую авторизацию Stylist.
    """
    async with Stylist() as stylist:
        client = stylist.client

        # Не читаем и не печатаем секреты.
        # Stylist получает OAuth-токен при входе в контекст.
        # Не ищем его в заголовках HTTP-клиента.
        token = getattr(stylist, "token", None)

        if not isinstance(token, str) or not token.strip():
            raise RuntimeError("gigachat_oauth_token_missing")

        token = token.strip()

        source_data = await download_image(client, source_url)
        source_id = await upload_image(
            client, token, *source_data
        )

        messages = [{
            "role": "system",
            "content": (
                "Ты эксперт по визуальному сравнению одежды. "
                "Сравни изображения, а не названия товаров. "
                "Оцени цвет, принт, фасон, рукава, вырез, "
                "длину и характерные детали. "
                "Не объявляй товар идентичным только по фото. "
                "Ответь исключительно JSON."
            ),
        }, {
            "role": "user",
            "content": "ЭТАЛОН: исходный товар Wildberries.",
            "attachments": [source_id],
        }]

        uploaded = []

        for index, candidate in enumerate(candidates):
            url = get_image(candidate)
            if not url:
                continue
            try:
                data = await download_image(client, url)
                file_id = await upload_image(
                    client, token, *data
                )
            except Exception as exc:
                logger.warning(
                    "vision_candidate_image_error type=%s",
                    type(exc).__name__,
                )
                continue

            uploaded.append(index)
            messages.append({
                "role": "user",
                "content": f"КАНДИДАТ {index}: сравни с эталоном.",
                "attachments": [file_id],
            })

        if not uploaded:
            return {}

        messages.append({
            "role": "user",
            "content": (
                "Верни JSON вида "
                '{"results":[{"index":0,"score":90,'
                '"reason":"совпадают цвет, принт и силуэт","color_match":true}]}. '
                "Для каждого представленного кандидата дай "
                "визуальную оценку от 0 до 100. "
                "100 означает практически полное визуальное "
                "совпадение, НЕ доказанную идентичность. "
                "Для каждого кандидата обязательно верни color_match: "
                "true только если основной цвет одежды совпадает "
                "с эталоном; false если отличается или нельзя "
                "уверенно установить совпадение цвета. "
                "Не компенсируй другой цвет сходством фасона. "
                "Не оценивай кандидатов, фото которых нет. "
                "Индексы кандидатов: "
                + ", ".join(map(str, uploaded))
            ),
        })

        logger.info("vision_stage=chat_start")
        response = await client.post(
            API + "/chat/completions",
            headers={"Authorization": "Bearer " + token},
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.1,
                "stream": False,
            },
            timeout=httpx.Timeout(20.0, connect=12.0),
        )
        response.raise_for_status()

        choices = response.json().get("choices") or []
        if not choices:
            return {}

        content = choices[0].get(
            "message", {}
        ).get("content", "")

        scores = {}
        for item in parse_response(content):
            if not isinstance(item, dict):
                continue

            index = item.get("index")
            score = item.get("score")

            if type(index) is not int or index not in uploaded:
                continue
            if type(score) not in (int, float):
                continue
            if not 0 <= score <= 100:
                continue

            scores[index] = {
                "score": round(score / 100, 3),
                "reason": str(item.get("reason", ""))[:240],
                "color_match": item.get("color_match") is True,
            }

        return scores

async def rank_offers_vision(source, offers):
    """STYLELINK_VISION_BEST_AUTO_V1: проверяем кандидатов до выбора."""
    if not offers:
        return []

    exact = [
        offer for offer in offers
        if offer.get("match_type") == "exact"
        and offer.get("exact_match_verified") is True
    ]
    if exact:
        return sorted(
            exact,
            key=lambda offer: offer.get("match_score", 0),
            reverse=True,
        )[:1]

    source_url = get_image(source)
    if not source_url:
        logger.warning("vision_source_image_missing")
        return []

    candidates = [
        offer for offer in offers
        if get_image(offer)
        and offer.get("match_type") != "exact"
    ][:8]

    if not candidates:
        logger.warning("vision_candidates_images_missing")
        return []

    logger.info(
        "vision_candidates_start count=%s",
        len(candidates),
    )

    try:
        scores = await asyncio.wait_for(
            compare_images(source_url, candidates),
            timeout=60,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "vision_http_error status=%s path=%s",
            exc.response.status_code,
            exc.request.url.path,
        )
        return []
    except Exception as exc:
        logger.warning(
            "vision_unavailable type=%s",
            type(exc).__name__,
        )
        return []

    verified = []

    for index, result in scores.items():
        if type(index) is not int or not 0 <= index < len(candidates):
            continue
        if not isinstance(result, dict):
            continue

        score = result.get("score")
        if type(score) not in (int, float) or not 0 <= score <= 1:
            continue

        # STYLELINK_YM_SEARCH_COLOR_V1
        if result.get("color_match") is not True:
            logger.info(
                "vision_candidate_rejected reason=color_not_confirmed index=%s",
                index,
            )
            continue

        offer = dict(candidates[index])
        offer["match_score"] = score
        offer["ai_similarity_score"] = score
        offer["ai_reason"] = result.get("reason", "")
        offer["vision_verified"] = True
        verified.append(offer)

    verified.sort(
        key=lambda offer: offer["match_score"],
        reverse=True,
    )

    # Не показываем слабое совпадение как лучшую альтернативу.
    best = [
        offer for offer in verified
        if offer["match_score"] >= 0.65
    ][:1]

    logger.info(
        "vision_candidates_result checked=%s scored=%s selected=%s",
        len(candidates),
        len(verified),
        len(best),
    )

    return best
