"""Verify order ownership and return only the requested allow-listed fields."""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from emporio_agent.data import otp_repository
from emporio_agent.data.csv_tables import (
    READ_FAILURES,
    as_number,
    cell_text,
    read_table,
)
from emporio_agent.data.values import recorded_number
from emporio_agent.logging import log_failure
from emporio_agent.mail.sender import safe_send

_CODE = re.compile(r"\d{6}")
_ALLOWED = ("status", "order_date", "items", "total_brl")
_MAX_ORDER_ID = 64
_Row = dict[str, object]
_Result = dict[str, object]
_Load = Callable[[str, Path | None], list[_Row]]


def request_order_code(
    order_id: str,
    *,
    sender: object,
    now: datetime | None = None,
    data_dir: Path | None = None,
) -> _Result:
    """Send a code when one order has an email. No order facts are returned."""
    normalized = _order_id(order_id)
    if normalized is None:
        return {"error": "invalid_input"}
    row, error = _one_order(normalized, data_dir, _match_rows)
    if error is not None:
        return error
    assert row is not None
    email = str(row["email"] or "").strip()
    if not email:
        return _fail("email_missing", normalized)
    code = _new_code()
    sent_at = _clock(now)
    stored_id = str(row["order_id"])
    if not safe_send(sender, email, code, stored_id):
        log_failure("code_not_sent", order_id=stored_id, sender_error="send_failed")
        return {"error": "code_not_sent"}
    otp_repository.store_code(stored_id, code, sent_at)
    return {"code_sent": True}


def confirm_order_code(
    order_id: str,
    code: str,
    *,
    session_id: str,
    now: datetime | None = None,
    data_dir: Path | None = None,
) -> _Result:
    """Accept a current code and grant this session. No order field is returned."""
    normalized = _order_id(order_id)
    if (
        normalized is None
        or not isinstance(session_id, str)
        or not session_id
        or not isinstance(code, str)
        or _CODE.fullmatch(code) is None
    ):
        return {"error": "invalid_input"}
    row, error = _one_order(normalized, data_dir, _detail_rows)
    if error is not None:
        return error
    assert row is not None
    stored_id = str(row["order_id"])
    moment = _clock(now)
    reason = _rejection_reason(stored_id, code, moment)
    if reason is not None:
        log_failure("code_rejected", order_id=stored_id, reason=reason)
        return {"error": "code_rejected"}
    otp_repository.save_grant(session_id, stored_id, moment)
    return {"verified": True}


def get_order_details(
    order_id: str,
    fields: list[str],
    *,
    session_id: str,
    data_dir: Path | None = None,
) -> _Result:
    """Return only the requested allow-listed fields after a grant for this session."""
    normalized = _order_id(order_id)
    selected = _fields(fields)
    if (
        normalized is None
        or selected is None
        or not isinstance(session_id, str)
        or not session_id
    ):
        return {"error": "invalid_input"}
    row, error = _one_order(normalized, data_dir, _detail_rows)
    if error is not None:
        return error
    assert row is not None
    stored_id = str(row["order_id"])
    if not otp_repository.has_grant(session_id, stored_id):
        return _fail("not_owner", stored_id)
    items: list[_Row] = []
    if "items" in selected:
        try:
            items = _item_rows(stored_id, data_dir)
        except READ_FAILURES:
            return _fail("unavailable", stored_id)
    values = {
        "status": row["status"],
        "order_date": row["order_date"],
        "items": items,
        "total_brl": recorded_number(row["total_brl"]),
    }
    return {name: values[name] for name in _ALLOWED if name in selected}


def _one_order(
    order_id: str,
    data_dir: Path | None,
    load: _Load,
) -> tuple[_Row | None, _Result | None]:
    """Return the single matching row, or a logged error result."""
    try:
        rows = load(order_id, data_dir)
    except READ_FAILURES:
        return None, _fail("unavailable", order_id)
    if len(rows) == 1:
        return rows[0], None
    code = "not_found" if not rows else "ambiguous_order"
    return None, _fail(code, order_id)


def _fail(code: str, order_id: str) -> _Result:
    """Log one order failure and return its error code."""
    log_failure(code, order_id=order_id)
    return {"error": code}


def _match_rows(order_id: str, data_dir: Path | None) -> list[_Row]:
    """Return order id and email for one identifier from the CSVs."""
    orders = _orders(order_id, data_dir)
    if orders.empty:
        return []
    customers = as_number(read_table("customers", data_dir), "customer_id")
    frame = as_number(orders, "customer_id").merge(
        customers[["customer_id", "email"]],
        on="customer_id",
        how="left",
    )
    return [
        {"order_id": cell_text(row["order_id"]), "email": cell_text(row["email"])}
        for row in frame.to_dict(orient="records")
    ]


def _detail_rows(order_id: str, data_dir: Path | None) -> list[_Row]:
    """Return the allow-listed order columns for one identifier."""
    return [
        {
            "order_id": cell_text(row["order_id"]),
            "status": cell_text(row["status"]),
            "order_date": cell_text(row["order_date"]),
            "total_brl": row["total_brl"],
        }
        for row in _orders(order_id, data_dir).to_dict(orient="records")
    ]


def _item_rows(order_id: str, data_dir: Path | None) -> list[_Row]:
    """Return item name and quantity. Line price is not read and not computed."""
    items = read_table("order_items", data_dir)
    if items.empty:
        return []
    products = as_number(read_table("products", data_dir), "product_id")
    frame = as_number(items, "product_id").merge(
        products[["product_id", "name"]],
        on="product_id",
        how="left",
    )
    same = frame["order_id"].map(_casefold) == order_id.casefold()
    return [
        {"name": cell_text(row["name"]), "quantity": recorded_number(row["quantity"])}
        for row in frame.loc[same].to_dict(orient="records")
    ]


def _orders(order_id: str, data_dir: Path | None) -> pd.DataFrame:
    """Return CSV order rows whose identifier matches, ignoring case."""
    orders = read_table("orders", data_dir)
    if orders.empty:
        return orders
    same = orders["order_id"].map(_casefold) == order_id.casefold()
    return orders.loc[same]


def _casefold(value: object) -> str:
    """Return a comparable identifier, or an empty string when the cell is empty."""
    text = cell_text(value)
    return text.casefold() if text else ""


def _rejection_reason(order_id: str, code: str, now: datetime) -> str | None:
    """Return why a code is rejected, or None when it can be accepted."""
    row = otp_repository.find_active(order_id)
    if row is None or row.code_hash != otp_repository.hash_code(code):
        return "mismatch"
    return "expired" if now >= row.expires_at else None


def _order_id(value: object) -> str | None:
    """Return a trimmed order id, or None when it is missing or too long."""
    text = value.strip() if isinstance(value, str) else ""
    return text if text and len(text) <= _MAX_ORDER_ID else None


def _fields(value: object) -> list[str] | None:
    """Return a non-empty allow-listed field list, or None."""
    if not isinstance(value, list) or not value:
        return None
    if any(not isinstance(item, str) or item not in _ALLOWED for item in value):
        return None
    return list(dict.fromkeys(value))


def _new_code() -> str:
    """Return a six-digit code other than 000000."""
    code = "000000"
    while code == "000000":
        code = f"{secrets.randbelow(1_000_000):06d}"
    return code


def _clock(now: datetime | None) -> datetime:
    """Return an aware UTC timestamp."""
    moment = now or datetime.now(timezone.utc)
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
