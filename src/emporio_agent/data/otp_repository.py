"""Store ownership codes and grants in process memory.

The raw code is never written. This state dies with the process.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class _StoredCode:
    """One sent code. The raw digits are not a field."""

    order_id: str
    code_hash: str
    sent_at: datetime
    expires_at: datetime
    replaced: bool = False


@dataclass(frozen=True)
class ActiveCode:
    """Latest unreplaced ownership code for one order."""

    code_hash: str
    sent_at: datetime
    expires_at: datetime
    replaced: bool


_codes: list[_StoredCode] = []
_grants: dict[tuple[str, str], datetime] = {}


def hash_code(code: str) -> str:
    """Return the SHA-256 hex digest of a six-digit code."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def store_code(order_id: str, code: str, sent_at: datetime) -> None:
    """Replace the previous code and store the new hash for 15 minutes."""
    key = order_id.casefold()
    for row in _codes:
        if row.order_id.casefold() == key and not row.replaced:
            row.replaced = True
    _codes.append(
        _StoredCode(
            order_id=order_id,
            code_hash=hash_code(code),
            sent_at=sent_at,
            expires_at=sent_at + timedelta(minutes=15),
        )
    )


def find_active(order_id: str) -> ActiveCode | None:
    """Return the latest unreplaced code for an order."""
    key = order_id.casefold()
    for row in reversed(_codes):
        if row.order_id.casefold() == key and not row.replaced:
            return ActiveCode(
                code_hash=row.code_hash,
                sent_at=row.sent_at,
                expires_at=row.expires_at,
                replaced=row.replaced,
            )
    return None


def save_grant(session_id: str, order_id: str, granted_at: datetime) -> None:
    """Record that this session may read the order."""
    _grants[(session_id, order_id.casefold())] = granted_at


def has_grant(session_id: str, order_id: str) -> bool:
    """Return True when this session has already verified the order."""
    return (session_id, order_id.casefold()) in _grants
