from fastapi import FastAPI

app = FastAPI(title="Mock FashionCLIP")


@app.get("/")
async def root():
    return {
        "service": "mock-fashion-clip",
        "status": "ok",
    }


@app.post("/api/v1/outfits")
async def create_outfits(payload: dict):
    generation_id = payload["generation_id"]
    products = payload.get("products", [])

    by_category = {}

    for product in products:
        category = product.get("category")

        if category:
            by_category.setdefault(category, []).append(product)

    outfits = []

    # Вариант 1: платье + обувь
    if by_category.get("dress") and by_category.get("shoes"):
        selected = [
            by_category["dress"][0],
            by_category["shoes"][0],
        ]

    # Вариант 2: верх + низ + обувь
    elif (
        by_category.get("top")
        and by_category.get("bottom")
        and by_category.get("shoes")
    ):
        selected = [
            by_category["top"][0],
            by_category["bottom"][0],
            by_category["shoes"][0],
        ]

    # Для интеграционного теста:
    # если полного комплекта нет, возвращаем до 3 товаров.
    else:
        selected = products[:3]

    if selected:
        items = []

        for position, product in enumerate(selected, start=1):
            items.append(
                {
                    "product_id": product["product_id"],
                    "position": position,
                    "category": product["category"],
                    "score": 0.90,
                }
            )

        outfits.append(
            {
                "rank": 1,
                "score": 0.92,
                "items": items,
            }
        )

    return {
        "generation_id": generation_id,
        "outfits": outfits,
    }
