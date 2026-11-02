"""Validate a promotion query and return the service result unchanged."""

from __future__ import annotations

from emporio_agent.services.promotion_service import search_promotions as search_current


def search_promotions(query: str = "") -> dict[str, object]:
    """Search current promotions in the CSV. An empty query returns every row."""
    if not isinstance(query, str) or query != query.strip() or len(query) > 200:
        return {"error": "invalid_input"}
    return search_current(query)
