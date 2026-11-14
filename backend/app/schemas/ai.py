from typing import Literal
from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    item_type: str = Field(
        description="Конкретный тип товара, который нужно найти"
    )
    category: Literal['top', 'bottom', 'dress', 'shoes', 'outerwear', 'accessory'] = Field(
        description=(
            "Категория товара для FashionCLIP: "
            "top, bottom, dress, shoes, outerwear или accessory"
        )
    )
    search_query: str = Field(
        description="Поисковый запрос для маркетплейса"
    )


class SearchItems(BaseModel):
    items: list[SearchItem] = Field(min_length=1, max_length=6)
