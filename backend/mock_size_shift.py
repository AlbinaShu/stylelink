from fastapi import FastAPI

from app.schemas.size_shift import (
    SizeShiftRequest,
    SizeShiftResponse,
    SizeShiftPrediction,
)

app = FastAPI(title="Mock Size Shift ML")


@app.get("/")
async def root():
    return {
        "service": "mock-size-shift",
        "status": "ok",
    }


@app.post(
    "/v1/size-shift/predict",
    response_model=SizeShiftResponse,
)
async def predict(
    request: SizeShiftRequest,
) -> SizeShiftResponse:
    predictions = []

    for product in request.products:
        reviews = product.reviews
        num_reviews = len(reviews)

        # Для проверки HTTP-контура:
        # если отзывов нет — недостаточно данных.
        if num_reviews == 0:
            predictions.append(
                SizeShiftPrediction(
                    product_id=product.product_id,
                    status="insufficient_evidence",
                    fit_signal=None,
                    recommended_size=None,
                    confidence=None,
                    num_reviews=0,
                    num_fit_reviews=0,
                    explanation=(
                        "Недостаточно данных для "
                        "определения посадки"
                    ),
                )
            )
            continue

        # Mock не является реальной ML-логикой.
        # Просто возвращаем валидный predicted response.
        sizes = [
            review.size
            for review in reviews
            if review.size is not None
        ]

        recommended_size = (
            sizes[0]
            if sizes
            else None
        )

        predictions.append(
            SizeShiftPrediction(
                product_id=product.product_id,
                status="predicted",
                fit_signal="true_to_size",
                recommended_size=recommended_size,
                confidence=0.85,
                num_reviews=num_reviews,
                num_fit_reviews=num_reviews,
                explanation=(
                    f"На основе {num_reviews} отзывов: "
                    "соответствует размеру"
                ),
            )
        )

    return SizeShiftResponse(
        generation_id=request.generation_id,
        predictions=predictions,
    )
