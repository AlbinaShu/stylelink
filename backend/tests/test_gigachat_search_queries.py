import pytest

from app.services.gigachat import clean_search_query


@pytest.mark.parametrize("amount", ["5000", "5000.0"])
def test_bare_budget_is_removed_but_other_numbers_are_preserved(amount):
    assert clean_search_query(f"брюки хлопок 100% {amount}", budget=5000.0) == "брюки хлопок 100%"


def test_budget_is_not_removed_from_a_product_identifier():
    assert clean_search_query("рубашка артикул5000", budget=5000) == "рубашка артикул5000"


def test_no_budget_preserves_numeric_features():
    assert clean_search_query("рюкзак 20 л") == "рюкзак 20 л"
