"""Validate a catalog query and return the service result unchanged."""

from __future__ import annotations

import sqlite3

from emporio_agent.data.connection import connect
from emporio_agent.services.catalog_service import search_products as search_catalog


def search_products(query: str) -> dict[str, object]:
    """Search product names. query is required, trimmed, and at most 200 characters."""
    if (
        not isinstance(query, str)
        or query != query.strip()
        or query == ""
        or len(query) > 200
    ):
        return {"error": "invalid_input"}
    connection, error = _open()
    if error is not None:
        return error
    assert connection is not None
    try:
        return search_catalog(query, connection=connection)
    finally:
        connection.close()


def _open() -> tuple[object | None, dict[str, str] | None]:
    """Open the operational database, or return unavailable."""
    try:
        return connect(create=False), None
    except FileNotFoundError:
        return None, {"error": "unavailable"}
    except sqlite3.Error:
        return None, {"error": "unavailable"}
