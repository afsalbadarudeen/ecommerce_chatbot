from typing import Optional

from app.data import get_products_df

_MAX_LIMIT = 20
_DEFAULT_LIMIT = 5

_NUMERIC_COLS = frozenset({"price", "stock", "rating"})
_ALL_COLS = frozenset({"product_id", "sku", "name", "brand", "category", "price", "stock", "rating"})
_GROUP_COLS = frozenset({"category", "brand"})
_ALLOWED_OPS = frozenset({"count", "average", "min", "max", "sum", "list_unique", "top_n"})


def _apply_filters(
    df,
    name: Optional[str],
    category: Optional[str],
    min_price: Optional[float],
    max_price: Optional[float],
    in_stock: Optional[bool],
):
    if name is not None:
        df = df[df["name"].str.contains(name, case=False, na=False, regex=False)]
    if category is not None:
        df = df[df["category"].str.lower() == category.lower()]
    if min_price is not None:
        df = df[df["price"] >= min_price]
    if max_price is not None:
        df = df[df["price"] <= max_price]
    if in_stock is True:
        df = df[df["stock"] > 0]
    elif in_stock is False:
        df = df[df["stock"] == 0]
    return df


def search_products(
    name: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    limit: int = _DEFAULT_LIMIT,
) -> list[dict]:
    limit = min(max(1, limit), _MAX_LIMIT)
    result = _apply_filters(get_products_df(), name, category, min_price, max_price, in_stock)
    return result.head(limit).to_dict(orient="records")


def analyze_products(
    operation: str,
    column: Optional[str] = None,
    group_by: Optional[str] = None,
    sort_by: Optional[str] = None,
    ascending: bool = True,
    limit: int = 10,
    name: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
) -> dict:
    if operation not in _ALLOWED_OPS:
        return {"error": "invalid operation"}

    df = _apply_filters(get_products_df(), name, category, min_price, max_price, in_stock)
    limit = min(max(1, limit), _MAX_LIMIT)

    if operation == "list_unique":
        if column not in _ALL_COLS:
            return {"error": "invalid column"}
        vals = sorted(str(v) for v in df[column].dropna().unique())
        return {"unique_values": vals, "count": len(vals)}

    if operation == "count":
        if group_by:
            result = df.groupby(group_by).size().reset_index(name="count")
            result = result.sort_values("count", ascending=False)
            return {"data": result.head(limit).to_dict(orient="records"), "total": int(df.shape[0])}
        return {"count": int(df.shape[0])}

    if column not in _NUMERIC_COLS:
        return {"error": f"column must be one of {sorted(_NUMERIC_COLS)} for {operation}"}

    if operation in ("average", "min", "max", "sum"):
        agg_fn = {"average": "mean", "min": "min", "max": "max", "sum": "sum"}[operation]
        if group_by:
            result = df.groupby(group_by)[column].agg(agg_fn).reset_index()
            result.columns = [group_by, f"{operation}_{column}"]
            out_col = f"{operation}_{column}"
            sort_col = sort_by if sort_by in result.columns else out_col
            result = result.sort_values(sort_col, ascending=ascending)
            return {"data": result.head(limit).to_dict(orient="records")}
        val = getattr(df[column], agg_fn)()
        if operation in ("average", "sum"):
            val = round(float(val), 2)
        if operation in ("min", "max"):
            idx = df[column].idxmin() if operation == "min" else df[column].idxmax()
            return {"value": val, "product": df.loc[idx].to_dict()}
        return {"value": val}

    if operation == "top_n":
        sort_col = sort_by if sort_by in _ALL_COLS else column
        result = df.sort_values(sort_col, ascending=ascending)
        return {"data": result.head(limit).to_dict(orient="records")}

    return {"error": "unknown operation"}


ANALYZE_PRODUCTS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "analyze_products",
        "description": (
            "Perform aggregate analysis on the ShopNest product catalogue. "
            "Use for questions about counts, averages, totals, extremes, unique values, "
            "rankings, or comparisons across categories/brands. "
            "Combine with filters to narrow the scope first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["count", "average", "min", "max", "sum", "list_unique", "top_n"],
                    "description": (
                        "count=row count; average/min/max/sum=aggregate on column; "
                        "list_unique=distinct values of column; "
                        "top_n=rows sorted by column (use sort_by + ascending)"
                    ),
                },
                "column": {
                    "type": "string",
                    "enum": ["price", "stock", "rating", "name", "brand", "category"],
                    "description": "Column to aggregate or list. Required for all ops except bare count.",
                },
                "group_by": {
                    "type": "string",
                    "enum": ["category", "brand"],
                    "description": "Group aggregate results by this column.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["price", "stock", "rating", "name", "brand", "category"],
                    "description": "Sort results by this column (used with top_n or grouped results).",
                },
                "ascending": {
                    "type": "boolean",
                    "description": "Sort ascending (true) or descending (false). Default true.",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Max rows to return (1–{_MAX_LIMIT}). Default 10.",
                    "default": 10,
                },
                "name": {
                    "type": "string",
                    "description": "Pre-filter: case-insensitive substring on product name.",
                },
                "category": {
                    "type": "string",
                    "enum": ["Electronics", "Home & Kitchen", "Sports & Outdoors", "Beauty", "Clothing"],
                    "description": "Pre-filter: exact category.",
                },
                "min_price": {"type": "number", "description": "Pre-filter: minimum price (inclusive)."},
                "max_price": {"type": "number", "description": "Pre-filter: maximum price (inclusive)."},
                "in_stock": {"type": "boolean", "description": "Pre-filter: true=in-stock only."},
            },
            "required": ["operation"],
        },
    },
}

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
