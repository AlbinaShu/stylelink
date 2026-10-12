import asyncio
import html
import json
import random
import re
import time
from typing import Any

import requests

from app.services.marketplaces.base import MarketplaceService


class YandexMarketAccessBlocked(RuntimeError):
    pass


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
                    body = response.content.decode("utf-8", errors="replace")
                    if "Вы не робот?" in body[:5000]:
                        raise YandexMarketAccessBlocked(
                            "Yandex Market requested a CAPTCHA for a product card"
                        )
                    return body

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

    @staticmethod
    def _normalize_category(
        name: str | None,
    ) -> str | None:
        """
        Приводит название товара к одной из категорий,
        используемых FashionCLIP.

        Возможные значения:
        - top
        - bottom
        - dress
        - shoes
        - outerwear
        - accessory
        """

        if not name:
            return None

        value = name.lower()

        # Более специфичные категории должны проверяться раньше.

        categories: dict[str, tuple[str, ...]] = {
            "dress": (
                "платье",
                "сарафан",
            ),
            "outerwear": (
                "куртка",
                "пальто",
                "пуховик",
                "тренч",
                "ветровка",
                "бомбер",
                "шуба",
                "дубленка",
                "дублёнка",
                "плащ",
            ),
            "shoes": (
                "кроссовки",
                "кеды",
                "ботинки",
                "полуботинки",
                "туфли",
                "сапоги",
                "ботильоны",
                "лоферы",
                "мокасины",
                "босоножки",
                "сандалии",
                "тапочки",
                "обувь",
            ),
            "bottom": (
                "джинсы",
                "брюки",
                "штаны",
                "юбка",
                "шорты",
                "легинсы",
                "лосины",
            ),
            "top": (
                "футболка",
                "рубашка",
                "блузка",
                "блуза",
                "свитер",
                "свитшот",
                "худи",
                "лонгслив",
                "топ",
                "водолазка",
                "джемпер",
                "кардиган",
                "поло",
                "майка",
                "толстовка",
            ),
            "accessory": (
                "сумка",
                "рюкзак",
                "ремень",
                "шарф",
                "палантин",
                "шапка",
                "кепка",
                "панама",
                "очки",
                "перчатки",
                "варежки",
                "аксессуар",
            ),
        }

        for category, keywords in categories.items():
            if any(keyword in value for keyword in keywords):
                return category

        return None

    @staticmethod
    def _extract_image_url(
        product: dict[str, Any],
    ) -> str | None:
        """
        JSON-LD image может быть:
        - строкой;
        - списком;
        - объектом с полем url.

        FashionCLIP нужен один URL изображения.
        """

        image = product.get("image")

        if isinstance(image, str):
            return image

        if isinstance(image, list):
            for item in image:
                if isinstance(item, str) and item:
                    return item

                if isinstance(item, dict):
                    url = item.get("url")

                    if isinstance(url, str) and url:
                        return url

            return None

        if isinstance(image, dict):
            url = image.get("url")

            if isinstance(url, str):
                return url

        return None

    @staticmethod
    def _extract_colors(
        product: dict[str, Any],
    ) -> list[str] | None:
        """
        Пытается получить цвет из JSON-LD Product.

        Поле optional: если цвет отсутствует,
        возвращаем None.
        """

        color = product.get("color")

        if isinstance(color, str):
            color = color.strip()

            if color:
                return [color]

        if isinstance(color, list):
            colors = [
                str(item).strip()
                for item in color
                if str(item).strip()
            ]

            if colors:
                return list(dict.fromkeys(colors))

        return None

    def _parse_product_card(
        self,
        html_text: str,
    ) -> dict[str, Any]:
        """
        Парсит HTML карточки товара.

        Возвращает данные товара, необходимые Backend:

        - external_id;
        - name;
        - category;
        - description;
        - price;
        - sizes;
        - image_url;
        - product_url;
        - colors.

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

        # Иногда offers может быть массивом.
        if isinstance(offer, list):
            offer = (
                offer[0]
                if offer and isinstance(offer[0], dict)
                else {}
            )

        if not isinstance(offer, dict):
            offer = {}

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
                if isinstance(product.get("offers"), dict)
                else offer.get("url")
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
        # 4. Данные для FashionCLIP
        # -------------------------------------------------

        name = product.get("name")

        description = product.get("description")

        if not isinstance(description, str):
            description = None

        if description:
            description = description.strip() or None

        image_url = self._extract_image_url(product)
        colors = self._extract_colors(product)

        category = self._normalize_category(
            name if isinstance(name, str) else None
        )

        # -------------------------------------------------
        # 5. Нормализованный товар
        # -------------------------------------------------

        return {
            "marketplace": self.MARKETPLACE,
            "external_id": external_id,
            "name": name,
            "category": category,
            "description": description,
            "price": offer.get("price"),
            "sizes": [
                variant["size"]
                for variant in variants
            ],
            "image_url": image_url,
            "product_url": product_url,
            "colors": colors,
            "raw_data": {
                "variants": variants,
            },
        }


    @staticmethod
    def _extract_json_string(
        text: str,
        key: str,
    ) -> str | None:
        match = re.search(
            rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"',
            text,
        )

        if not match:
            return None

        try:
            return json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError:
            return match.group(1)

    @classmethod
    def _parse_fit_data(
        cls,
        html_text: str,
    ) -> dict[str, Any]:
        model_match = re.search(
            r'"modelId"\s*:\s*"?(\d+)"?',
            html_text,
        )

        model_id = (
            model_match.group(1)
            if model_match
            else None
        )

        review_ids = list(
            dict.fromkeys(
                re.findall(
                    r'"reviewId"\s*:\s*"?(\d+)"?',
                    html_text,
                )
            )
        )

        reviews: list[dict[str, Any]] = []

        for review_id in review_ids:
            positions = []

            for pattern in (
                f'"reviewId":"{review_id}"',
                f'"reviewId":{review_id}',
            ):
                position = html_text.find(pattern)

                if position != -1:
                    positions.append(position)

            if not positions:
                continue

            position = min(positions)

            chunk = html_text[
                max(0, position - 5000):
                min(len(html_text), position + 12000)
            ]

            parts = []

            for key in ("pro", "contra", "comment"):
                value = cls._extract_json_string(
                    chunk,
                    key,
                )

                if value and value.strip():
                    parts.append(value.strip())

            review_text = " ".join(
                dict.fromkeys(parts)
            ).strip()

            # Пустой отзыв нам действительно нечего
            # отправлять в текстовую ML-модель.
            if not review_text:
                continue

            size = None

            titles = re.findall(
                r'"title"\s*:\s*"((?:\\.|[^"\\])*)"',
                chunk,
            )

            for raw_title in titles:
                try:
                    title = json.loads(
                        f'"{raw_title}"'
                    )
                except json.JSONDecodeError:
                    title = raw_title

                size_match = re.search(
                    r'(?:размер|Размер)\s+'
                    r'([A-Za-zА-Яа-я0-9./-]+)',
                    title,
                )

                if size_match:
                    size = size_match.group(1)
                    break

            reviews.append(
                {
                    "text": review_text,
                    "size": size,
                }
            )

        return {
            "model_id": model_id,
            "reviews": reviews,
        }

    async def get_fit_data(
        self,
        product_url: str,
    ) -> dict[str, Any]:
        clean_url = (
            product_url
            .split("?", 1)[0]
            .rstrip("/")
        )

        if clean_url.endswith("/reviews"):
            reviews_url = clean_url
        else:
            reviews_url = f"{clean_url}/reviews"

        reviews_html = await self._get_html(
            reviews_url
        )

        return self._parse_fit_data(
            reviews_html
        )

    async def search_products(
        self,
        search_query: str,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Ищет товары на Яндекс Маркете и загружает
        подробные данные карточек.
        """

        # -------------------------------------------------
        # 1. Получаем HTML страницы поиска
        # -------------------------------------------------

        search_html = await self._get_html(
            self.SEARCH_URL,
            params={
                "text": search_query,
                "page": page,
            },
        )

        search_html = html.unescape(search_html)

        # -------------------------------------------------
        # 2. Извлекаем ссылки на карточки
        # -------------------------------------------------

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

        # Пока ограничиваем количество карточек
        # на один поисковый запрос.
        #
        # Общий лимит для FashionCLIP будет контролироваться
        # отдельно на уровне generation pipeline.
        card_urls = card_urls[:20]

        # -------------------------------------------------
        # 3. Загружаем и парсим одну карточку
        # -------------------------------------------------

        async def load_product(
            url: str,
        ) -> dict[str, Any] | None:
            try:
                card_html = await self._get_html(url)

                product = self._parse_product_card(
                    card_html
                )

                # Минимальный набор данных для дальнейшего
                # формирования FashionCLIP request.
                required_fields = (
                    "external_id",
                    "name",
                    "category",
                    "price",
                    "image_url",
                    "product_url",
                )

                if any(
                    product.get(field) is None
                    for field in required_fields
                ):
                    return None

                # Размеры пока сохраняем обязательными:
                # они понадобятся на следующих этапах pipeline.
                sizes = product.get("sizes") or []

                if not sizes:
                    return None

                # Один размер может встречаться у нескольких OSKU
                # (например, разные цвета). Для общего списка
                # размеров оставляем каждое значение один раз.
                product["sizes"] = list(
                    dict.fromkeys(sizes)
                )

                return product

            except (
                requests.RequestException,
                ValueError,
            ):
                # Одна проблемная карточка
                # не должна ронять весь поиск.
                return None

        # -------------------------------------------------
        # 4. Карточки запускаем конкурентно
        # -------------------------------------------------

        results = await asyncio.gather(
            *(
                load_product(url)
                for url in card_urls
            )
        )

        # -------------------------------------------------
        # 5. Убираем карточки, которые не удалось получить
        # -------------------------------------------------

        return [
            product
            for product in results
            if product is not None
        ]
