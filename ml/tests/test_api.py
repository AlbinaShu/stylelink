import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class FakeOutfitModels:
    def encode_request(self, products, context):
        vectors = {
            product.product_id: {
                "top": [1.0, 0.0],
                "bottom": [0.8, 0.6],
                "dress": [0.9, 0.4],
                "shoes": [0.6, 0.8],
            }.get(product.category, [0.7, 0.7])
            for product in products
        }
        return vectors, [1.0, 0.0]


class FakeFitModel:
    def classify(self, texts):
        return [
            ("runs_small", 0.9) if "маломер" in text.lower() else
            ("runs_large", 0.9) if "большемер" in text.lower() else
            ("true_to_size", 0.85)
            for text in texts
        ]


class FakeB2FitModel:
    backend = "b2"

    def __init__(self):
        self.seen_texts = []

    def classify(self, texts):
        self.seen_texts.extend(texts)
        return [
            {
                "label": "runs_small",
                "confidence": 0.8,
                "probabilities": {
                    "no_signal": 0.1,
                    "runs_large": 0.05,
                    "runs_small": 0.8,
                    "true_to_size": 0.05,
                },
            }
            for _ in texts
        ]


class MlApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.outfit_patch = patch("app.outfits.get_outfit_models", return_value=FakeOutfitModels())
        self.fit_patch = patch("app.size_shift.get_fit_model", return_value=FakeFitModel())
        self.outfit_patch.start()
        self.fit_patch.start()
        self.addCleanup(self.outfit_patch.stop)
        self.addCleanup(self.fit_patch.stop)
        self.generation_id = str(uuid4())
        self.products = [
            {
                "product_id": str(uuid4()),
                "name": name,
                "category": category,
                "price": price,
                "image_url": "https://example.com/image.jpg",
            }
            for name, category, price in (
                ("Top", "top", 1500),
                ("Bottom", "bottom", 2000),
                ("Shoes", "shoes", 2500),
            )
        ]

    def test_outfits_keep_product_ids_and_budget(self):
        response = self.client.post(
            "/api/v1/outfits",
            json={
                "generation_id": self.generation_id,
                "context": {"budget": 6000},
                "products": self.products,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["generation_id"], self.generation_id)
        self.assertEqual(len(body["outfits"]), 1)
        self.assertGreater(body["outfits"][0]["score"], 0)
        self.assertEqual(
            {item["product_id"] for item in body["outfits"][0]["items"]},
            {item["product_id"] for item in self.products},
        )

    def test_outfits_can_be_empty(self):
        response = self.client.post(
            "/api/v1/outfits",
            json={
                "generation_id": self.generation_id,
                "context": {"budget": 1000},
                "products": self.products,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outfits"], [])

    def test_optional_accessory_respects_budget(self):
        accessory = {
            "product_id": str(uuid4()),
            "name": "Bag",
            "category": "accessory",
            "price": 500,
            "image_url": "https://example.com/bag.jpg",
        }
        response = self.client.post(
            "/api/v1/outfits",
            json={
                "generation_id": self.generation_id,
                "context": {"budget": 6500},
                "products": [*self.products, accessory],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(
            any(item["product_id"] == accessory["product_id"] for item in outfit["items"])
            for outfit in response.json()["outfits"]
        ))

        response = self.client.post(
            "/api/v1/outfits",
            json={
                "generation_id": self.generation_id,
                "context": {"budget": 6000},
                "products": [*self.products, accessory],
            },
        )
        self.assertEqual(len(response.json()["outfits"]), 1)

    def test_outfit_request_rejects_duplicate_ids(self):
        response = self.client.post(
            "/api/v1/outfits",
            json={
                "generation_id": self.generation_id,
                "context": {},
                "products": [self.products[0], self.products[0]],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_outfit_request_rejects_more_than_100_products(self):
        products = [
            {**self.products[0], "product_id": str(uuid4())}
            for _ in range(101)
        ]
        response = self.client.post(
            "/api/v1/outfits",
            json={
                "generation_id": self.generation_id,
                "context": {},
                "products": products,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_size_shift_does_not_fabricate_size_or_fit(self):
        product_id = str(uuid4())
        response = self.client.post(
            "/v1/size-shift/predict",
            json={
                "generation_id": self.generation_id,
                "products": [
                    {
                        "product_id": product_id,
                        "model_id": "6102168479",
                        "reviews": [
                            {"text": "Маломерит", "size": "52"},
                            {"text": "Село идеально", "size": None},
                        ],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        prediction = response.json()["predictions"][0]
        self.assertEqual(prediction["product_id"], product_id)
        self.assertEqual(prediction["status"], "insufficient_evidence")
        self.assertEqual(prediction["num_reviews"], 2)
        self.assertIsNone(prediction["fit_signal"])
        self.assertIsNone(prediction["recommended_size"])

    def test_size_shift_predicts_only_with_consistent_reviews(self):
        response = self.client.post(
            "/v1/size-shift/predict",
            json={
                "generation_id": self.generation_id,
                "products": [
                    {
                        "product_id": str(uuid4()),
                        "reviews": [
                            {"text": "Маломерит на размер"},
                            {"text": "В груди маломерит"},
                            {"text": "Маломерит, брать больше"},
                            {"text": "Хорошая ткань"},
                        ],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        prediction = response.json()["predictions"][0]
        self.assertEqual(prediction["status"], "predicted")
        self.assertEqual(prediction["fit_signal"], "runs_small")
        self.assertEqual(prediction["num_fit_reviews"], 3)
        self.assertIsNone(prediction["recommended_size"])

    def test_size_shift_abstains_on_conflicting_reviews(self):
        response = self.client.post(
            "/v1/size-shift/predict",
            json={
                "generation_id": self.generation_id,
                "products": [{
                    "product_id": str(uuid4()),
                    "reviews": [
                        {"text": "Маломерит в плечах"},
                        {"text": "Большемерит на размер"},
                        {"text": "Идет размер в размер"},
                    ],
                }],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["predictions"][0]["status"], "insufficient_evidence"
        )

    def test_size_shift_rejects_blank_review(self):
        response = self.client.post(
            "/v1/size-shift/predict",
            json={
                "generation_id": self.generation_id,
                "products": [
                    {
                        "product_id": str(uuid4()),
                        "reviews": [{"text": "  "}],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_b2_uses_all_review_texts_and_equal_weight_aggregation(self):
        model = FakeB2FitModel()
        with patch("app.size_shift.get_fit_model", return_value=model):
            response = self.client.post(
                "/v1/size-shift/predict",
                json={
                    "generation_id": self.generation_id,
                    "products": [
                        {
                            "product_id": str(uuid4()),
                            "reviews": [
                                {"text": "Прекрасная ткань", "size": "M"},
                                {"text": "Очень удобная вещь"},
                            ],
                        }
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        prediction = response.json()["predictions"][0]
        self.assertEqual(prediction["status"], "predicted")
        self.assertEqual(prediction["fit_signal"], "runs_small")
        self.assertEqual(prediction["num_fit_reviews"], 2)
        self.assertIn("Прекрасная ткань [ORDERED_SIZE=M]", model.seen_texts)


if __name__ == "__main__":
    unittest.main()
