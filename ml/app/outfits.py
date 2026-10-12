from itertools import chain, product

from app.model_runtime import get_outfit_models
from app.schemas import Outfit, OutfitItem, OutfitProduct, OutfitRequest, OutfitResponse


MAX_PRODUCTS_PER_CATEGORY = 8


def _similarity(left: list[float], right: list[float]) -> float:
    return max(0.0, min(1.0, (sum(a * b for a, b in zip(left, right)) + 1) / 2))


def create_outfits(request: OutfitRequest) -> OutfitResponse:
    by_category: dict[str, list[OutfitProduct]] = {}
    for item in request.products:
        group = by_category.setdefault(item.category, [])
        if len(group) < MAX_PRODUCTS_PER_CATEGORY:
            group.append(item)

    if not by_category.get("shoes") or not (
        by_category.get("dress") or (by_category.get("top") and by_category.get("bottom"))
    ):
        return OutfitResponse(generation_id=request.generation_id, outfits=[])

    selected = list(chain.from_iterable(by_category.values()))
    vectors, query_vector = get_outfit_models().encode_request(selected, request.context)
    relevance = {
        item_id: _similarity(vector, query_vector)
        for item_id, vector in vectors.items()
    }

    base_candidates = chain(
        product(by_category.get("dress", []), by_category.get("shoes", [])),
        product(
            by_category.get("top", []),
            by_category.get("bottom", []),
            by_category.get("shoes", []),
        ),
    )
    ranked: list[tuple[float, tuple[OutfitProduct, ...]]] = []
    outerwear_options = [None, *by_category.get("outerwear", [])[:2]]
    accessory_options = [None, *by_category.get("accessory", [])[:2]]
    for base in base_candidates:
        for outerwear, accessory in product(outerwear_options, accessory_options):
            candidate = (*base, *(item for item in (outerwear, accessory) if item))
            if any(item.product_id not in vectors for item in candidate):
                continue
            if request.context.budget is not None and sum(
                item.price for item in candidate
            ) > request.context.budget:
                continue

            item_score = sum(relevance[item.product_id] for item in candidate) / len(candidate)
            pair_score = sum(
                _similarity(vectors[left.product_id], vectors[right.product_id])
                for left, right in product(candidate, repeat=2)
                if left.product_id != right.product_id
            ) / (len(candidate) * (len(candidate) - 1))
            ranked.append((0.8 * item_score + 0.2 * pair_score, candidate))

    ranked.sort(key=lambda entry: entry[0], reverse=True)
    outfits = [
        Outfit(
            rank=rank,
            score=round(score, 4),
            items=[
                OutfitItem(
                    product_id=item.product_id,
                    position=position,
                    category=item.category,
                    score=round(relevance[item.product_id], 4),
                )
                for position, item in enumerate(candidate, start=1)
            ],
        )
        for rank, (score, candidate) in enumerate(ranked[:5], start=1)
    ]
    return OutfitResponse(generation_id=request.generation_id, outfits=outfits)
