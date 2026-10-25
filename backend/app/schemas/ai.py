from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    item_type: str = Field(
        description="Конкретный тип товара, который нужно найти"
    )
    category: str = Field(
        description=(
            "Категория товара для FashionCLIP: "
            "top, bottom, dress, shoes, outerwear или accessory"
        )
    )
    search_query: str = Field(
        description="Поисковый запрос для Яндекс Маркета"
    )


class SearchItems(BaseModel):
    items: list[SearchItem]
