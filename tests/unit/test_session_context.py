"""A session keeps history and does not reuse another session's order grant."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from agno.db.in_memory import InMemoryDb
from agno.knowledge.knowledge import Knowledge

from emporio_agent.agent.assistant import build_agent
from emporio_agent.mail.sender import InMemorySender
from emporio_agent.services.order_service import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from tests.unit.support import reset_ownership_store, write_table

_NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _fresh_ownership_store() -> None:
    """Each test starts without a code or a grant from another test."""
    reset_ownership_store()


def test_agent_keeps_history_in_process_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The agent keeps history for this process in an in-memory session store."""
    monkeypatch.setattr(
        "emporio_agent.agent.assistant.ensure_policy_index",
        lambda: Knowledge(max_results=4),
    )
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    agent = build_agent()

    assert agent.add_history_to_context is True
    assert isinstance(agent.db, InMemoryDb)


def test_order_grant_does_not_transfer_to_another_session(tmp_path: Path) -> None:
    """A grant for one session_id returns not_owner for a different session_id."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "customers",
        [
            {
                "customer_id": 3,
                "name": "Ada Customer",
                "email": "buyer@example.com",
                "phone": "(67) 90000-0000",
                "city": "Campo Grande",
            }
        ],
    )
    write_table(
        folder,
        "orders",
        [
            {
                "order_id": "1",
                "customer_id": 3,
                "status": "delivered",
                "order_date": "2025-10-15",
                "total_brl": "10",
            }
        ],
    )
    sender = InMemorySender()
    request_order_code("1", data_dir=folder, sender=sender, now=_NOW)
    code = sender.messages[0]["code"]
    confirm_order_code(
        "1",
        code,
        session_id="session-a",
        data_dir=folder,
        now=_NOW,
    )

    other = get_order_details(
        "1", ["status"], session_id="session-b", data_dir=folder
    )
    same = get_order_details(
        "1", ["status"], session_id="session-a", data_dir=folder
    )

    assert other == {"error": "not_owner"}
    assert same == {"status": "delivered"}
