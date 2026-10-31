"""Verify order ownership and return only the requested allow-listed fields."""

from __future__ import annotations

import re
import secrets
import sqlite3
from datetime import datetime, timezone

from emporio_agent.data import order_repository, otp_repository
from emporio_agent.logging import log_failure
from emporio_agent.mail.sender import safe_send

_CODE = re.compile(r"\d{6}")
_ALLOWED_FIELDS = ("status", "order_date", "items", "total_brl")
_MAX_ORDER_ID = 64


def request_order_code(
    order_id: str,
    *,
    connection: sqlite3.Connection,
    sender: object,
    now: datetime | None = None,
) -> dict[str, object]:
    """Send a code when one order has an email. No order facts are returned."""
    normalized = _order_id(order_id)
    if normalized is None:
        return {"error": "invalid_input"}
    try:
        matches = order_repository.find_matches(connection, normalized)
    except sqlite3.Error:
        log_failure("unavailable", order_id=normalized)
        return {"error": "unavailable"}
    if len(matches) == 0:
        log_failure("not_found", order_id=normalized)
        return {"error": "not_found"}
    if len(matches) > 1:
        log_failure("ambiguous_order", order_id=normalized)
        return {"error": "ambiguous_order"}
    email = matches[0]["email"]
    if email is None or str(email).strip() == "":
        log_failure("email_missing", order_id=normalized)
        return {"error": "email_missing"}
    code = _new_code()
    sent_at = _clock(now)
    stored_id = str(matches[0]["order_id"])
    if not safe_send(sender, str(email), code, stored_id):
        log_failure("code_not_sent", order_id=stored_id, sender_error="send_failed")
        return {"error": "code_not_sent"}
    otp_repository.store_code(connection, stored_id, code, sent_at)
    connection.commit()
    return {"code_sent": True}


def confirm_order_code(
    order_id: str,
    code: str,
    *,
    session_id: str,
    connection: sqlite3.Connection,
    now: datetime | None = None,
) -> dict[str, object]:
    """Accept a current code and grant this session. No order field is returned."""
    normalized = _order_id(order_id)
    if normalized is None or not isinstance(session_id, str) or session_id == "":
        return {"error": "invalid_input"}
    if not isinstance(code, str) or _CODE.fullmatch(code) is None:
        return {"error": "invalid_input"}
    try:
        matches = order_repository.find_details(connection, normalized)
    except sqlite3.Error:
        log_failure("unavailable", order_id=normalized)
        return {"error": "unavailable"}
    if len(matches) == 0:
        log_failure("not_found", order_id=normalized)
        return {"error": "not_found"}
    if len(matches) > 1:
        log_failure("ambiguous_order", order_id=normalized)
        return {"error": "ambiguous_order"}
    stored_id = str(matches[0]["order_id"])
    reason = _rejection_reason(connection, stored_id, code, _clock(now))
    if reason is not None:
        log_failure("code_rejected", order_id=stored_id, reason=reason)
        return {"error": "code_rejected"}
    otp_repository.save_grant(connection, session_id, stored_id, _clock(now))
    connection.commit()
    return {"verified": True}


def get_order_details(
    order_id: str,
    fields: list[str],
    *,
    session_id: str,
    connection: sqlite3.Connection,
) -> dict[str, object]:
    """Return only the requested allow-listed fields after a grant for this session."""
    normalized = _order_id(order_id)
    selected = _fields(fields)
    if (
        normalized is None
        or selected is None
        or not isinstance(session_id, str)
        or session_id == ""
    ):
        return {"error": "invalid_input"}
    try:
        matches = order_repository.find_details(connection, normalized)
    except sqlite3.Error:
        log_failure("unavailable", order_id=normalized)
        return {"error": "unavailable"}
    if len(matches) == 0:
        log_failure("not_found", order_id=normalized)
        return {"error": "not_found"}
    if len(matches) > 1:
        log_failure("ambiguous_order", order_id=normalized)
        return {"error": "ambiguous_order"}
    stored_id = str(matches[0]["order_id"])
    if not otp_repository.has_grant(connection, session_id, stored_id):
        log_failure("not_owner", order_id=stored_id)
        return {"error": "not_owner"}
    items = (
        order_repository.find_items(connection, stored_id)
        if "items" in selected
        else []
    )
    return order_repository.order_payload(matches[0], selected, items)


def _rejection_reason(
    connection: sqlite3.Connection,
    order_id: str,
    code: str,
    now: datetime,
) -> str | None:
    """Return why a code is rejected, or None when it can be accepted."""
    row = otp_repository.find_active(connection, order_id)
    if row is None or row["code_hash"] != otp_repository.hash_code(code):
        return "mismatch"
    if row["replaced"]:
        return "replaced"
    expires_at = datetime.fromisoformat(str(row["expires_at"]))
    if now >= expires_at:
        return "expired"
    return None


def _order_id(value: object) -> str | None:
    """Return a trimmed order id, or None when it is missing or too long."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text == "" or len(text) > _MAX_ORDER_ID:
        return None
    return text


def _fields(value: object) -> list[str] | None:
    """Return a non-empty allow-listed field list, or None."""
    if not isinstance(value, list) or not value:
        return None
    if any(not isinstance(item, str) or item not in _ALLOWED_FIELDS for item in value):
        return None
    return list(dict.fromkeys(value))


def _new_code() -> str:
    """Return a six-digit code other than 000000."""
    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        if code != "000000":
            return code


def _clock(now: datetime | None) -> datetime:
    """Return an aware UTC timestamp."""
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now
