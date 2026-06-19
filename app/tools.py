from typing import Optional

from app.data import get_products_df

_MAX_LIMIT = 20
_DEFAULT_LIMIT = 5


def search_products(
    name: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    limit: int = _DEFAULT_LIMIT,
) -> list[dict]:
    limit = min(max(1, limit), _MAX_LIMIT)
    result = get_products_df()

    if name is not None:
        result = result[result["name"].str.contains(name, case=False, na=False, regex=False)]
    if category is not None:
        result = result[result["category"].str.lower() == category.lower()]
    if min_price is not None:
        result = result[result["price"] >= min_price]
    if max_price is not None:
        result = result[result["price"] <= max_price]
    if in_stock is True:
        result = result[result["stock"] > 0]
    elif in_stock is False:
        result = result[result["stock"] == 0]

    return result.head(limit).to_dict(orient="records")


# OpenAI tool schema for search_products
SEARCH_PRODUCTS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": (
            "Search the ShopNest product catalogue. "
            "All parameters are optional and are ANDed together. "
            "Use this whenever the user asks about products, prices, availability, or categories."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Case-insensitive substring to match against product names.",
                },
                "category": {
                    "type": "string",
                    "description": "Exact product category.",
                    "enum": [
                        "Electronics",
                        "Home & Kitchen",
                        "Sports & Outdoors",
                        "Beauty",
                        "Clothing",
                    ],
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price in USD (inclusive).",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price in USD (inclusive).",
                },
                "in_stock": {
                    "type": "boolean",
                    "description": "True → in-stock items only; false → out-of-stock only.",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Max results to return (1–{_MAX_LIMIT}). Defaults to {_DEFAULT_LIMIT}.",
                    "default": _DEFAULT_LIMIT,
                },
            },
            "required": [],
        },
    },
}
