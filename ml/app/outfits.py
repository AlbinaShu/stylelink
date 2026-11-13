from itertools import chain, product

from app.model_runtime import get_outfit_models
from app.schemas import Outfit, OutfitItem, OutfitProduct, OutfitRequest, OutfitResponse


MAX_PRODUCTS_PER_CATEGORY = 8


def _similarity(left: list[float], right: list[float]) -> float:
    return max(0.0, min(1.0, (sum(a * b for a, b in zip(left, right)) + 1) / 2))


def create_outfits(request: OutfitRequest) -> OutfitResponse:
    by_category: dict[str, list[OutfitProduct]] = {}
    for item in request.products:
        by_category.setdefault(item.category, []).append(item)

    required = list(dict.fromkeys(request.required_categories or []))
    if (required and any(not by_category.get(category) for category in required)) or (
        not required and (not by_category.get("shoes") or not (
            by_category.get("dress") or (by_category.get("top") and by_category.get("bottom"))
        ))
    ):
        return OutfitResponse(generation_id=request.generation_id, outfits=[])

    selected = list(chain.from_iterable(by_category.values()))
    vectors, query_vector = get_outfit_models().encode_request(selected, request.context)
    relevance = {
        item_id: _similarity(vector, query_vector)
        for item_id, vector in vectors.items()
    }

    # Rank ALL supplied products before limiting the combinatorial search.
    for category, items in by_category.items():
        by_category[category] = sorted(
            [item for item in items if item.product_id in vectors],
            key=lambda item: relevance[item.product_id], reverse=True,
        )[:MAX_PRODUCTS_PER_CATEGORY]

    base_candidates = chain(
        product(by_category.get("dress", []), by_category.get("shoes", [])),
        product(
            by_category.get("top", []),
            by_category.get("bottom", []),
            by_category.get("shoes", []),
        ),
    )
    if required:
        base_candidates = product(*(by_category[category] for category in required))
    ranked: list[tuple[float, tuple[OutfitProduct, ...]]] = []
    outerwear_options = [None] if required else [None, *by_category.get("outerwear", [])[:2]]
    accessory_options = [None] if required else [None, *by_category.get("accessory", [])[:2]]
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
            ) / max(1, len(candidate) * (len(candidate) - 1))
            ranked.append((0.8 * item_score + 0.2 * pair_score, candidate))
            # Retain only the requested best outfits, even for six required categories.
            ranked.sort(key=lambda entry: entry[0], reverse=True)
            del ranked[request.outfit_count:]

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
        for rank, (score, candidate) in enumerate(ranked[:request.outfit_count], start=1)
    ]
    return OutfitResponse(generation_id=request.generation_id, outfits=outfits)
