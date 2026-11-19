import asyncio
import json
import logging
import re
import ssl
import uuid
from pathlib import Path

import certifi
import httpx

from app.core.config import settings
from app.services.marketplaces.yandex_market import YandexMarketMarketplace

logger = logging.getLogger(__name__)

CATEGORIES = {
    "dress": "платье",
    "top": "верхняя часть одежды",
    "bottom": "брюки юбка или низ одежды",
    "shoes": "обувь",
    "outerwear": "верхняя одежда",
    "accessory": "аксессуар",
}


def get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def clean_text(value, limit=250):
    return str(value or "").strip()[:limit]


def parse_json(text):
    text = str(text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise ValueError("GigaChat не вернул JSON")


class Stylist:
    def __init__(self):
        self.token = None

    async def __aenter__(self):
        ca = Path.home() / ".config/stylelink/certs/russian_trusted_root_ca.pem"
        if not ca.is_file():
            raise RuntimeError("Не найден CA-сертификат GigaChat")

        context = ssl.create_default_context(cafile=certifi.where())
        context.load_verify_locations(cafile=str(ca))

        self.client = httpx.AsyncClient(
            verify=context,
            timeout=httpx.Timeout(45.0, connect=12.0),
            follow_redirects=True,
        )

        try:
            auth = await self.client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": "Basic " + settings.gigachat_credentials,
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
            )
            auth.raise_for_status()
            self.token = auth.json()["access_token"]
        except Exception:
            await self.client.aclose()
            raise

        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def ask_json(self, prompt):
        response = await self.client.post(
            "https://api.giga.chat/v1/chat/completions",
            headers={"Authorization": "Bearer " + self.token},
            json={
                "model": settings.gigachat_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты AI-стилист StyleLink. Анализируй только "
                            "переданные сведения о товарах. "
                            "Не выдумывай цены, размеры, ссылки и свойства. "
                            "Верни только корректный JSON без Markdown."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_json(content)


async def search_and_rank(source):
    name = clean_text(get_value(source, "name"))
    category = clean_text(get_value(source, "category"))
    description = clean_text(get_value(source, "description"), 500)
    color = get_value(source, "colors") or get_value(source, "color")
    price = get_value(source, "price")

    if not name:
        return []

    parser = YandexMarketMarketplace()

    async with Stylist() as stylist:
        plan = await stylist.ask_json(
            "Исходный товар Wildberries:\n"
            + json.dumps({
                "name": name,
                "category": category,
                "description": description,
                "color": color,
                "price": price,
            }, ensure_ascii=False, default=str)
            + "\nСоставь максимум 3 коротких поисковых запроса "
              "для Яндекс Маркета. Сохраняй тип вещи, цвет и фасон. "
              "Формат: {\"queries\": [\"...\", \"...\"]}"
        )

        queries = []
        for q in plan.get("queries", []):
            if isinstance(q, str) and 3 <= len(q.strip()) <= 100:
                queries.append(q.strip())

        queries = list(dict.fromkeys(queries))[:2]
        if not queries:
            queries = [name[:100]]

        logger.info("gigachat_stylist_queries count=%s", len(queries))

        products = []
        seen = set()

        for query in queries:
            try:
                found = await asyncio.wait_for(
                    parser.search_products(query, fallback_category=category or None),
                    timeout=100,
                )
            except Exception as exc:
                logger.warning(
                    "gigachat_stylist_parser_error type=%s",
                    type(exc).__name__,
                )
                continue

            for product in found or []:
                if not isinstance(product, dict):
                    continue

                url = product.get("product_url")
                title = product.get("name")
                cost = product.get("price")

                if not isinstance(url, str) or not url.startswith(
                    ("https://market.yandex.ru/card/",
                     "https://market.yandex.ru/product/")
                ):
                    continue

                if not title or cost is None or isinstance(cost, bool):
                    continue

                try:
                    if float(cost) <= 0:
                        continue
                except (TypeError, ValueError):
                    continue

                detected = product.get("category")
                if category and detected and detected != category:
                    continue

                if url in seen:
                    continue

                seen.add(url)
                products.append(product)

        logger.info(
            "gigachat_stylist_candidates count=%s", len(products)
        )

        if not products:
            return []

        candidates = []
        for i, product in enumerate(products[:24]):
            candidates.append({
                "id": i,
                "name": clean_text(product.get("name")),
                "description": clean_text(product.get("description"), 350),
                "brand": clean_text(product.get("brand"), 100),
                "category": product.get("category"),
                "colors": product.get("colors"),
                "price": product.get("price"),
                "sizes": product.get("sizes"),
            })

        try:
            ranking = await asyncio.wait_for(
                stylist.ask_json(
                "Сравни исходный товар с кандидатами Яндекс Маркета.\n"
                "Исходный товар: "
                + json.dumps({
                    "name": name,
                    "category": category,
                    "description": description,
                    "color": color,
                    "price": price,
                }, ensure_ascii=False, default=str)
                + "\nКандидаты: "
                + json.dumps(candidates, ensure_ascii=False, default=str)
                + "\nВыбери до 8 наиболее похожих товаров. "
                  "Учитывай тип вещи, цвет, фасон, стиль и цену. "
                  "Не утверждай совпадение свойств, если данных нет. "
                  "Формат JSON: "
                  "{\"ranked\": [{\"id\": 0, \"score\": 85, "
                  "\"reason\": \"Похожий фасон\"}]}. "
                  "score — целое число от 0 до 100."
            ),
                timeout=10,
            )
            ranked = ranking.get("ranked", [])
        except Exception as exc:
            logger.warning(
                "gigachat_stylist_ranking_error type=%s",
                type(exc).__name__,
            )
            ranked = []

        result = []
        selected = set()

        for item in ranked:
            if not isinstance(item, dict):
                continue

            idx = item.get("id")
            if type(idx) is not int or not 0 <= idx < len(candidates):
                continue
            if idx in selected:
                continue

            product = dict(products[idx])
            try:
                score = int(item.get("score", 0))
            except (TypeError, ValueError):
                score = 0

            product["ai_similarity_score"] = max(0, min(100, score))
            product["ai_reason"] = clean_text(item.get("reason"), 200)
            result.append(product)
            selected.add(idx)

            if len(result) >= 8:
                break

        if not result:
            result = products[:8]

        logger.info(
            "gigachat_stylist_selected count=%s", len(result)
        )
        return result
