"""Read orders and items using an explicit column list."""

from __future__ import annotations

import sqlite3

from emporio_agent.data.values import recorded_number

_MATCH = """
SELECT o.order_id, c.email
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
WHERE lower(o.order_id) = lower(?)
"""

_DETAILS = """
SELECT o.order_id, o.status, o.order_date, o.total_brl
FROM orders AS o
WHERE lower(o.order_id) = lower(?)
"""

_ITEMS = """
SELECT p.name AS name, oi.quantity AS quantity
FROM order_items AS oi
LEFT JOIN products AS p ON p.product_id = oi.product_id
WHERE lower(oi.order_id) = lower(?)
ORDER BY oi.rowid
"""


def find_matches(connection: sqlite3.Connection, order_id: str) -> list[sqlite3.Row]:
    """Return matching orders and the email used only to send a code."""
    return list(connection.execute(_MATCH, (order_id,)).fetchall())


def find_details(connection: sqlite3.Connection, order_id: str) -> list[sqlite3.Row]:
    """Return allow-listed order columns for one identifier."""
    return list(connection.execute(_DETAILS, (order_id,)).fetchall())


def find_items(
    connection: sqlite3.Connection, order_id: str
) -> list[dict[str, object]]:
    """Return item name and quantity. Line price is not stored and not computed."""
    rows = connection.execute(_ITEMS, (order_id,)).fetchall()
    return [
        {"name": row["name"], "quantity": recorded_number(row["quantity"])}
        for row in rows
    ]


def order_payload(
    row: sqlite3.Row, fields: list[str], items: list[dict[str, object]]
) -> dict:
    """Copy only the requested allow-listed keys."""
    payload: dict[str, object] = {}
    if "status" in fields:
        payload["status"] = row["status"]
    if "order_date" in fields:
        payload["order_date"] = row["order_date"]
    if "items" in fields:
        payload["items"] = items
    if "total_brl" in fields:
        payload["total_brl"] = recorded_number(row["total_brl"])
    return payload
