"""Shared fixtures for CSV tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from emporio_agent.data import otp_repository
from emporio_agent.data.csv_tables import TABLE_FILES


def write_table(
    folder: Path,
    table: str,
    rows: list[dict[str, object]],
    columns: list[str] | None = None,
) -> None:
    """Write one supplied CSV file name into folder."""
    folder.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=columns)
    frame.to_csv(folder / TABLE_FILES[table], index=False)


def reset_ownership_store() -> None:
    """Drop in-process codes and grants left by an earlier test."""
    otp_repository._codes.clear()
    otp_repository._grants.clear()
