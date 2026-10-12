import re

from app.model_runtime import get_fit_model
from app.schemas import SizeShiftPrediction, SizeShiftRequest, SizeShiftResponse


FIT_WORDS = re.compile(
    r"маломер|большемер|размер|посадк|великоват|тесн|узк|село|сидит|подош[её]?л[аои]?|свободн",
    re.IGNORECASE,
)
MAX_REVIEWS_PER_PRODUCT = 20
MIN_FIT_REVIEWS = 3
MIN_REVIEW_SCORE = 0.55
MIN_AGREEMENT = 0.6


def predict_size_shift(request: SizeShiftRequest) -> SizeShiftResponse:
    texts_by_product: list[list[str]] = []
    all_texts: list[str] = []
    for product in request.products:
        seen: set[str] = set()
        selected: list[str] = []
        for review in product.reviews:
            normalized = " ".join(review.text.lower().split())
            if normalized in seen or not FIT_WORDS.search(review.text):
                continue
            seen.add(normalized)
            selected.append(review.text)
            if len(selected) == MAX_REVIEWS_PER_PRODUCT:
                break
        texts_by_product.append(selected)
        all_texts.extend(selected)

    classified = get_fit_model().classify(all_texts) if all_texts else []
    offset = 0
    predictions: list[SizeShiftPrediction] = []
    for product, texts in zip(request.products, texts_by_product):
        results = classified[offset : offset + len(texts)]
        offset += len(texts)
        usable = [
            (label, score)
            for label, score in results
            if score >= MIN_REVIEW_SCORE
        ]
        counts = {"runs_small": 0, "true_to_size": 0, "runs_large": 0}
        for label, _ in usable:
            counts[label] += 1
        winner = max(counts, key=counts.get)
        agreement = counts[winner] / len(usable) if usable else 0.0
        predicted = len(usable) >= MIN_FIT_REVIEWS and agreement >= MIN_AGREEMENT
        confidence = (
            agreement * sum(score for label, score in usable if label == winner)
            / counts[winner]
            if predicted
            else None
        )
        predictions.append(
            SizeShiftPrediction(
                product_id=product.product_id,
                status="predicted" if predicted else "insufficient_evidence",
                fit_signal=winner if predicted else None,
                recommended_size=None,
                confidence=round(confidence, 4) if confidence is not None else None,
                num_reviews=len(product.reviews),
                num_fit_reviews=len(usable),
                explanation=(
                    f"{counts[winner]} из {len(usable)} подходящих отзывов согласуются по посадке."
                    if predicted
                    else "Недостаточно согласованных отзывов о посадке."
                ),
            )
        )
    return SizeShiftResponse(generation_id=request.generation_id, predictions=predictions)
