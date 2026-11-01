import math
import re
from typing import Any

from app.model_runtime import FitClassification, get_fit_model
from app.schemas import SizeShiftPrediction, SizeShiftRequest, SizeShiftResponse


FIT_WORDS = re.compile(
    r"маломер|большемер|размер|посадк|великоват|тесн|узк|село|сидит|подош[её]?л[аои]?|свободн",
    re.IGNORECASE,
)
DIRECTION_LABELS = ("true_to_size", "runs_small", "runs_large")
MAX_REVIEWS_PER_PRODUCT = 20
B2_REVIEW_THRESHOLD = 0.60
B2_ITEM_THRESHOLD = 0.60
ZERO_SHOT_MIN_FIT_REVIEWS = 3
ZERO_SHOT_MIN_REVIEW_SCORE = 0.55
ZERO_SHOT_MIN_AGREEMENT = 0.60


def _model_text(text: str, size: str | None) -> str:
    normalized = " ".join(text.split())
    ordered_size = (size or "").strip()
    return f"{normalized} [ORDERED_SIZE={ordered_size}]" if ordered_size else normalized


def _unpack_classification(
    result: FitClassification | tuple[str, float] | dict[str, Any],
) -> tuple[str, float, dict[str, float]]:
    if isinstance(result, FitClassification):
        return result.label, result.confidence, result.probabilities
    if isinstance(result, dict):
        label = str(result["label"])
        confidence = float(result["confidence"])
        probabilities = {
            str(key): float(value)
            for key, value in dict(result.get("probabilities") or {}).items()
        }
        return label, confidence, probabilities or {label: confidence}
    label, confidence = result
    return str(label), float(confidence), {str(label): float(confidence)}


def _select_reviews(product, backend: str) -> list[str]:
    seen: set[tuple[str, str]] = set()
    selected: list[str] = []
    for review in product.reviews:
        normalized = " ".join(review.text.lower().split())
        size = (review.size or "").strip()
        deduplication_key = (normalized, size)
        if deduplication_key in seen:
            continue
        if backend == "zero_shot" and not FIT_WORDS.search(review.text):
            continue
        seen.add(deduplication_key)
        selected.append(
            _model_text(review.text, review.size) if backend == "b2" else review.text
        )
        if len(selected) == MAX_REVIEWS_PER_PRODUCT:
            break
    return selected


def _predict_b2(product, results) -> SizeShiftPrediction:
    evidence: list[dict[str, float]] = []
    for result in results:
        label, confidence, probabilities = _unpack_classification(result)
        if confidence < B2_REVIEW_THRESHOLD or label == "no_signal":
            continue
        direction_total = sum(probabilities.get(candidate, 0.0) for candidate in DIRECTION_LABELS)
        if direction_total <= 0:
            continue
        evidence.append(
            {
                candidate: probabilities.get(candidate, 0.0) / direction_total
                for candidate in DIRECTION_LABELS
            }
        )

    if not evidence:
        return SizeShiftPrediction(
            product_id=product.product_id,
            status="insufficient_evidence",
            fit_signal=None,
            recommended_size=None,
            confidence=None,
            num_reviews=len(product.reviews),
            num_fit_reviews=0,
            explanation="B2 не нашла уверенных направленных свидетельств о посадке.",
        )

    item_probabilities = {
        label: sum(row[label] for row in evidence) / len(evidence)
        for label in DIRECTION_LABELS
    }
    winner = max(item_probabilities, key=item_probabilities.get)
    confidence = item_probabilities[winner]
    tied = sum(
        math.isclose(value, confidence, rel_tol=1e-9, abs_tol=1e-12)
        for value in item_probabilities.values()
    ) > 1
    predicted = confidence >= B2_ITEM_THRESHOLD and not tied
    return SizeShiftPrediction(
        product_id=product.product_id,
        status="predicted" if predicted else "insufficient_evidence",
        fit_signal=winner if predicted else None,
        recommended_size=None,
        confidence=round(confidence, 4) if predicted else None,
        num_reviews=len(product.reviews),
        num_fit_reviews=len(evidence),
        explanation=(
            f"Equal-weight aggregation: {len(evidence)} уверенных отзывов, "
            f"confidence {confidence:.3f}."
            if predicted
            else "Equal-weight aggregation не достигла порога confidence 0.60."
        ),
    )


def _predict_zero_shot(product, results) -> SizeShiftPrediction:
    usable = []
    for result in results:
        label, score, _ = _unpack_classification(result)
        if score >= ZERO_SHOT_MIN_REVIEW_SCORE:
            usable.append((label, score))
    counts = {label: 0 for label in DIRECTION_LABELS}
    for label, _ in usable:
        if label in counts:
            counts[label] += 1
    winner = max(counts, key=counts.get)
    agreement = counts[winner] / len(usable) if usable else 0.0
    predicted = (
        len(usable) >= ZERO_SHOT_MIN_FIT_REVIEWS
        and agreement >= ZERO_SHOT_MIN_AGREEMENT
    )
    confidence = (
        agreement
        * sum(score for label, score in usable if label == winner)
        / counts[winner]
        if predicted
        else None
    )
    return SizeShiftPrediction(
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


def predict_size_shift(request: SizeShiftRequest) -> SizeShiftResponse:
    model = get_fit_model()
    backend = getattr(model, "backend", "zero_shot")
    texts_by_product = [
        _select_reviews(product, backend) for product in request.products
    ]
    all_texts = [text for texts in texts_by_product for text in texts]
    classified = model.classify(all_texts) if all_texts else []

    offset = 0
    predictions = []
    for product, texts in zip(request.products, texts_by_product):
        results = classified[offset : offset + len(texts)]
        offset += len(texts)
        predictions.append(
            _predict_b2(product, results)
            if backend == "b2"
            else _predict_zero_shot(product, results)
        )
    return SizeShiftResponse(generation_id=request.generation_id, predictions=predictions)
