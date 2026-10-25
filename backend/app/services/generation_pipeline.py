from uuid import UUID

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.generation import Generation
from app.models.generation_search_item import GenerationSearchItem
from app.models.generation_search_item_product import (
    GenerationSearchItemProduct,
)
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem
from app.models.product import Product
from app.models.profile import Profile
from app.schemas.fashion_clip import (
    FashionClipContext,
    FashionClipProduct,
    FashionClipRequest,
)
from app.schemas.size_shift import (
    SizeShiftProduct,
    SizeShiftRequest,
)
from app.services.gigachat import GigaChatService
from app.services.marketplaces.yandex_market import (
    YandexMarketMarketplace,
)
from app.services.ml.fashion_clip_client import FashionClipClient
from app.services.ml.size_shift_client import SizeShiftClient
from app.services.product_service import ProductService
from app.services.size_recommendation_service import SizeRecommendationService


class GenerationPipeline:
    MAX_FASHION_CLIP_PRODUCTS = 100

    async def run(self, generation_id: UUID) -> None:
        async with AsyncSessionLocal() as db:
            try:
                # -------------------------------------------------
                # 0. Получаем Generation
                # -------------------------------------------------

                result = await db.execute(
                    select(Generation).where(
                        Generation.id == generation_id
                    )
                )

                generation = result.scalar_one_or_none()

                if generation is None:
                    return

                # Профиль пользователя нужен Backend для рекомендации размера.
                profile_result = await db.execute(
                    select(Profile).where(
                        Profile.user_id == generation.user_id
                    )
                )
                profile = profile_result.scalar_one_or_none()

                # -------------------------------------------------
                # 1. GigaChat формирует поисковые запросы
                # -------------------------------------------------

                generation.status = "generating_queries"
                await db.commit()

                gigachat = GigaChatService()

                generated_items = gigachat.generate_search_items(
                    generation
                )

                search_items: list[GenerationSearchItem] = []

                for item in generated_items.items:
                    search_item = GenerationSearchItem(
                        generation_id=generation.id,
                        item_type=item.item_type,
                        category=item.category,
                        search_query=item.search_query,
                    )

                    db.add(search_item)
                    search_items.append(search_item)

                await db.flush()

                # -------------------------------------------------
                # 2. Ищем товары на Яндекс Маркете
                # -------------------------------------------------

                generation.status = "searching_products"
                await db.commit()

                marketplace = YandexMarketMarketplace()
                product_service = ProductService()

                # Распределяем бюджет по количеству элементов образа.
                #
                # Это не жёсткий лимит итоговой стоимости:
                # диапазоны нужны только для формирования более
                # релевантного по цене пула товаров для FashionCLIP.
                item_count = len(search_items)

                target_price: float | None = None
                price_to: float | None = None

                if generation.budget is not None and item_count > 0:
                    target_price = (
                        float(generation.budget) / item_count
                    )
                    price_to = target_price * 1.20

                for search_item in search_items:
                    products = []

                    if target_price is not None:
                        # Ступенчато расширяем только нижнюю границу.
                        #
                        # При target_price = 10 000 ₽:
                        # 1. 5 500–12 000 ₽
                        # 2. 3 500–12 000 ₽
                        # 3. 2 000–12 000 ₽
                        price_from_steps = (
                            target_price * 0.55,
                            target_price * 0.35,
                            target_price * 0.20,
                        )

                        for price_from in price_from_steps:
                            products = (
                                await marketplace.search_products(
                                    search_item.search_query,
                                    price_from=price_from,
                                    price_to=price_to,
                                    fallback_category=search_item.category,
                                )
                            )

                            if products:
                                break

                    # Последний fallback:
                    # если ни один ценовой диапазон не дал товаров,
                    # ищем без ограничения по цене.
                    if not products:
                        products = await marketplace.search_products(
                            search_item.search_query,
                            fallback_category=search_item.category,
                        )

                    await product_service.save_search_products(
                        db=db,
                        search_item=search_item,
                        products=products,
                    )

                # Сохраняем найденные Product и связи.
                await db.commit()

                # -------------------------------------------------
                # 3. Собираем уникальные Product этой генерации
                # -------------------------------------------------

                products_result = await db.execute(
                    select(Product)
                    .join(
                        GenerationSearchItemProduct,
                        GenerationSearchItemProduct.product_id
                        == Product.id,
                    )
                    .join(
                        GenerationSearchItem,
                        GenerationSearchItem.id
                        == GenerationSearchItemProduct
                        .generation_search_item_id,
                    )
                    .where(
                        GenerationSearchItem.generation_id
                        == generation.id
                    )
                    .order_by(
                        GenerationSearchItemProduct.position.asc()
                    )
                )

                found_products = list(
                    products_result.scalars().all()
                )

                # Один Product может попасть через несколько
                # поисковых запросов. Оставляем каждый UUID один раз.
                unique_products: list[Product] = []
                seen_product_ids: set[UUID] = set()

                for product in found_products:
                    if product.id in seen_product_ids:
                        continue

                    seen_product_ids.add(product.id)

                    # В FashionCLIP отправляем только карточки,
                    # для которых есть обязательные данные.
                    if not product.name:
                        continue

                    if not product.category:
                        continue

                    if product.price is None:
                        continue

                    if not product.image_url:
                        continue

                    unique_products.append(product)

                    if (
                        len(unique_products)
                        >= self.MAX_FASHION_CLIP_PRODUCTS
                    ):
                        break

                # -------------------------------------------------
                # 4. Если товаров нет — валидный пустой результат
                # -------------------------------------------------

                if not unique_products:
                    generation.status = "completed"
                    await db.commit()
                    return

                # -------------------------------------------------
                # 5. Формируем FashionCLIP request
                # -------------------------------------------------

                generation.status = "forming_outfits"
                await db.commit()

                fashion_clip_products = [
                    FashionClipProduct(
                        product_id=product.id,
                        name=product.name,
                        category=product.category,
                        price=float(product.price),
                        image_url=product.image_url,
                        description=product.description,
                        colors=product.colors,
                    )
                    for product in unique_products
                ]

                fashion_clip_request = FashionClipRequest(
                    generation_id=generation.id,
                    context=FashionClipContext(
                        prompt=generation.prompt,
                        style=generation.style,
                        occasion=generation.occasion,
                        budget=generation.budget,
                    ),
                    products=fashion_clip_products,
                )

                # -------------------------------------------------
                # 6. Первый реальный HTTP-вызов ML
                # -------------------------------------------------

                fashion_clip = FashionClipClient()

                fashion_clip_response = (
                    await fashion_clip.create_outfits(
                        fashion_clip_request
                    )
                )

                # Защита от ответа не для нашей Generation.
                if (
                    fashion_clip_response.generation_id
                    != generation.id
                ):
                    raise RuntimeError(
                        "FashionCLIP returned wrong generation_id"
                    )

                # -------------------------------------------------
                # 7. Загружаем Product в словарь по UUID
                # -------------------------------------------------

                products_by_id = {
                    product.id: product
                    for product in unique_products
                }

                # -------------------------------------------------
                # 8. Удаляем старые outfits этой Generation
                #
                # Это делает повторный вызов pipeline безопаснее:
                # не получим дубли образов.
                # -------------------------------------------------

                await db.execute(
                    delete(Outfit).where(
                        Outfit.generation_id == generation.id
                    )
                )

                await db.flush()

                # -------------------------------------------------
                # 9. Сохраняем Outfit + OutfitItem
                # -------------------------------------------------

                for ml_outfit in fashion_clip_response.outfits:
                    valid_items: list[
                        tuple[object, Product]
                    ] = []

                    for ml_item in ml_outfit.items:
                        product = products_by_id.get(
                            ml_item.product_id
                        )

                        # ML не должен возвращать неизвестный
                        # product_id. Если всё же вернул —
                        # такой item пропускаем.
                        if product is None:
                            continue

                        valid_items.append(
                            (ml_item, product)
                        )

                    # Пустой Outfit не сохраняем.
                    if not valid_items:
                        continue

                    total_price = sum(
                        float(product.price or 0)
                        for _, product in valid_items
                    )

                    outfit = Outfit(
                        generation_id=generation.id,
                        rank=ml_outfit.rank,
                        score=ml_outfit.score,
                        title=f"Образ {ml_outfit.rank}",
                        occasion=generation.occasion or "other",
                        style=generation.style or "other",
                        total_price=total_price,
                        image=None,
                        ai_explanation=None,
                    )

                    db.add(outfit)
                    await db.flush()

                    for ml_item, product in valid_items:
                        available_sizes = (
                            SizeRecommendationService.normalize_available_sizes(
                                product.sizes,
                                ml_item.category,
                            )
                        )

                        recommended_size = (
                            SizeRecommendationService.recommend_size(
                                available_sizes=available_sizes,
                                category=ml_item.category,
                                gender=generation.gender,
                                chest=generation.chest,
                                waist=generation.waist,
                                hips=generation.hips,
                            )
                        )

                        outfit_item = OutfitItem(
                            outfit_id=outfit.id,
                            product_id=product.id,
                            position=ml_item.position,
                            category=ml_item.category,
                            score=ml_item.score,

                            # Snapshot полей Product.
                            brand=product.brand or "",
                            name=product.name or "",
                            price=float(product.price or 0),
                            size=None,
                            available_sizes=available_sizes,
                            recommended_size=recommended_size,
                            image=product.image_url,
                            marketplace=product.marketplace,
                            url=product.product_url or "",
                        )

                        db.add(outfit_item)

                # -------------------------------------------------
                # 10. Собираем уникальные товары из выбранных outfits
                # -------------------------------------------------

                selected_product_ids: list[UUID] = []
                seen_selected_product_ids: set[UUID] = set()

                for ml_outfit in fashion_clip_response.outfits:
                    for ml_item in ml_outfit.items:
                        product_id = ml_item.product_id

                        if product_id in seen_selected_product_ids:
                            continue

                        if product_id not in products_by_id:
                            continue

                        seen_selected_product_ids.add(product_id)
                        selected_product_ids.append(product_id)

                # -------------------------------------------------
                # 11. Собираем fit data только для выбранных товаров
                # -------------------------------------------------

                generation.status = "collecting_fit_data"
                await db.commit()

                size_shift_products: list[dict] = []

                for product_id in selected_product_ids:
                    product = products_by_id[product_id]

                    if not product.product_url:
                        continue

                    try:
                        fit_data = await marketplace.get_fit_data(
                            product.product_url
                        )
                    except Exception:
                        # Ошибка отзывов одного товара не должна
                        # уничтожать всю уже сформированную подборку.
                        continue

                    size_shift_products.append(
                        {
                            "product_id": str(product.id),
                            "model_id": fit_data.get("model_id"),
                            "reviews": fit_data.get("reviews") or [],
                        }
                    )

                # -------------------------------------------------
                # 12. Size Shift ML
                # -------------------------------------------------

                generation.status = "predicting_fit"
                await db.commit()

                size_shift_request = SizeShiftRequest(
                    generation_id=generation.id,
                    products=[
                        SizeShiftProduct.model_validate(product)
                        for product in size_shift_products
                    ],
                )

                size_shift_client = SizeShiftClient()

                size_shift_response = (
                    await size_shift_client.predict(
                        size_shift_request
                    )
                )

                if (
                    size_shift_response.generation_id
                    != generation.id
                ):
                    raise RuntimeError(
                        "Size Shift returned wrong generation_id"
                    )

                # ML должен возвращать prediction только для товаров,
                # которые Backend отправил в запросе.
                requested_product_ids = {
                    product.product_id
                    for product in size_shift_request.products
                }

                for prediction in size_shift_response.predictions:
                    if (
                        prediction.product_id
                        not in requested_product_ids
                    ):
                        raise RuntimeError(
                            "Size Shift returned unknown product_id: "
                            f"{prediction.product_id}"
                        )

                print(
                    "SIZE_SHIFT_RESPONSE:",
                    size_shift_response.model_dump(
                        mode="json"
                    ),
                )

                # -------------------------------------------------
                # 13. Сохраняем Size Shift prediction
                #
                # Один Product может находиться в нескольких
                # Outfit, поэтому обновляем все OutfitItem
                # этого generation с данным product_id.
                # -------------------------------------------------

                for prediction in size_shift_response.predictions:
                    result = await db.execute(
                        select(OutfitItem)
                        .join(
                            Outfit,
                            Outfit.id == OutfitItem.outfit_id,
                        )
                        .where(
                            Outfit.generation_id == generation.id,
                            OutfitItem.product_id
                            == prediction.product_id,
                        )
                    )

                    outfit_items = result.scalars().all()

                    for outfit_item in outfit_items:
                        outfit_item.fit_status = (
                            prediction.status
                        )
                        outfit_item.fit_signal = (
                            prediction.fit_signal
                        )
                        outfit_item.fit_confidence = (
                            prediction.confidence
                        )
                        outfit_item.fit_num_reviews = (
                            prediction.num_reviews
                        )
                        outfit_item.fit_num_fit_reviews = (
                            prediction.num_fit_reviews
                        )
                        outfit_item.fit_explanation = (
                            prediction.explanation
                        )

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
