"""Read the supplied store CSVs with Pandas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from emporio_agent.config import load_settings

TABLE_FILES = {
    "categories": "desafio_tecnico_ai_eng - categories.csv",
    "customers": "desafio_tecnico_ai_eng - customers.csv",
    "products": "desafio_tecnico_ai_eng - products.csv",
    "orders": "desafio_tecnico_ai_eng - orders.csv",
    "order_items": "desafio_tecnico_ai_eng - order_items.csv",
    "promotions": "desafio_tecnico_ai_eng - promotions.csv",
}

READ_FAILURES = (OSError, UnicodeError, KeyError, ValueError, TypeError)


def read_table(table: str, data_dir: Path | None = None) -> pd.DataFrame:
    """Return one CSV. A missing file raises FileNotFoundError with its name."""
    folder = Path(data_dir) if data_dir is not None else load_settings().data_dir
    path = folder / TABLE_FILES[table]
    if not path.is_file():
        raise FileNotFoundError(path.name)
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def cell_text(value: object) -> str | None:
    """Return a cell as text, or None when it is empty."""
    if value is None or pd.isna(value):
        return None
    return str(value)


def as_number(frame: pd.DataFrame, *columns: str) -> pd.DataFrame:
    """Return a copy with the named id columns parsed as numbers."""
    copied = frame.copy()
    for column in columns:
        copied[column] = pd.to_numeric(copied[column], errors="coerce")
    return copied
