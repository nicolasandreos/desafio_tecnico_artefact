"""Return current promotions, optionally filtered by product or category name."""

from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path

from emporio_agent.data.connection import connect
from emporio_agent.data.promotion_repository import list_current_promotions

_MAX_QUERY = 200


def search_promotions(
    query: str | None = None,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: Path | None = None,
) -> dict[str, object]:
    """Return current promotions. An empty query returns every current row."""
    checked = _checked_query(query)
    if checked is None:
        return {"error": "invalid_input"}
    owns = False
    conn = connection
    try:
        if conn is None:
            conn = connect(database_path, create=False)
            owns = True
        rows = list_current_promotions(conn)
    except FileNotFoundError:
        return {"error": "unavailable"}
    except sqlite3.Error:
        return {"error": "unavailable"}
    finally:
        if owns and conn is not None:
            conn.close()
    matched = [row for row in rows if _matches(row, checked)]
    if not matched:
        return {"error": "not_found"}
    return {"promotions": matched}


def _checked_query(query: str | None) -> str | None:
    """Return a trimmed query, or None when the text is not usable."""
    if query is None:
        return ""
    if not isinstance(query, str):
        return None
    if query != query.strip() or len(query) > _MAX_QUERY:
        return None
    return query


def _matches(row: dict[str, object], query: str) -> bool:
    """Return True when the query is empty or appears in the name or category."""
    if query == "":
        return True
    folded = _fold(query)
    product_name = _fold(str(row.get("product_name") or ""))
    category_name = _fold(str(row.get("category_name") or ""))
    return folded in product_name or folded in category_name


def _fold(text: str) -> str:
    """Return lower-case text without accents."""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.casefold()
