"""Match catalog products by name and cap the result at five rows."""

from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path

from emporio_agent.data.catalog_repository import list_products
from emporio_agent.data.connection import connect

_MAX_MATCHES = 5
_MAX_QUERY = 200


def search_products(
    query: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: Path | None = None,
) -> dict[str, object]:
    """Return one to five name matches, or an error code."""
    if not _valid_query(query):
        return {"error": "invalid_input"}
    owns = False
    conn = connection
    try:
        if conn is None:
            conn = connect(database_path, create=False)
            owns = True
        products = list_products(conn)
    except FileNotFoundError:
        return {"error": "unavailable"}
    except sqlite3.Error:
        return {"error": "unavailable"}
    finally:
        if owns and conn is not None:
            conn.close()
    matches = [row for row in products if _name_matches(str(row["name"]), query)]
    if not matches:
        return {"error": "not_found"}
    if len(matches) > _MAX_MATCHES:
        return {"error": "too_broad", "match_count": len(matches)}
    return {"matches": matches}


def _valid_query(query: object) -> bool:
    """Return True when query is a trimmed string of at most 200 characters."""
    if not isinstance(query, str):
        return False
    if query != query.strip() or query == "":
        return False
    return len(query) <= _MAX_QUERY


def _name_matches(name: str, query: str) -> bool:
    """Return True when every query word appears in the product name."""
    folded_name = _fold(name)
    words = [_fold(word) for word in query.split() if word]
    return all(word in folded_name for word in words)


def _fold(text: str) -> str:
    """Return lower-case text without accents."""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.casefold()
