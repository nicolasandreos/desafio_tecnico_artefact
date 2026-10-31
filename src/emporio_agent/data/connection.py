"""Open the operational SQLite file. The session file is never opened here."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from emporio_agent.config import load_settings

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path | None = None, *, create: bool = False) -> sqlite3.Connection:
    """Open the operational database and apply the schema.

    Args:
        path: Database file. Defaults to ``SQLITE_PATH``.
        create: When True, create a missing file. Queries leave this False.

    Raises:
        ValueError: The path is the AgentOS session database.
        FileNotFoundError: The file is missing and ``create`` is False.
    """
    settings = load_settings()
    db_path = Path(path) if path is not None else settings.sqlite_path
    if _same_file(db_path, settings.session_db_path):
        raise ValueError("The session database cannot be used for operational data")
    if not db_path.exists():
        if not create:
            raise FileNotFoundError(db_path.name)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return connection


def _same_file(left: Path, right: Path) -> bool:
    """Return True when both paths name the same file."""
    return left.expanduser().resolve() == right.expanduser().resolve()
