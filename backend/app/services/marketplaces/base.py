from abc import ABC, abstractmethod


class MarketplaceService(ABC):

    @abstractmethod
    async def search_products(
        self,
        search_query: str,
        page: int = 1,
        price_from: float | None = None,
        price_to: float | None = None,
        fallback_category: str | None = None,
    ) -> list[dict]:
        """
        Ищет товары на маркетплейсе.

        Возвращает товары в едином формате приложения.
        """
        raise NotImplementedError
