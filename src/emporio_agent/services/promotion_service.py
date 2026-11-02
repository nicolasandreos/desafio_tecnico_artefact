"""Return current promotions, optionally filtered by product or category name."""

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

_MAX_QUERY = 200


def search_promotions(
    query: str | None = None,
    *,
    data_dir: Path | None = None,
) -> dict[str, object]:
    """Return current promotions from the CSVs. An empty query returns every row."""
    checked = _checked_query(query)
    if checked is None:
        return {"error": "invalid_input"}
    try:
        rows = _promotion_rows(data_dir)
    except READ_FAILURES:
        return {"error": "unavailable"}
    matched = [row for row in rows if _matches(row, checked)]
    if not matched:
        return {"error": "not_found"}
    return {"promotions": matched}


def _promotion_rows(data_dir: Path | None) -> list[dict[str, object]]:
    """Join active promotions.csv rows to the product and category names."""
    promotions = read_table("promotions", data_dir)
    active = promotions.loc[
        pd.to_numeric(promotions["is_active"], errors="coerce") == 1
    ]
    if active.empty:
        return []
    products = as_number(
        read_table("products", data_dir), "product_id", "category_id"
    ).rename(columns={"name": "product_name"})
    categories = as_number(read_table("categories", data_dir), "category_id").rename(
        columns={"name": "category_name"}
    )
    frame = as_number(active, "product_id").merge(
        products[["product_id", "product_name", "category_id"]],
        on="product_id",
        how="inner",
    )
    frame = frame.merge(
        categories[["category_id", "category_name"]],
        on="category_id",
        how="left",
    )
    frame = frame.assign(
        _id=pd.to_numeric(frame["promotion_id"], errors="coerce")
    ).sort_values("_id")
    return [
        {
            "product_name": cell_text(row["product_name"]) or "",
            "category_name": cell_text(row["category_name"]),
            "discount_percent": recorded_number(row["discount_percent"]),
            "description": cell_text(row["description"]),
        }
        for row in frame.to_dict(orient="records")
    ]


def _checked_query(query: str | None) -> str | None:
    """Return a trimmed query, or None when the text is not usable."""
    if query is None:
        return ""
    usable = (
        isinstance(query, str) and query == query.strip() and len(query) <= _MAX_QUERY
    )
    return query if usable else None


def _matches(row: dict[str, object], query: str) -> bool:
    """Return True when the query is empty or appears in the name or category."""
    folded = _fold(query)
    names = (
        _fold(str(row.get("product_name") or "")),
        _fold(str(row.get("category_name") or "")),
    )
    return any(folded in name for name in names)


def _fold(text: str) -> str:
    """Return lower-case text without accents."""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.casefold()
