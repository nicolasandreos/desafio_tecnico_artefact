"""Read allow-listed product columns. Description and specs are not selected."""

from __future__ import annotations

import sqlite3

from emporio_agent.data.values import recorded_number

_LIST_PRODUCTS = """
SELECT
    p.name,
    c.name AS category_name,
    p.price_brl,
    p.stock_quantity,
    p.status
FROM products AS p
LEFT JOIN categories AS c ON c.category_id = p.category_id
ORDER BY p.product_id
"""


def list_products(connection: sqlite3.Connection) -> list[dict[str, object]]:
    """Return every product's customer-facing columns."""
    rows = connection.execute(_LIST_PRODUCTS).fetchall()
    return [
        {
            "name": row["name"],
            "category_name": row["category_name"],
            "price_brl": recorded_number(row["price_brl"]),
            "stock_quantity": recorded_number(row["stock_quantity"]),
            "status": row["status"],
        }
        for row in rows
    ]
