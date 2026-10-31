"""Load the supplied CSVs into the operational SQLite database."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pandas as pd

from emporio_agent.config import load_settings
from emporio_agent.data.connection import connect
from emporio_agent.knowledge.policy_knowledge import POLICY_SOURCE, rebuild_policy_index
from emporio_agent.logging import log_failure

_CSV_FILES = (
    ("categories", "desafio_tecnico_ai_eng - categories.csv"),
    ("customers", "desafio_tecnico_ai_eng - customers.csv"),
    ("products", "desafio_tecnico_ai_eng - products.csv"),
    ("orders", "desafio_tecnico_ai_eng - orders.csv"),
    ("order_items", "desafio_tecnico_ai_eng - order_items.csv"),
    ("promotions", "desafio_tecnico_ai_eng - promotions.csv"),
)

_DELETE_ORDER = (
    "promotions",
    "order_items",
    "orders",
    "products",
    "customers",
    "categories",
)


def ingest(data_dir: Path | None = None, database_path: Path | None = None) -> None:
    """Replace operational rows from the six supplied CSV files.

    Raises:
        FileNotFoundError: A required CSV is absent. The message is the file name.
    """
    settings = load_settings()
    folder = Path(data_dir) if data_dir is not None else settings.data_dir
    frames = _read_frames(folder)
    pdf_path = folder / POLICY_SOURCE
    if not pdf_path.is_file():
        log_failure("missing_file", file_name=pdf_path.name)
        raise FileNotFoundError(pdf_path.name)
    if not settings.openai_api_key:
        log_failure("missing_credential")
        raise RuntimeError("OPENAI_API_KEY is required to index the policy PDF")
    connection = connect(database_path, create=True)
    try:
        _replace_rows(connection, frames)
    finally:
        connection.close()
    rebuild_policy_index(pdf_path)


def _read_frames(folder: Path) -> dict[str, pd.DataFrame]:
    """Return one data frame per required CSV."""
    frames: dict[str, pd.DataFrame] = {}
    for table, file_name in _CSV_FILES:
        path = folder / file_name
        if not path.is_file():
            log_failure("missing_file", file_name=file_name)
            raise FileNotFoundError(file_name)
        frames[table] = pd.read_csv(path, dtype=str, keep_default_na=True)
    return frames


def _replace_rows(
    connection: sqlite3.Connection, frames: dict[str, pd.DataFrame]
) -> None:
    """Delete and insert the CSV-backed tables in one transaction."""
    with connection:
        for table in _DELETE_ORDER:
            connection.execute(f"DELETE FROM {table}")
        _insert_categories(connection, frames["categories"])
        _insert_customers(connection, frames["customers"])
        _insert_products(connection, frames["products"])
        _insert_orders(connection, frames["orders"])
        _insert_order_items(connection, frames["order_items"])
        _insert_promotions(connection, frames["promotions"])


def _insert_categories(connection: sqlite3.Connection, frame: pd.DataFrame) -> None:
    """Insert category rows."""
    rows = [
        (_int(row["category_id"]), _text(row["name"]), _text(row["description"]))
        for row in frame.to_dict(orient="records")
    ]
    connection.executemany(
        "INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
        rows,
    )


def _insert_customers(connection: sqlite3.Connection, frame: pd.DataFrame) -> None:
    """Insert customer rows. These columns are not returned by tools."""
    rows = [
        (
            _int(row["customer_id"]),
            _text(row["name"]),
            _text(row["phone"]),
            _text(row["email"]),
            _text(row["city"]),
        )
        for row in frame.to_dict(orient="records")
    ]
    connection.executemany(
        """
        INSERT INTO customers (customer_id, name, phone, email, city)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_products(connection: sqlite3.Connection, frame: pd.DataFrame) -> None:
    """Insert product rows, keeping a missing price or stock as NULL."""
    rows = [
        (
            _int(row["product_id"]),
            _required_text(row["name"]),
            _int(row["category_id"]),
            _text(row["price_brl"]),
            _int(row["stock_quantity"]),
            _text(row["status"]),
            _text(row["description"]),
            _text(row["specs"]),
            _text(row["created_at"]),
        )
        for row in frame.to_dict(orient="records")
    ]
    connection.executemany(
        """
        INSERT INTO products (
            product_id, name, category_id, price_brl, stock_quantity,
            status, description, specs, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_orders(connection: sqlite3.Connection, frame: pd.DataFrame) -> None:
    """Insert order rows. The identifier is stored as text."""
    rows = [
        (
            _identifier(row["order_id"]),
            _int(row["customer_id"]),
            _text(row["order_date"]),
            _text(row["status"]),
            _text(row["total_brl"]),
            _text(row["payment_method"]),
            _text(row["tracking_code"]),
            _text(row["estimated_delivery"]),
            _text(row["notes"]),
        )
        for row in frame.to_dict(orient="records")
    ]
    connection.executemany(
        """
        INSERT INTO orders (
            order_id, customer_id, order_date, status, total_brl,
            payment_method, tracking_code, estimated_delivery, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_order_items(connection: sqlite3.Connection, frame: pd.DataFrame) -> None:
    """Insert item rows without a line price."""
    rows = [
        (
            _identifier(row["order_id"]),
            _int(row["product_id"]),
            _int(row["quantity"]),
        )
        for row in frame.to_dict(orient="records")
    ]
    connection.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
        rows,
    )


def _insert_promotions(connection: sqlite3.Connection, frame: pd.DataFrame) -> None:
    """Insert promotion rows. ``is_active`` stays the recorded flag."""
    rows = [
        (
            _int(row["promotion_id"]),
            _int(row["product_id"]),
            _int(row["discount_percent"]),
            _text(row["description"]),
            _int(row["is_active"]),
        )
        for row in frame.to_dict(orient="records")
    ]
    connection.executemany(
        """
        INSERT INTO promotions (
            promotion_id, product_id, discount_percent, description, is_active
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _missing(value: object) -> bool:
    """Return True when a cell has no recorded value."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == "" or str(value).strip().lower() == "nan"


def _text(value: object) -> str | None:
    """Return a trimmed string, or None when the cell is empty."""
    if _missing(value):
        return None
    return str(value).strip()


def _required_text(value: object) -> str:
    """Return a trimmed string for a required column."""
    text = _text(value)
    if text is None:
        raise ValueError("A required text column is empty")
    return text


def _int(value: object) -> int | None:
    """Return an integer cell, or None when it is empty."""
    text = _text(value)
    if text is None:
        return None
    return int(float(text))


def _identifier(value: object) -> str:
    """Return an order id without a trailing decimal from a numeric cell."""
    text = _required_text(value)
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return text


def main() -> None:
    """Load the store files named by the environment."""
    ingest()


if __name__ == "__main__":
    main()
