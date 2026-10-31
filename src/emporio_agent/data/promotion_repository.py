"""Read current promotions with the product and category names."""

from __future__ import annotations

import sqlite3

_CURRENT = """
SELECT
    p.name AS product_name,
    c.name AS category_name,
    pr.discount_percent,
    pr.description
FROM promotions AS pr
JOIN products AS p ON p.product_id = pr.product_id
LEFT JOIN categories AS c ON c.category_id = p.category_id
WHERE pr.is_active = 1
ORDER BY pr.promotion_id
"""


def list_current_promotions(connection: sqlite3.Connection) -> list[dict[str, object]]:
    """Return promotions whose recorded is_active flag is 1."""
    rows = connection.execute(_CURRENT).fetchall()
    return [
        {
            "product_name": row["product_name"],
            "category_name": row["category_name"],
            "discount_percent": row["discount_percent"],
            "description": row["description"],
        }
        for row in rows
    ]
