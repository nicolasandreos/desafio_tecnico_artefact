"""Resend delivers the ownership code as HTML and hides it from the result."""

import logging
from pathlib import Path

import pytest

from emporio_agent.config import Settings
from emporio_agent.logging import get_logger
from emporio_agent.mail.sender import (
    OutboxSender,
    ResendSender,
    build_sender,
    safe_send,
)


def _settings(**overrides: object) -> Settings:
    """Return settings for a mail sender. Secrets stay on the object."""
    values: dict[str, object] = {
        "openai_api_key": None,
        "openai_model": None,
        "os_security_key": None,
        "resend_api_key": "re_testkeyvalue1",
        "resend_from": "loja@example.com",
        "data_dir": Path("data"),
        "sqlite_path": Path("var/emporio.db"),
        "session_db_path": Path("var/sessions.db"),
        "chroma_path": Path("var/chroma"),
        "outbox_dir": Path("var/outbox"),
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_resend_sender_posts_html(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured sender calls Resend with an HTML body and returns nothing."""
    captured: dict[str, object] = {}

    def _send(params: dict[str, object]) -> dict[str, str]:
        captured.update(params)
        return {"id": "email_1"}

    monkeypatch.setattr("emporio_agent.mail.sender.resend.Emails.send", _send)
    sender = ResendSender(_settings())

    sender.send("buyer@example.com", "123456", "A<b>1")

    assert captured["from"] == "loja@example.com"
    assert captured["to"] == ["buyer@example.com"]
    assert captured["subject"] == "Codigo do pedido A<b>1"
    html = str(captured["html"])
    assert "<p>" in html
    assert "<strong>123456</strong>" in html
    assert "A&lt;b&gt;1" in html
    assert "buyer@example.com" not in html
    assert "re_testkeyvalue1" not in html


def test_resend_failure_logs_the_error_name_only(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A Resend failure returns false and logs the exception name only."""

    def _send(params: dict[str, object]) -> None:
        del params
        raise OSError("failed for buyer@example.com code 123456")

    monkeypatch.setattr("emporio_agent.mail.sender.resend.Emails.send", _send)
    get_logger().propagate = True
    with caplog.at_level(logging.ERROR, logger="emporio_agent"):
        delivered = safe_send(
            ResendSender(_settings()),
            "buyer@example.com",
            "123456",
            "1",
        )

    assert delivered is False
    assert "code_not_sent" in caplog.text
    assert "OSError" in caplog.text
    assert "buyer@example.com" not in caplog.text
    assert "123456" not in caplog.text
    assert "re_testkeyvalue1" not in caplog.text


def test_build_sender_uses_resend_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both Resend settings select the Resend sender."""
    monkeypatch.setattr(
        "emporio_agent.mail.sender.load_settings",
        lambda: _settings(),
    )

    assert isinstance(build_sender(), ResendSender)


def test_build_sender_uses_the_outbox_without_resend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing Resend settings keep the local outbox."""
    monkeypatch.setattr(
        "emporio_agent.mail.sender.load_settings",
        lambda: _settings(
            resend_api_key=None,
            resend_from=None,
            outbox_dir=tmp_path,
        ),
    )

    sender = build_sender()

    assert isinstance(sender, OutboxSender)
