"""Order facts stay hidden until the email code for this session is accepted."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from emporio_agent.data.otp_repository import hash_code
from emporio_agent.mail.sender import InMemorySender
from emporio_agent.services.order_service import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from tests.unit.support import (
    insert_customer,
    insert_item,
    insert_order,
    insert_product,
    open_database,
)

_NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
_HIDDEN = (
    "email",
    "phone",
    "name",
    "city",
    "payment_method",
    "tracking_code",
    "estimated_delivery",
    "notes",
    "code",
)


class _FailingSender:
    """Raise on send so the service must hide every order field."""

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Fail without delivering the code."""
        raise OSError(f"mailbox down for {to_address}")


def _seed(
    tmp_path: Path, *, order_id: str = "Ab12", email: str | None = "buyer@example.com"
):
    """Load one customer, one product, and one order."""
    connection = open_database(tmp_path / "orders.db")
    insert_customer(
        connection, 3, email=email, name="Ada Customer", city="Campo Grande"
    )
    insert_product(
        connection,
        product_id=93,
        name="Piano de Cauda",
        price_brl="999.0",
        stock_quantity=1,
    )
    insert_order(connection, order_id, customer_id=3)
    insert_item(connection, order_id, 93, 1)
    connection.commit()
    return connection


def _codes(sender: InMemorySender) -> list[str]:
    """Return codes captured by the in-memory sender."""
    return [message["code"] for message in sender.messages]


def test_no_order_field_before_a_correct_code(tmp_path: Path) -> None:
    """Requesting a code reveals nothing about the order."""
    connection = _seed(tmp_path)
    sender = InMemorySender()

    result = request_order_code("Ab12", connection=connection, sender=sender, now=_NOW)

    assert result == {"code_sent": True}
    assert len(sender.messages) == 1
    assert "buyer@example.com" not in str(result)
    for key in ("status", "order_date", "items", "total_brl", *_HIDDEN):
        assert key not in result
    details = get_order_details(
        "Ab12",
        ["status"],
        session_id="session-a",
        connection=connection,
    )
    assert details == {"error": "not_owner"}


def test_status_only_after_the_correct_code(tmp_path: Path) -> None:
    """A status request after the code returns only status."""
    connection = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code(" ab12 ", connection=connection, sender=sender, now=_NOW)
    code = _codes(sender)[0]

    confirmed = confirm_order_code(
        "AB12",
        code,
        session_id="session-a",
        connection=connection,
        now=_NOW,
    )
    details = get_order_details(
        "Ab12",
        ["status"],
        session_id="session-a",
        connection=connection,
    )

    assert confirmed == {"verified": True}
    assert details == {"status": "delivered"}
    assert len(sender.messages) == 1


def test_later_fields_in_the_same_session_do_not_send_a_new_code(
    tmp_path: Path,
) -> None:
    """A later request returns only the asked keys and does not send another code."""
    connection = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", connection=connection, sender=sender, now=_NOW)
    code = _codes(sender)[0]
    confirm_order_code(
        "Ab12",
        code,
        session_id="session-a",
        connection=connection,
        now=_NOW,
    )

    details = get_order_details(
        "Ab12",
        ["order_date", "items", "total_brl"],
        session_id="session-a",
        connection=connection,
    )

    assert set(details) == {"order_date", "items", "total_brl"}
    assert details["order_date"] == "2025-10-15"
    assert details["total_brl"] == 11499
    assert details["items"] == [{"name": "Piano de Cauda", "quantity": 1}]
    assert "status" not in details
    assert len(sender.messages) == 1


def test_hidden_columns_never_appear(tmp_path: Path) -> None:
    """Email, phone, name, city, payment, tracking, delivery, and notes stay out."""
    connection = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", connection=connection, sender=sender, now=_NOW)
    confirm_order_code(
        "Ab12",
        _codes(sender)[0],
        session_id="session-a",
        connection=connection,
        now=_NOW,
    )
    details = get_order_details(
        "Ab12",
        ["status", "order_date", "items", "total_brl"],
        session_id="session-a",
        connection=connection,
    )

    rendered = str(details)
    for token in (
        "buyer@example.com",
        "Ada Customer",
        "Campo Grande",
        "pix",
        "BRTRACK",
        "leave at desk",
    ):
        assert token not in rendered
    for key in _HIDDEN:
        assert key not in details


def test_name_only_and_unknown_id_reveal_nothing(tmp_path: Path) -> None:
    """A person's name or an unknown id sends no code and no order field."""
    connection = _seed(tmp_path)
    sender = InMemorySender()

    by_name = request_order_code(
        "Ada Customer", connection=connection, sender=sender, now=_NOW
    )
    missing = request_order_code(
        "missing-id", connection=connection, sender=sender, now=_NOW
    )

    assert by_name == {"error": "not_found"}
    assert missing == {"error": "not_found"}
    assert sender.messages == []


