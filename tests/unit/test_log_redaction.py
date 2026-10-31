"""Failure logs keep error codes and drop secrets."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from emporio_agent.data.ingest import ingest
from emporio_agent.knowledge.policy_knowledge import rebuild_policy_index
from emporio_agent.logging import get_logger, log_failure, redact
from emporio_agent.mail.sender import safe_send
from emporio_agent.services.order_service import request_order_code
from tests.unit.support import insert_customer, insert_order, open_database


class _Boom:
    """Fail with a message that contains an address and a code."""

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Raise an error that includes values the log must drop."""
        raise OSError(f"failed for {to_address} code {code}")


def test_redact_drops_api_keys_emails_and_six_digit_codes() -> None:
    """API keys, email addresses, and six-digit codes are removed from log text."""
    cleaned = redact(
        "key sk-abcDEF1234567890 resend re_abcDEF1234567890 "
        "email buyer@example.com phone (67) 99812-3456 code 123456"
    )

    assert "sk-abcDEF1234567890" not in cleaned
    assert "re_abcDEF1234567890" not in cleaned
    assert "buyer@example.com" not in cleaned
    assert "99812-3456" not in cleaned
    assert "123456" not in cleaned


def test_log_failure_drops_secret_fields(caplog: pytest.LogCaptureFixture) -> None:
    """Named secret fields are omitted and a leaked code is redacted."""
    logger = get_logger()
    logger.propagate = True
    with caplog.at_level(logging.ERROR, logger="emporio_agent"):
        log_failure(
            "missing_file",
            file_name="orders.csv",
            email="buyer@example.com",
            code="123456",
            api_key="sk-abcDEF1234567890",
        )

    assert "missing_file" in caplog.text
    assert "orders.csv" in caplog.text
    assert "buyer@example.com" not in caplog.text
    assert "123456" not in caplog.text
    assert "sk-abcDEF1234567890" not in caplog.text


def test_missing_csv_is_logged_without_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing CSV is logged with the file name and without credentials."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecretvalue1")
    monkeypatch.setenv("RESEND_API_KEY", "re_secretvalue123")
    get_logger().propagate = True
    with caplog.at_level(logging.ERROR, logger="emporio_agent"):
        with pytest.raises(FileNotFoundError, match="categories.csv"):
            ingest(data_dir=tmp_path)

    assert "missing_file" in caplog.text
    assert "categories.csv" in caplog.text
    assert "sk-supersecretvalue1" not in caplog.text
    assert "re_secretvalue123" not in caplog.text


def test_missing_policy_pdf_is_logged_without_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing policy PDF is logged with the file name and without credentials."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecretvalue1")
    get_logger().propagate = True
    missing = tmp_path / "políticas_da_loja.pdf"
    with caplog.at_level(logging.ERROR, logger="emporio_agent"):
        with pytest.raises(FileNotFoundError, match="políticas_da_loja.pdf"):
            rebuild_policy_index(missing)

    assert "missing_file" in caplog.text
    assert "políticas_da_loja.pdf" in caplog.text
    assert "sk-supersecretvalue1" not in caplog.text


def test_mail_sender_logs_the_error_name_only(caplog: pytest.LogCaptureFixture) -> None:
    """The mail sender logs the exception name and not the address or the code."""
    get_logger().propagate = True
    with caplog.at_level(logging.ERROR, logger="emporio_agent"):
        delivered = safe_send(_Boom(), "buyer@example.com", "123456", "1")

    assert delivered is False
    assert "code_not_sent" in caplog.text
    assert "OSError" in caplog.text
    assert "buyer@example.com" not in caplog.text
    assert "123456" not in caplog.text


def test_order_service_logs_the_order_id_and_not_the_code(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An order failure log contains the order id and the error code, not the digits."""
    connection = open_database(tmp_path / "orders.db")
    insert_customer(connection, 3, email="buyer@example.com")
    insert_order(connection, "77", customer_id=3)
    connection.commit()
    get_logger().propagate = True
    with caplog.at_level(logging.ERROR, logger="emporio_agent"):
        result = request_order_code(
            "77",
            connection=connection,
            sender=_Boom(),
            now=datetime(2026, 10, 31, tzinfo=timezone.utc),
        )

    assert result == {"error": "code_not_sent"}
    assert "code_not_sent" in caplog.text
    assert "order_id=77" in caplog.text
    assert "buyer@example.com" not in caplog.text
    assert "123456" not in caplog.text
