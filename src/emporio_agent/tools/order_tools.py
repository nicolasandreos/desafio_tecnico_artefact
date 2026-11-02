"""Validate order-tool arguments. A model-supplied session id is ignored."""

from __future__ import annotations

import re

from agno.run import RunContext

from emporio_agent.mail.sender import build_sender
from emporio_agent.services.order_service import (
    confirm_order_code as confirm_code,
)
from emporio_agent.services.order_service import (
    get_order_details as read_order,
)
from emporio_agent.services.order_service import (
    request_order_code as send_code,
)

_CODE = re.compile(r"\d{6}")
_FIELDS = {"status", "order_date", "items", "total_brl"}


def request_order_code(
    order_id: str,
    session_id: str | None = None,
    run_context: RunContext | None = None,
) -> dict[str, object]:
    """Send an ownership code for one order. The result contains no order facts."""
    del session_id, run_context
    if not isinstance(order_id, str) or order_id.strip() == "":
        return {"error": "invalid_input"}
    return send_code(order_id, sender=build_sender())


def confirm_order_code(
    order_id: str,
    code: str,
    session_id: str | None = None,
    run_context: RunContext | None = None,
) -> dict[str, object]:
    """Accept a six-digit code for this session. The result contains no order facts."""
    del session_id
    if not isinstance(order_id, str) or order_id.strip() == "":
        return {"error": "invalid_input"}
    if not isinstance(code, str) or _CODE.fullmatch(code) is None:
        return {"error": "invalid_input"}
    return confirm_code(
        order_id,
        code,
        session_id=_session_id(run_context),
    )


def get_order_details(
    order_id: str,
    fields: list[str],
    session_id: str | None = None,
    run_context: RunContext | None = None,
) -> dict[str, object]:
    """Return the requested allow-listed fields for an order this session verified."""
    del session_id
    if not isinstance(order_id, str) or order_id.strip() == "":
        return {"error": "invalid_input"}
    if not isinstance(fields, list) or not fields:
        return {"error": "invalid_input"}
    if any(not isinstance(field, str) or field not in _FIELDS for field in fields):
        return {"error": "invalid_input"}
    return read_order(
        order_id,
        fields,
        session_id=_session_id(run_context),
    )


def _session_id(run_context: RunContext | None) -> str:
    """Return the session id from the run, never from model input."""
    if run_context is None:
        return ""
    value = getattr(run_context, "session_id", None)
    if isinstance(value, str):
        return value
    return ""
