"""Store ownership codes as hashes. The raw code is never written."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta


def hash_code(code: str) -> str:
    """Return the SHA-256 hex digest of a six-digit code."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def store_code(
    connection: sqlite3.Connection,
    order_id: str,
    code: str,
    sent_at: datetime,
) -> None:
    """Replace the previous code and store the new hash for 15 minutes."""
    expires_at = sent_at + timedelta(minutes=15)
    connection.execute(
        """
        UPDATE ownership_codes
        SET replaced = 1
        WHERE lower(order_id) = lower(?) AND replaced = 0
        """,
        (order_id,),
    )
    connection.execute(
        """
        INSERT INTO ownership_codes (order_id, code_hash, sent_at, expires_at, replaced)
        VALUES (?, ?, ?, ?, 0)
        """,
        (order_id, hash_code(code), sent_at.isoformat(), expires_at.isoformat()),
    )


def find_active(connection: sqlite3.Connection, order_id: str) -> sqlite3.Row | None:
    """Return the latest unreplaced code row for an order."""
    return connection.execute(
        """
        SELECT code_hash, sent_at, expires_at, replaced
        FROM ownership_codes
        WHERE lower(order_id) = lower(?) AND replaced = 0
        ORDER BY code_id DESC
        LIMIT 1
        """,
        (order_id,),
    ).fetchone()


def save_grant(
    connection: sqlite3.Connection,
    session_id: str,
    order_id: str,
    granted_at: datetime,
) -> None:
    """Record that this session may read the order."""
    connection.execute(
        """
        INSERT INTO order_grants (session_id, order_id, granted_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id, order_id)
        DO UPDATE SET granted_at = excluded.granted_at
        """,
        (session_id, order_id, granted_at.isoformat()),
    )


def has_grant(connection: sqlite3.Connection, session_id: str, order_id: str) -> bool:
    """Return True when this session has already verified the order."""
    row = connection.execute(
        """
        SELECT 1
        FROM order_grants
        WHERE session_id = ? AND lower(order_id) = lower(?)
        """,
        (session_id, order_id),
    ).fetchone()
    return row is not None
