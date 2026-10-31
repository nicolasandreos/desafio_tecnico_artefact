"""A session keeps history and does not reuse another session's order grant."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from emporio_agent.agent.assistant import build_agent
from emporio_agent.data.connection import connect
from emporio_agent.mail.sender import InMemorySender
from emporio_agent.services.order_service import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from tests.unit.support import insert_customer, insert_order, open_database

_NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def test_agent_keeps_history_in_the_session_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The agent is built with history in context and a session SqliteDb."""
    session_path = tmp_path / "sessions.db"
    operational_path = tmp_path / "emporio.db"
    monkeypatch.setenv("SESSION_DB_PATH", str(session_path))
    monkeypatch.setenv("SQLITE_PATH", str(operational_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-testkey12345678")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4")

    agent = build_agent()

    assert agent.add_history_to_context is True
    assert type(agent.db).__name__ == "SqliteDb"
    assert Path(agent.db.db_file).resolve() == session_path.resolve()
    assert Path(agent.db.db_file).resolve() != operational_path.resolve()


def test_order_grant_does_not_transfer_to_another_session(tmp_path: Path) -> None:
    """A grant for one session_id returns not_owner for a different session_id."""
    connection = open_database(tmp_path / "orders.db")
    insert_customer(connection, 3, email="buyer@example.com")
    insert_order(connection, "1", customer_id=3, status="delivered")
    connection.commit()
    sender = InMemorySender()
    request_order_code("1", connection=connection, sender=sender, now=_NOW)
    code = sender.messages[0]["code"]
    confirm_order_code(
        "1", code, session_id="session-a", connection=connection, now=_NOW
    )

    other = get_order_details(
        "1", ["status"], session_id="session-b", connection=connection
    )
    same = get_order_details(
        "1", ["status"], session_id="session-a", connection=connection
    )

    assert other == {"error": "not_owner"}
    assert same == {"status": "delivered"}


def test_session_database_cannot_be_opened_as_operational(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catalog and order access refuse the session database path."""
    session_path = tmp_path / "sessions.db"
    monkeypatch.setenv("SESSION_DB_PATH", str(session_path))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "emporio.db"))

    with pytest.raises(ValueError):
        connect(session_path, create=True)
