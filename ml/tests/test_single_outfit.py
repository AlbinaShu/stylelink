import unittest
from unittest.mock import patch
from uuid import uuid4

from app.outfits import create_outfits
from app.schemas import OutfitRequest


class SingleOutfitTest(unittest.TestCase):
    def request(self, products, **kw):
        return OutfitRequest(generation_id=uuid4(), context={"budget": 5000},
                             products=products, **kw)

    def item(self, name, category="top"):
        return {"product_id": uuid4(), "name": name, "category": category,
                "price": 1000, "image_url": "https://example.com/a.jpg"}

    def test_required_top_and_bottom_do_not_require_shoes(self):
        class Models:
            def encode_request(self, products, context):
                return {p.product_id: [1.0, 0.0] for p in products}, [1.0, 0.0]
        with patch("app.outfits.get_outfit_models", return_value=Models()):
            result = create_outfits(self.request(
                [self.item("Top"), self.item("Bottom", "bottom")],
                outfit_count=1, required_categories=["top", "bottom"]))
        self.assertEqual(len(result.outfits), 1)
        self.assertEqual({p.category for p in result.outfits[0].items}, {"top", "bottom"})

    def test_ninth_candidate_is_ranked_and_single_item_has_no_division_by_zero(self):
        class Models:
            def encode_request(self, products, context):
                return {p.product_id: ([1.0, 0.0] if p.name == "best" else [-1.0, 0.0])
                        for p in products}, [1.0, 0.0]
        products = [self.item("other") for _ in range(8)] + [self.item("best")]
        with patch("app.outfits.get_outfit_models", return_value=Models()):
            result = create_outfits(self.request(products, outfit_count=1,
                                                  required_categories=["top"]))
        self.assertEqual(len(result.outfits), 1)
        self.assertEqual(result.outfits[0].items[0].product_id, products[-1]["product_id"])

    def test_missing_required_category_returns_no_outfit(self):
        result = create_outfits(self.request([self.item("Top")],
            outfit_count=1, required_categories=["top", "bottom"]))
        self.assertEqual(result.outfits, [])


if __name__ == "__main__":
    unittest.main()
