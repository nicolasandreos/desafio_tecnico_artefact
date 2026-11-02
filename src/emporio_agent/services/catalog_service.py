"""Match catalog products by name or category and cap the result at five rows."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd

from emporio_agent.data.csv_tables import (
    READ_FAILURES,
    as_number,
    cell_text,
    read_table,
)
from emporio_agent.data.values import recorded_number

_MAX_MATCHES = 5
_MAX_QUERY = 200


def search_products(query: str, *, data_dir: Path | None = None) -> dict[str, object]:
    """Return one to five name or category matches, or an error code."""
    if not _valid_query(query):
        return {"error": "invalid_input"}
    try:
        products = _product_rows(data_dir)
    except READ_FAILURES:
        return {"error": "unavailable"}
    matches = [row for row in products if _row_matches(row, query)]
    count = len(matches)
    if count == 0 or count > _MAX_MATCHES:
        return (
            {"error": "not_found"}
            if count == 0
            else {"error": "too_broad", "match_count": count}
        )
    return {"matches": matches}


def list_product_categories(*, data_dir: Path | None = None) -> dict[str, object]:
    """Return every category in the catalog, including those with no product."""
    try:
        categories = read_table("categories", data_dir)
    except READ_FAILURES:
        return {"error": "unavailable"}
    if categories.empty or "name" not in categories.columns:
        return {"error": "not_found"}
    frame = as_number(categories, "category_id").sort_values("category_id")
    rows = [
        {
            "name": name,
            "description": cell_text(row.get("description")),
        }
        for row in frame.to_dict(orient="records")
        if (name := cell_text(row.get("name")))
    ]
    if not rows:
        return {"error": "not_found"}
    return {"categories": rows}


def search_products_by_brand(
    brand: str,
    *,
    data_dir: Path | None = None,
) -> dict[str, object]:
    """Return every product whose name contains the manufacturer as a whole word."""
    if not _valid_query(brand):
        return {"error": "invalid_input"}
    try:
        products = _product_rows(data_dir)
    except READ_FAILURES:
        return {"error": "unavailable"}
    matches = [row for row in products if _brand_matches(str(row["name"]), brand)]
    if not matches:
        return {"error": "not_found"}
    return {"matches": matches}


def _product_rows(data_dir: Path | None) -> list[dict[str, object]]:
    """Join products.csv to categories.csv and keep the customer-facing columns."""
    products = read_table("products", data_dir)
    if products.empty:
        return []
    categories = as_number(read_table("categories", data_dir), "category_id")
    products = as_number(products, "category_id")
    categories = categories.rename(columns={"name": "category_name"})
    frame = products.merge(
        categories[["category_id", "category_name"]],
        on="category_id",
        how="left",
    )
    frame = frame.assign(
        _id=pd.to_numeric(frame["product_id"], errors="coerce")
    ).sort_values("_id")
    return [
        {
            "name": cell_text(row["name"]) or "",
            "category_name": cell_text(row["category_name"]),
            "price_brl": recorded_number(row["price_brl"]),
            "stock_quantity": recorded_number(row["stock_quantity"]),
            "status": cell_text(row["status"]),
        }
        for row in frame.to_dict(orient="records")
    ]


def _valid_query(query: object) -> bool:
    """Return True when query is a trimmed string of at most 200 characters."""
    return (
        isinstance(query, str)
        and query == query.strip()
        and 0 < len(query) <= _MAX_QUERY
    )


def _brand_matches(name: str, brand: str) -> bool:
    """Return True when every brand word is a whole word in the product name."""
    words = set(_stem(name).split())
    wanted = [_stem(word) for word in brand.split() if word]
    return bool(wanted) and all(word in words for word in wanted)


def _row_matches(row: dict[str, object], query: str) -> bool:
    """Return True when every query word is in the name or the category."""
    name = _stem(_text(row.get("name")))
    category = _stem(_text(row.get("category_name")))
    words = [_stem(word) for word in query.split() if word]
    return all(word in name or word in category for word in words)


def _text(value: object) -> str:
    """Return a cell as text. Missing stays empty."""
    return "" if value is None else str(value)


def _stem(text: str) -> str:
    """Fold accents, then reduce each word to a singular stem."""
    return " ".join(_stem_word(word) for word in _fold(text).split())


def _stem_word(word: str) -> str:
    """Map a folded Portuguese plural onto the singular form used in search."""
    if len(word) > 4 and word.endswith(("oes", "aes")):
        return f"{word[:-3]}ao"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _fold(text: str) -> str:
    """Return lower-case text without accents."""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.casefold()
