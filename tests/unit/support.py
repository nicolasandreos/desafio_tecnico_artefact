"""Shared fixtures for operational-database tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from emporio_agent.data.connection import connect


def open_database(path: Path) -> sqlite3.Connection:
    """Create an operational database at path."""
    return connect(path, create=True)


def insert_category(
    connection: sqlite3.Connection,
    category_id: int,
    name: str,
) -> None:
    """Insert one category."""
    connection.execute(
        "INSERT INTO categories (category_id, name, description) VALUES (?, ?, NULL)",
        (category_id, name),
    )


def insert_product(
    connection: sqlite3.Connection,
    *,
    product_id: int,
    name: str,
    category_id: int | None = None,
    price_brl: str | None = "10.00",
    stock_quantity: int | None = 1,
    status: str = "active",
    description: str | None = None,
    specs: str | None = None,
    created_at: str | None = "2020-01-01",
) -> None:
    """Insert one product. Price is stored as recorded text."""
    connection.execute(
        """
        INSERT INTO products (
            product_id, name, category_id, price_brl, stock_quantity,
            status, description, specs, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            name,
            category_id,
            price_brl,
            stock_quantity,
            status,
            description,
            specs,
            created_at,
        ),
    )


def insert_customer(
    connection: sqlite3.Connection,
    customer_id: int,
    *,
    name: str = "Ada Customer",
    phone: str = "(67) 90000-0000",
    email: str | None = "buyer@example.com",
    city: str = "Campo Grande",
) -> None:
    """Insert one customer. These columns must stay out of tool results."""
    connection.execute(
        """
        INSERT INTO customers (customer_id, name, phone, email, city)
        VALUES (?, ?, ?, ?, ?)
        """,
        (customer_id, name, phone, email, city),
    )


def insert_order(
    connection: sqlite3.Connection,
    order_id: str,
    *,
    customer_id: int,
    status: str = "delivered",
    order_date: str = "2025-10-15",
    total_brl: str = "11499",
    payment_method: str = "pix",
    tracking_code: str = "BRTRACK",
    estimated_delivery: str = "2025-10-25",
    notes: str = "leave at desk",
) -> None:
    """Insert one order, including columns the customer must not see."""
    connection.execute(
        """
        INSERT INTO orders (
            order_id, customer_id, order_date, status, total_brl,
            payment_method, tracking_code, estimated_delivery, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            customer_id,
            order_date,
            status,
            total_brl,
            payment_method,
            tracking_code,
            estimated_delivery,
            notes,
        ),
    )


def insert_item(
    connection: sqlite3.Connection,
    order_id: str,
    product_id: int,
    quantity: int,
) -> None:
    """Insert one order item."""
    connection.execute(
        "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
        (order_id, product_id, quantity),
    )
