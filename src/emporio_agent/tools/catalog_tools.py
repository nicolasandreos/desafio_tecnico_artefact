"""Validate a catalog query and return the service result unchanged."""

from __future__ import annotations

from emporio_agent.services.catalog_service import (
    list_product_categories as list_categories,
)
from emporio_agent.services.catalog_service import (
    search_products as search_catalog,
)
from emporio_agent.services.catalog_service import (
    search_products_by_brand as search_brand,
)


def search_products(query: str) -> dict[str, object]:
    """Search the catalog by product name or category name.

    query is trimmed and at most 200 characters. Accents and singular or
    plural forms still match, so violão matches the category Violões.
    Description and specs are not searched. More than five matches returns
    too_broad and the match count, with no product rows.
    """
    if (
        not isinstance(query, str)
        or query != query.strip()
        or query == ""
        or len(query) > 200
    ):
        return {"error": "invalid_input"}
    return search_catalog(query)


def list_product_categories() -> dict[str, object]:
    """List every instrument category in the catalog.

    Each category has name and description, including a category that
    has no product yet. An empty category table is not_found.
    """
    return list_categories()


def search_products_by_brand(brand: str) -> dict[str, object]:
    """Return products of one manufacturer.

    brand is trimmed and at most 200 characters. The manufacturer must
    appear as a whole word in the product name, so Yamaha matches
    Yamaha C40 and Bateria Acústica Yamaha. Description and specs are
    not searched. Every match is returned.
    """
    if (
        not isinstance(brand, str)
        or brand != brand.strip()
        or brand == ""
        or len(brand) > 200
    ):
        return {"error": "invalid_input"}
    return search_brand(brand)
