import re

from gigachat import GigaChat

from app.core.config import settings
from app.models.generation import Generation
from app.schemas.ai import SearchItems



SEARCH_ITEMS_SYSTEM_PROMPT = """
Ты — AI-стилист.

Твоя задача — определить конкретные товары одежды и обуви,
которые нужно найти на Яндекс Маркете для формирования образа пользователя.

Правила:

1. Разбей задачу на отдельные конкретные товары.
2. Каждый товар должен быть самостоятельным поисковым запросом.
3. Учитывай пол, повод, стиль, сезон и бюджет пользователя.
4. Учитывай параметры фигуры пользователя при выборе подходящего
   типа одежды и кроя.
5. Параметры роста, веса, груди, талии и бёдер НЕ должны попадать
   в search_query.
6. Бюджет НЕ должен попадать в search_query.
7. Размеры конкретных товаров НЕ должны попадать в search_query.
8. Не вычисляй размер одежды или обуви пользователя.
9. search_query должен содержать только признаки самого товара:
   тип, назначение, пол, сезон, материал, цвет, крой и другие
   полезные характеристики.
10. Не добавляй в search_query служебные названия параметров,
    например "style", "season", "budget", "gender", "height", "weight".
11. Не придумывай идентификаторы товаров Маркета.
12. Не используй названия конкретных брендов, если пользователь их не просил.
13. Не добавляй название маркетплейса в search_query.
14. Не добавляй аксессуары или дополнительные товары без необходимости.
15. Не повторяй один и тот же тип товара.
16. item_type должен быть максимально конкретным названием товара.
17. Не используй слишком общие значения item_type:
    "одежда", "обувь", "аксессуары", "верхняя одежда", "низ".
18. Если search_query содержит конкретный товар, item_type должен называть
    именно этот товар. Например:
    "кроссовки мужские..." → item_type "кроссовки",
    "ботинки мужские..." → item_type "ботинки",
    "куртка мужская..." → item_type "куртка".
19. Выбирай только товары, необходимые для формирования запрошенного образа.
20. Для каждого товара обязательно укажи category.
21. category может иметь только одно из значений:
    "top", "bottom", "dress", "shoes", "outerwear", "accessory".
22. category — это общая категория товара для FashionCLIP,
    а item_type — конкретное название товара. Например:
    item_type "велосипедки" → category "bottom",
    item_type "джоггеры" → category "bottom",
    item_type "кюлоты" → category "bottom",
    item_type "спортивный топ" → category "top",
    item_type "кроссовки" → category "shoes".
"""


def clean_search_query(query: str) -> str:
    """Удаляет из поискового запроса служебные параметры."""

    # "style casual" -> "casual"
    query = re.sub(
        r"\bstyle\s+",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Бюджет: "15000 руб", "15000 рублей", "15000 ₽",
    # "бюджет 15000", "до 15000" и т.п.
    query = re.sub(
        r"\b(?:бюджет\s*(?:до\s*)?|до\s*)?"
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:₽|руб(?:лей|ля)?|р\.?)\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Если модель написала просто "бюджет 15000".
    query = re.sub(
        r"\bбюджет\s+\d+(?:[.,]\d+)?\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Параметры в сантиметрах.
    query = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*см\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Параметры тела.
    query = re.sub(
        r"\b(?:рост|вес|грудь|талия|бёдра|бедра)\s*"
        r"\d+(?:[.,]\d+)?\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Размеры: "размер 42", "размер L-M", "size 42-43".
    query = re.sub(
        r"\b(?:размер|size)\s*"
        r"[A-Za-zА-Яа-я0-9]+"
        r"(?:[-–][A-Za-zА-Яа-я0-9]+)?\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Название площадки.
    query = re.sub(
        r"\bWildberries\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    # Убираем лишние пробелы и знаки.
    query = re.sub(r"\s+", " ", query).strip(" ,.-")

    return query


class GigaChatService:
    def __init__(self):
        self.client = GigaChat(
            credentials=settings.gigachat_credentials,
            model=settings.gigachat_model,
            verify_ssl_certs=False,
        )

    def chat(self, prompt: str) -> str:
        response = self.client.chat(prompt)
        return response.choices[0].message.content

    def build_search_items_prompt(self, generation: Generation) -> str:
        return f"""
{SEARCH_ITEMS_SYSTEM_PROMPT}

Данные пользователя:

Повод: {generation.occasion or "не указан"}
Стиль: {generation.style or "не указан"}
Сезон: {generation.season or "не указан"}
Бюджет: {
    generation.budget
    if generation.budget is not None
    else "не указан"
} рублей
Пол: {generation.gender or "не указан"}

Параметры фигуры:
Рост: {
    generation.height
    if generation.height is not None
    else "не указан"
} см
Вес: {
    generation.weight
    if generation.weight is not None
    else "не указан"
} кг
Грудь: {
    generation.chest
    if generation.chest is not None
    else "не указано"
} см
Талия: {
    generation.waist
    if generation.waist is not None
    else "не указано"
} см
Бёдра: {
    generation.hips
    if generation.hips is not None
    else "не указано"
} см

Дополнительное пожелание:
{generation.prompt or "нет"}

Сформируй список конкретных товаров, необходимых для этого образа.
"""

    def parse_search_items(self, prompt: str) -> SearchItems:
        response = self.client.chat_parse(
            prompt,
            response_format=SearchItems,
            strict=True,
        )
        return response[1]

    def generate_search_items(self, generation: Generation) -> SearchItems:
        prompt = self.build_search_items_prompt(generation)
        result = self.parse_search_items(prompt)

        for item in result.items:
            item.search_query = clean_search_query(item.search_query)

        return result
