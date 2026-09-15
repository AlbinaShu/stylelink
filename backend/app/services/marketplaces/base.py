from abc import ABC, abstractmethod


class MarketplaceService(ABC):

    @abstractmethod
    async def search_products(
        self,
        search_query: str,
        page: int = 1,
    ) -> list[dict]:
        """
        Ищет товары на маркетплейсе.

        Возвращает товары в едином формате приложения.
        """
        raise NotImplementedError