def test_identifier_match_ignores_case_and_surrounding_spaces(tmp_path: Path) -> None:
    """Ab12 matches ab12 and the same id with surrounding spaces."""
    connection = _seed(tmp_path, order_id="Ab12")
    sender = InMemorySender()

    result = request_order_code(
        "  ab12  ", connection=connection, sender=sender, now=_NOW
    )

    assert result == {"code_sent": True}
    assert len(sender.messages) == 1


def test_duplicate_identifier_sends_no_code(tmp_path: Path) -> None:
    """More than one row for an identifier sends no code and returns no field."""
    connection = _seed(tmp_path, order_id="Ab12")
    insert_order(connection, "ab12", customer_id=3)
    connection.commit()
    sender = InMemorySender()

    result = request_order_code("AB12", connection=connection, sender=sender, now=_NOW)

    assert result == {"error": "ambiguous_order"}
    assert sender.messages == []
    assert "status" not in result


def test_missing_email_sends_no_code(tmp_path: Path) -> None:
    """An order without an email returns email_missing and sends nothing."""
    connection = _seed(tmp_path, email=None)
    sender = InMemorySender()

    result = request_order_code("Ab12", connection=connection, sender=sender, now=_NOW)

    assert result == {"error": "email_missing"}
    assert sender.messages == []


def test_code_is_stored_as_a_hash_and_expires_fifteen_minutes_later(
    tmp_path: Path,
) -> None:
    """Acceptance requires the hash, replaced false, and a time before expires_at."""
    connection = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", connection=connection, sender=sender, now=_NOW)
    code = _codes(sender)[0]
    row = connection.execute(
        "SELECT code_hash, replaced, sent_at, expires_at FROM ownership_codes"
    ).fetchone()

    assert row["code_hash"] == hash_code(code)
    assert row["code_hash"] != code
    assert row["replaced"] == 0
    assert row["expires_at"] == (_NOW + timedelta(minutes=15)).isoformat()
    confirmed = confirm_order_code(
        "Ab12",
        code,
        session_id="session-a",
        connection=connection,
        now=_NOW + timedelta(minutes=14),
    )
    assert confirmed == {"verified": True}


def test_a_newer_code_replaces_the_previous_one(tmp_path: Path) -> None:
    """A newer code sets the previous replaced flag and the old code is rejected."""
    connection = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", connection=connection, sender=sender, now=_NOW)
    first = _codes(sender)[0]
    request_order_code(
        "Ab12", connection=connection, sender=sender, now=_NOW + timedelta(minutes=1)
    )
    second = _codes(sender)[1]
    flags = connection.execute(
        "SELECT code_hash, replaced FROM ownership_codes ORDER BY code_id"
    ).fetchall()

    assert flags[0]["code_hash"] == hash_code(first)
    assert flags[0]["replaced"] == 1
    assert flags[1]["replaced"] == 0
    rejected = confirm_order_code(
        "Ab12",
        first,
        session_id="session-a",
        connection=connection,
        now=_NOW + timedelta(minutes=1),
    )
    assert rejected == {"error": "code_rejected"}
    accepted = confirm_order_code(
        "Ab12",
        second,
        session_id="session-a",
        connection=connection,
        now=_NOW + timedelta(minutes=1),
    )
    assert accepted == {"verified": True}


def test_wrong_expired_and_reused_codes_are_rejected(tmp_path: Path) -> None:
    """000000, an expired code, and the same code on another order are rejected."""
    connection = _seed(tmp_path, order_id="1")
    insert_customer(connection, 4, email="other@example.com", name="Other Person")
    insert_order(connection, "2", customer_id=4, status="pending", total_brl="10")
    connection.commit()
    sender = InMemorySender()
    request_order_code("1", connection=connection, sender=sender, now=_NOW)
    code = _codes(sender)[0]

    wrong = confirm_order_code(
        "1",
        "000000",
        session_id="session-a",
        connection=connection,
        now=_NOW,
    )
    expired = confirm_order_code(
        "1",
        code,
        session_id="session-a",
        connection=connection,
        now=_NOW + timedelta(minutes=15),
    )
    other_order = confirm_order_code(
        "2",
        code,
        session_id="session-a",
        connection=connection,
        now=_NOW,
    )

    assert wrong == {"error": "code_rejected"}
    assert expired == {"error": "code_rejected"}
    assert other_order == {"error": "code_rejected"}
    grant = connection.execute("SELECT COUNT(*) FROM order_grants").fetchone()[0]
    assert grant == 0
    details = get_order_details(
        "1", ["status"], session_id="session-a", connection=connection
    )
    assert details == {"error": "not_owner"}
    assert "status" not in str(wrong)


def test_sender_failure_reveals_nothing_and_creates_no_grant(tmp_path: Path) -> None:
    """A sender failure returns code_not_sent, no order field, and no grant."""
    connection = _seed(tmp_path)
    result = request_order_code(
        "Ab12",
        connection=connection,
        sender=_FailingSender(),
        now=_NOW,
    )

    assert result == {"error": "code_not_sent"}
    for key in ("status", "order_date", "items", "total_brl", "email", "code"):
        assert key not in result
    assert connection.execute("SELECT COUNT(*) FROM ownership_codes").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM order_grants").fetchone()[0] == 0
