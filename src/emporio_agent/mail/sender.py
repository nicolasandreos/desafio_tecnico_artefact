"""Deliver an ownership code without returning the address or the code."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

import resend

from emporio_agent.config import Settings, load_settings
from emporio_agent.logging import log_failure


class InMemorySender:
    """Capture codes in memory for tests."""

    def __init__(self) -> None:
        """Start with an empty outbox."""
        self.messages: list[dict[str, str]] = []

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Store one message. Callers must not put this payload in a tool result."""
        self.messages.append({"to": to_address, "code": code, "order_id": order_id})


class OutboxSender:
    """Write the code to a local file that the chat does not read."""

    def __init__(self, folder: Path) -> None:
        """Store codes under folder."""
        self.folder = folder

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Write the order id and the code. The address is not written."""
        del to_address
        self.folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = self.folder / f"{order_id}-{stamp}.txt"
        path.write_text(f"order_id: {order_id}\ncode: {code}\n", encoding="utf-8")


class ResendSender:
    """Send the ownership code as HTML through Resend."""

    def __init__(self, settings: Settings) -> None:
        """Keep the Resend key and from address. They are not logged."""
        self._api_key = settings.resend_api_key or ""
        self._from_address = settings.resend_from or ""

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Send a short Portuguese HTML message containing the code."""
        if self._api_key == "" or self._from_address == "":
            raise RuntimeError("Resend is not configured")
        resend.api_key = self._api_key
        resend.Emails.send(
            {
                "from": self._from_address,
                "to": [to_address],
                "subject": f"Codigo do pedido {order_id}",
                "html": _ownership_html(order_id, code),
            }
        )


def _ownership_html(order_id: str, code: str) -> str:
    """Return the ownership message as HTML. Callers must not log this body."""
    safe_order = html.escape(order_id, quote=True)
    safe_code = html.escape(code, quote=True)
    return (
        "<p>Seu codigo de confirmacao do pedido "
        f"<strong>{safe_order}</strong> e <strong>{safe_code}</strong>. "
        "Ele expira em 15 minutos.</p>"
    )


def build_sender() -> InMemorySender | OutboxSender | ResendSender:
    """Return Resend when it is configured, otherwise the local outbox."""
    settings = load_settings()
    if settings.resend_api_key and settings.resend_from:
        return ResendSender(settings)
    return OutboxSender(settings.outbox_dir)


def safe_send(sender: object, to_address: str, code: str, order_id: str) -> bool:
    """Send a code and log only the exception name when delivery fails."""
    try:
        sender.send(to_address, code, order_id)  # type: ignore[attr-defined]
    except Exception as exc:
        log_failure("code_not_sent", sender_error=type(exc).__name__)
        return False
    return True
