from uuid import UUID

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.generation import Generation
from app.models.generation_search_item import GenerationSearchItem
from app.services.gigachat import GigaChatService
from app.services.marketplaces.yandex_market import YandexMarketMarketplace
from app.services.product_service import ProductService


class GenerationPipeline:
    async def run(self, generation_id: UUID) -> None:
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Generation).where(
                        Generation.id == generation_id
                    )
                )
                generation = result.scalar_one_or_none()

                if generation is None:
                    return

                # 1. GigaChat формирует поисковые запросы
                generation.status = "generating_queries"
                await db.commit()

                gigachat = GigaChatService()
                generated_items = gigachat.generate_search_items(generation)

                search_items: list[GenerationSearchItem] = []

                for item in generated_items.items:
                    search_item = GenerationSearchItem(
                        generation_id=generation.id,
                        item_type=item.item_type,
                        search_query=item.search_query,
                    )
                    db.add(search_item)
                    search_items.append(search_item)

                await db.flush()

                # 2. Ищем товары на Яндекс Маркете
                generation.status = "searching_products"
                await db.commit()

                marketplace = YandexMarketMarketplace()
                product_service = ProductService()

                for search_item in search_items:
                    products = await marketplace.search_products(
                        search_item.search_query
                    )

                    await product_service.save_search_products(
                        db=db,
                        search_item=search_item,
                        products=products,
                    )

                # Пока ML-этапов ещё нет, считаем текущую часть завершённой
                generation.status = "completed"
                await db.commit()

            except Exception:
                await db.rollback()

                result = await db.execute(
                    select(Generation).where(
                        Generation.id == generation_id
                    )
                )
                generation = result.scalar_one_or_none()

                if generation is not None:
                    generation.status = "failed"
                    await db.commit()

                raise
