"""Snapshot the displayed recommendation without exposing treatment data to group A."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem


def displayed_size(item: OutfitItem, generation: Generation) -> str | None:
    if item.category == "accessory":
        return None
    if item.recommended_size is not None:
        return item.recommended_size
    if item.category in {"shoes", "shoe", "footwear", "обувь"} and generation.shoe_size is not None:
        for size in item.available_sizes or []:
            try:
                if float(size) == float(generation.shoe_size):
                    return size
            except (ValueError, TypeError):
                continue
    return None


def snapshot_item(item, outfit, generation, initial_selected_size, explanation_visible):
    sizes = item.available_sizes or []
    recommended = displayed_size(item, generation)
    if item.category == "accessory":
        exclusion = "size_not_applicable"
    elif recommended is None:
        exclusion = "no_recommended_size"
    elif recommended not in sizes:
        exclusion = "recommended_size_unavailable"
    elif initial_selected_size != recommended:
        exclusion = "recommendation_not_preselected"
    else:
        exclusion = None
    count = len(outfit.items)
    return {
        "product_id": str(item.product_id),
        "outfit_item_id": str(item.id),
        "outfit_id": str(outfit.id),
        "generation_id": str(generation.id),
        "name": item.name,
        "price": item.price,
        "category": item.category,
        "recommended_size": recommended,
        "initial_selected_size": initial_selected_size,
        "available_sizes": sizes,
        "eligible": exclusion is None,
        "exclusion_reason": exclusion,
        "outfit_style": outfit.style,
        "outfit_avg_price": outfit.total_price / count if count else None,
        "user_budget": generation.budget,
        "fit_status": item.fit_status,
        "fit_signal": item.fit_signal,
        "confidence": item.fit_confidence,
        "num_reviews": item.fit_num_reviews,
        "num_fit_reviews": item.fit_num_fit_reviews,
        "explanation_available": item.fit_status is not None,
        "explanation_visible": explanation_visible,
    }


async def recommendation_snapshots(session: AsyncSession, user_id: UUID, items):
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(OutfitItem, Outfit, Generation)
        .join(Outfit, Outfit.id == OutfitItem.outfit_id)
        .join(Generation, Generation.id == Outfit.generation_id)
        .options(selectinload(Outfit.items))
        .where(
            OutfitItem.id.in_([item.outfit_item_id for item in items]),
            Generation.user_id == user_id,
        )
    )
    rows = {item.id: (item, outfit, generation) for item, outfit, generation in result.all()}
    snapshots = []
    for client in items:
        row = rows.get(client.outfit_item_id)
        if row is None or row[0].product_id != client.product_id or row[1].id != client.outfit_id:
            raise ValueError("Displayed item does not belong to this user/outfit/product")
        value = snapshot_item(*row, client.initial_selected_size, client.explanation_visible)
        value["explanation_summary"] = client.explanation_summary if client.explanation_visible else None
        value["explanation_stage"] = "summary" if client.explanation_visible else None
        value["content_source"] = "client_rendered"
        snapshots.append(value)
    return snapshots
