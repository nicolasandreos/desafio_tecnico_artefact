"""Validate a promotion query and return the service result unchanged."""

from __future__ import annotations

import sqlite3

from emporio_agent.data.connection import connect
from emporio_agent.services.promotion_service import search_promotions as search_current


def search_promotions(query: str = "") -> dict[str, object]:
    """Search current promotions. An empty query returns every current promotion."""
    if not isinstance(query, str) or query != query.strip() or len(query) > 200:
        return {"error": "invalid_input"}
    try:
        connection = connect(create=False)
    except FileNotFoundError:
        return {"error": "unavailable"}
    except sqlite3.Error:
        return {"error": "unavailable"}
    try:
        return search_current(query, connection=connection)
    finally:
        connection.close()
