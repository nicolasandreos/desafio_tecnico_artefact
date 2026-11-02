"""Deliver an ownership code without returning the address or the code."""

from __future__ import annotations

import html

import resend

from emporio_agent.config import Settings, load_settings
from emporio_agent.logging import log_failure


class InMemorySender:
    """Capture codes in memory for tests."""

    def __init__(self) -> None:
        """Start with an empty message list."""
        self.messages: list[dict[str, str]] = []

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Store one message. Callers must not put this payload in a tool result."""
        self.messages.append({"to": to_address, "code": code, "order_id": order_id})


class ResendSender:
    """Send the ownership code as HTML through Resend."""

    def __init__(self, settings: Settings) -> None:
        """Keep the Resend key and from address. They are not logged."""
        self._api_key = settings.resend_api_key or ""
        self._from_address = settings.resend_from or ""

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Send a short Portuguese HTML message containing the code."""
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


def build_sender() -> ResendSender:
    """Return the Resend sender. Both Resend settings are required."""
    settings = load_settings()
    if not settings.resend_api_key or not settings.resend_from:
        raise RuntimeError(
            "RESEND_API_KEY and RESEND_FROM are required to send the ownership code"
        )
    return ResendSender(settings)


def safe_send(sender: object, to_address: str, code: str, order_id: str) -> bool:
    """Send a code and log only the exception name when delivery fails."""
    try:
        sender.send(to_address, code, order_id)  # type: ignore[attr-defined]
    except Exception as exc:
        log_failure("code_not_sent", sender_error=type(exc).__name__)
        return False
    return True
