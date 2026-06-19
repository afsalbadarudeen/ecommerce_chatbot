import pandas as pd
import pytest

from app.tools import search_products

# 25-row sample: enough to trigger the limit=20 clamp
_BASE = [
    {
        "name": f"Generic Item {i}",
        "category": "Electronics",
        "price": float(10 * i),
        "stock": 1,
        "description": f"Item {i}",
    }
    for i in range(1, 22)  # 21 rows at $10–$210
]
_EXTRAS = [
    {"name": "Wireless Headphones", "category": "Electronics",     "price": 89.99, "stock": 10, "description": "Great sound"},
    {"name": "Yoga Mat",            "category": "Sports & Outdoors","price": 45.00, "stock": 0,  "description": "Non-slip"},
    {"name": "Argan Oil",           "category": "Beauty",           "price": 22.50, "stock": 5,  "description": "Hair oil"},
    {"name": "Coffee Mug",          "category": "Home & Kitchen",   "price": 15.00, "stock": 3,  "description": "Ceramic"},
]
_SAMPLE = pd.DataFrame(_BASE + _EXTRAS)  # 25 rows total


@pytest.fixture(autouse=True)
def _patch_df(monkeypatch):
    monkeypatch.setattr("app.tools.get_products_df", lambda: _SAMPLE)


def test_name_search_case_insensitive():
    results = search_products(name="HEADPHONES")
    assert len(results) == 1
    assert results[0]["name"] == "Wireless Headphones"


def test_name_search_partial_match():
    # "oil" should match "Argan Oil" only
    results = search_products(name="oil", limit=20)
    assert all("oil" in r["name"].lower() for r in results)
    assert any(r["name"] == "Argan Oil" for r in results)


def test_price_range():
    results = search_products(min_price=20.00, max_price=50.00, limit=20)
    assert results, "Expected at least one result in $20–$50"
    assert all(20.00 <= r["price"] <= 50.00 for r in results)
    names = {r["name"] for r in results}
    assert "Yoga Mat" in names      # $45
    assert "Argan Oil" in names     # $22.50
    assert "Coffee Mug" not in names  # $15 is below min


def test_limit_clamp():
    # 25 rows in sample; limit=100 must be clamped to 20
    results = search_products(limit=100)
    assert len(results) == 20


def test_limit_default():
    results = search_products()
    assert len(results) == 5


def test_in_stock_true():
    results = search_products(in_stock=True, limit=20)
    assert results
    assert all(r["stock"] > 0 for r in results)
    assert not any(r["name"] == "Yoga Mat" for r in results)  # stock=0


def test_in_stock_false():
    results = search_products(in_stock=False, limit=20)
    assert all(r["stock"] == 0 for r in results)
    assert any(r["name"] == "Yoga Mat" for r in results)


def test_combined_filters():
    results = search_products(category="Electronics", max_price=100.00, in_stock=True, limit=20)
    assert all(r["category"] == "Electronics" for r in results)
    assert all(r["price"] <= 100.00 for r in results)
    assert all(r["stock"] > 0 for r in results)
