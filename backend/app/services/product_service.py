from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation_search_item import GenerationSearchItem
from app.models.generation_search_item_product import GenerationSearchItemProduct
from app.models.product import Product


class ProductService:
    MAX_PRODUCTS_PER_SEARCH_ITEM = 50

    async def save_search_products(
        self,
        db: AsyncSession,
        search_item: GenerationSearchItem,
        products: list[dict],
    ) -> list[Product]:
        """
        Сохраняет первые 50 уникальных товаров для одного поискового запроса.
        """

        # Убираем дубли внутри ответа маркетплейса,
        # сохраняя исходный порядок выдачи.
        unique_products: list[dict] = []
        seen: set[tuple[str, int]] = set()

        for product_data in products:
            marketplace = product_data.get("marketplace")
            external_id = product_data.get("external_id")

            if not marketplace or external_id is None:
                continue

            key = (marketplace, external_id)

            if key in seen:
                continue

            seen.add(key)
            unique_products.append(product_data)

            if len(unique_products) >= self.MAX_PRODUCTS_PER_SEARCH_ITEM:
                break

        saved_products: list[Product] = []

        for position, product_data in enumerate(unique_products, start=1):
            marketplace = product_data["marketplace"]
            external_id = product_data["external_id"]

            result = await db.execute(
                select(Product).where(
                    Product.marketplace == marketplace,
                    Product.external_id == external_id,
                )
            )

            product = result.scalar_one_or_none()

            if product is None:
                product = Product(
                    marketplace=marketplace,
                    external_id=external_id,
                )
                db.add(product)

            # Обновляем данные карточки при каждом новом поиске.
            product.imt_id = product_data.get("imt_id")
            product.name = product_data.get("name")
            product.brand = product_data.get("brand")
            product.product_url = product_data.get("product_url")
            product.image_url = product_data.get("image_url")
            product.supplier = product_data.get("supplier")
            product.supplier_id = product_data.get("supplier_id")
            product.price = product_data.get("price")
            product.rating = product_data.get("rating")
            product.review_rating = product_data.get("review_rating")
            product.feedbacks = product_data.get("feedbacks")
            product.subject_id = product_data.get("subject_id")
            product.subject_parent_id = product_data.get("subject_parent_id")
            product.colors = product_data.get("colors")
            product.sizes = product_data.get("sizes")
            product.raw_data = product_data.get("raw_data")

            # Нужен UUID нового Product перед созданием связи.
            await db.flush()

            link_result = await db.execute(
                select(GenerationSearchItemProduct).where(
                    GenerationSearchItemProduct.generation_search_item_id
                    == search_item.id,
                    GenerationSearchItemProduct.product_id == product.id,
                )
            )

            link = link_result.scalar_one_or_none()

            if link is None:
                link = GenerationSearchItemProduct(
                    generation_search_item_id=search_item.id,
                    product_id=product.id,
                    position=position,
                )
                db.add(link)
            else:
                link.position = position

            saved_products.append(product)

        await db.flush()

        return saved_products
