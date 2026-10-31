"""Deliver an ownership code without returning the address or the code."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timezone

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


class SmtpSender:
    """Send the code through optional SMTP settings."""

    def __init__(self, settings: Settings) -> None:
        """Keep SMTP settings on the sender. They are not logged."""
        self._settings = settings

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Send a short Portuguese message containing the code."""
        message = EmailMessage()
        message["From"] = self._settings.smtp_user or "emporio@localhost"
        message["To"] = to_address
        message["Subject"] = f"Codigo do pedido {order_id}"
        message.set_content(
            f"Seu codigo de confirmacao do pedido e {code}. Ele expira em 15 minutos."
        )
        host = self._settings.smtp_host or ""
        port = int(self._settings.smtp_port or "587")
        try:
            with smtplib.SMTP(host, port, timeout=30) as client:
                client.starttls()
                if self._settings.smtp_user and self._settings.smtp_password:
                    client.login(self._settings.smtp_user, self._settings.smtp_password)
                client.send_message(message)
        except Exception as exc:
            log_failure("code_not_sent", sender_error=type(exc).__name__)
            raise


def build_sender() -> InMemorySender | OutboxSender | SmtpSender:
    """Return SMTP when it is configured, otherwise the local outbox."""
    settings = load_settings()
    if settings.smtp_host:
        return SmtpSender(settings)
    return OutboxSender(settings.outbox_dir)


def safe_send(sender: object, to_address: str, code: str, order_id: str) -> bool:
    """Send a code and log only the exception name when delivery fails."""
    try:
        sender.send(to_address, code, order_id)  # type: ignore[attr-defined]
    except Exception as exc:
        log_failure("code_not_sent", sender_error=type(exc).__name__)
        return False
    return True
