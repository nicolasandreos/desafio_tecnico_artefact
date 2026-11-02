"""Order facts stay hidden until the email code for this session is accepted."""

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from emporio_agent.data import otp_repository
from emporio_agent.data.otp_repository import hash_code
from emporio_agent.mail.sender import InMemorySender
from emporio_agent.services.order_service import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from tests.unit.support import reset_ownership_store, write_table

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
_ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "status",
    "total_brl",
    "payment_method",
    "tracking_code",
    "estimated_delivery",
    "notes",
]


@pytest.fixture(autouse=True)
def _fresh_ownership_store() -> None:
    """Each test starts without a code or a grant from another test."""
    reset_ownership_store()


class _FailingSender:
    """Raise on send so the service must hide every order field."""

    def send(self, to_address: str, code: str, order_id: str) -> None:
        """Fail without delivering the code."""
        raise OSError(f"mailbox down for {to_address}")


def _seed(
    tmp_path: Path, *, order_id: str = "Ab12", email: str | None = "buyer@example.com"
) -> Path:
    """Write one customer, one product, and one order."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "customers",
        [
            {
                "customer_id": 3,
                "name": "Ada Customer",
                "phone": "(67) 90000-0000",
                "email": email,
                "city": "Campo Grande",
            }
        ],
    )
    write_table(
        folder,
        "products",
        [
            {
                "product_id": 93,
                "name": "Piano de Cauda",
                "price_brl": "999.0",
                "stock_quantity": 1,
                "status": "active",
            }
        ],
    )
    write_table(folder, "orders", [_order_row(order_id, customer_id=3)])
    write_table(
        folder,
        "order_items",
        [{"order_id": order_id, "product_id": 93, "quantity": 1}],
    )
    return folder


def _order_row(
    order_id: str, *, customer_id: int, **overrides: object
) -> dict[str, object]:
    """Return one order CSV row, including columns the customer must not see."""
    row: dict[str, object] = {
        "order_id": order_id,
        "customer_id": customer_id,
        "order_date": "2025-10-15",
        "status": "delivered",
        "total_brl": "11499",
        "payment_method": "pix",
        "tracking_code": "BRTRACK",
        "estimated_delivery": "2025-10-25",
        "notes": "leave at desk",
    }
    row.update(overrides)
    return row


def _append(folder: Path, table: str, row: dict[str, object]) -> None:
    """Add one CSV row beside the rows already written for this test."""
    import pandas as pd

    from emporio_agent.data.csv_tables import TABLE_FILES

    path = folder / TABLE_FILES[table]
    frame = pd.read_csv(path, dtype=str)
    extra = pd.DataFrame([row]).astype(str)
    pd.concat([frame, extra], ignore_index=True).to_csv(path, index=False)


def _codes(sender: InMemorySender) -> list[str]:
    """Return codes captured by the in-memory sender."""
    return [message["code"] for message in sender.messages]


def test_no_order_field_before_a_correct_code(tmp_path: Path) -> None:
    """Requesting a code reveals nothing about the order."""
    folder = _seed(tmp_path)
    sender = InMemorySender()

    result = request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)

    assert result == {"code_sent": True}
    assert len(sender.messages) == 1
    assert "buyer@example.com" not in str(result)
    for key in ("status", "order_date", "items", "total_brl", *_HIDDEN):
        assert key not in result
    details = get_order_details(
        "Ab12", ["status"], session_id="session-a", data_dir=folder
    )
    assert details == {"error": "not_owner"}


def test_status_only_after_the_correct_code(tmp_path: Path) -> None:
    """A status request after the code returns only status."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code(" ab12 ", sender=sender, now=_NOW, data_dir=folder)
    code = _codes(sender)[0]

    confirmed = confirm_order_code(
        "AB12", code, session_id="session-a", now=_NOW, data_dir=folder
    )
    details = get_order_details(
        "Ab12", ["status"], session_id="session-a", data_dir=folder
    )

    assert confirmed == {"verified": True}
    assert details == {"status": "delivered"}
    assert len(sender.messages) == 1


def test_later_fields_in_the_same_session_do_not_send_a_new_code(
    tmp_path: Path,
) -> None:
    """A later request returns only the asked keys and does not send another code."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    code = _codes(sender)[0]
    confirm_order_code(
        "Ab12", code, session_id="session-a", now=_NOW, data_dir=folder
    )

    details = get_order_details(
        "Ab12",
        ["order_date", "items", "total_brl"],
        session_id="session-a",
        data_dir=folder,
    )

    assert set(details) == {"order_date", "items", "total_brl"}
    assert details["order_date"] == "2025-10-15"
    assert details["total_brl"] == 11499
    assert details["items"] == [{"name": "Piano de Cauda", "quantity": 1}]
    assert "status" not in details
    assert len(sender.messages) == 1


def test_other_field_names_return_no_order_field(tmp_path: Path) -> None:
    """Email and payment method are invalid and reveal no order field."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    confirm_order_code(
        "Ab12",
        _codes(sender)[0],
        session_id="session-a",
        now=_NOW,
        data_dir=folder,
    )

    for field in ("email", "payment_method"):
        result = get_order_details(
            "Ab12", [field], session_id="session-a", data_dir=folder
        )
        assert result == {"error": "invalid_input"}
        assert "buyer@example.com" not in str(result)
        assert "pix" not in str(result)
        for key in ("status", "order_date", "items", "total_brl", field):
            assert key not in result


def test_hidden_columns_never_appear(tmp_path: Path) -> None:
    """Email, phone, name, city, payment, tracking, delivery, and notes stay out."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    confirm_order_code(
        "Ab12",
        _codes(sender)[0],
        session_id="session-a",
        now=_NOW,
        data_dir=folder,
    )
    details = get_order_details(
        "Ab12",
        ["status", "order_date", "items", "total_brl"],
        session_id="session-a",
        data_dir=folder,
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
    folder = _seed(tmp_path)
    sender = InMemorySender()

    by_name = request_order_code(
        "Ada Customer", sender=sender, now=_NOW, data_dir=folder
    )
    missing = request_order_code(
        "missing-id", sender=sender, now=_NOW, data_dir=folder
    )

    assert by_name == {"error": "not_found"}
    assert missing == {"error": "not_found"}
    assert by_name != {"error": "unavailable"}
    assert sender.messages == []


def test_identifier_match_ignores_case_and_surrounding_spaces(tmp_path: Path) -> None:
    """Ab12 matches ab12 and the same id with surrounding spaces."""
    folder = _seed(tmp_path, order_id="Ab12")
    sender = InMemorySender()

    result = request_order_code(
        "  ab12  ", sender=sender, now=_NOW, data_dir=folder
    )

    assert result == {"code_sent": True}
    assert len(sender.messages) == 1


def test_duplicate_identifier_sends_no_code(tmp_path: Path) -> None:
    """More than one row for an identifier sends no code and returns no field."""
    folder = _seed(tmp_path, order_id="Ab12")
    _append(folder, "orders", _order_row("ab12", customer_id=3))
    sender = InMemorySender()

    result = request_order_code("AB12", sender=sender, now=_NOW, data_dir=folder)

    assert result == {"error": "ambiguous_order"}
    assert sender.messages == []
    assert "status" not in result


def test_missing_email_sends_no_code(tmp_path: Path) -> None:
    """An order without an email returns email_missing and sends nothing."""
    folder = _seed(tmp_path, email=None)
    sender = InMemorySender()

    result = request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)

    assert result == {"error": "email_missing"}
    assert sender.messages == []


def test_missing_order_file_is_unavailable(tmp_path: Path) -> None:
    """A missing order file is unavailable, which is distinct from no match."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "customers",
        [{"customer_id": 3, "name": "Ada", "email": "buyer@example.com"}],
    )
    sender = InMemorySender()

    result = request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)

    assert result == {"error": "unavailable"}
    assert result != {"error": "not_found"}


def test_present_order_file_with_no_row_matches_nothing(tmp_path: Path) -> None:
    """A present order file with no row means nothing matched."""
    folder = tmp_path / "data"
    write_table(folder, "orders", [], columns=_ORDER_COLUMNS)
    sender = InMemorySender()

    result = request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)

    assert result == {"error": "not_found"}
    assert result != {"error": "unavailable"}


def test_code_is_stored_as_a_hash_and_expires_fifteen_minutes_later(
    tmp_path: Path,
) -> None:
    """Acceptance requires the hash, replaced false, and a time before expires_at."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    code = _codes(sender)[0]
    row = otp_repository.find_active("ab12")

    assert row is not None
    assert row.code_hash == hash_code(code)
    assert row.code_hash != code
    assert row.replaced is False
    assert row.expires_at == _NOW + timedelta(minutes=15)
    assert "code" not in otp_repository._StoredCode.__dataclass_fields__
    confirmed = confirm_order_code(
        "Ab12",
        code,
        session_id="session-a",
        now=_NOW + timedelta(minutes=14),
        data_dir=folder,
    )
    assert confirmed == {"verified": True}


def test_a_newer_code_replaces_the_previous_one(tmp_path: Path) -> None:
    """A newer code sets the previous replaced flag and the old code is rejected."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    first = _codes(sender)[0]
    request_order_code(
        "Ab12",
        sender=sender,
        now=_NOW + timedelta(minutes=1),
        data_dir=folder,
    )
    second = _codes(sender)[1]

    assert otp_repository._codes[0].code_hash == hash_code(first)
    assert otp_repository._codes[0].replaced is True
    assert otp_repository._codes[1].replaced is False
    rejected = confirm_order_code(
        "Ab12",
        first,
        session_id="session-a",
        now=_NOW + timedelta(minutes=1),
        data_dir=folder,
    )
    assert rejected == {"error": "code_rejected"}
    assert otp_repository.has_grant("session-a", "Ab12") is False
    accepted = confirm_order_code(
        "Ab12",
        second,
        session_id="session-a",
        now=_NOW + timedelta(minutes=1),
        data_dir=folder,
    )
    assert accepted == {"verified": True}


def test_wrong_expired_and_reused_codes_are_rejected(tmp_path: Path) -> None:
    """000000, an expired code, and the same code on another order are rejected."""
    folder = _seed(tmp_path, order_id="1")
    _append(
        folder,
        "customers",
        {
            "customer_id": 4,
            "name": "Other Person",
            "phone": "(67) 90000-0001",
            "email": "other@example.com",
            "city": "Campo Grande",
        },
    )
    _append(
        folder,
        "orders",
        _order_row("2", customer_id=4, status="pending", total_brl="10"),
    )
    sender = InMemorySender()
    request_order_code("1", sender=sender, now=_NOW, data_dir=folder)
    code = _codes(sender)[0]

    wrong = confirm_order_code(
        "1", "000000", session_id="session-a", now=_NOW, data_dir=folder
    )
    again = confirm_order_code(
        "1", "000000", session_id="session-a", now=_NOW, data_dir=folder
    )
    expired = confirm_order_code(
        "1",
        code,
        session_id="session-a",
        now=_NOW + timedelta(minutes=15),
        data_dir=folder,
    )
    other_order = confirm_order_code(
        "2", code, session_id="session-a", now=_NOW, data_dir=folder
    )

    assert wrong == {"error": "code_rejected"}
    assert again == {"error": "code_rejected"}
    assert expired == {"error": "code_rejected"}
    assert other_order == {"error": "code_rejected"}
    assert otp_repository.has_grant("session-a", "1") is False
    assert "attempts" not in otp_repository._StoredCode.__dataclass_fields__
    details = get_order_details(
        "1", ["status"], session_id="session-a", data_dir=folder
    )
    assert details == {"error": "not_owner"}
    assert "status" not in str(wrong)


def test_a_different_session_is_not_the_owner(tmp_path: Path) -> None:
    """A grant for one session does not reveal the order to another session."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    confirm_order_code(
        "Ab12",
        _codes(sender)[0],
        session_id="session-a",
        now=_NOW,
        data_dir=folder,
    )

    other = get_order_details(
        "Ab12", ["status"], session_id="session-b", data_dir=folder
    )

    assert other == {"error": "not_owner"}
    assert "delivered" not in str(other)


def test_a_new_process_does_not_keep_the_grant(tmp_path: Path) -> None:
    """A grant in this process is absent in a new Python process."""
    folder = _seed(tmp_path)
    sender = InMemorySender()
    request_order_code("Ab12", sender=sender, now=_NOW, data_dir=folder)
    confirm_order_code(
        "Ab12",
        _codes(sender)[0],
        session_id="session-a",
        now=_NOW,
        data_dir=folder,
    )
    assert otp_repository.has_grant("session-a", "Ab12") is True
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from emporio_agent.data.otp_repository import has_grant; "
            "raise SystemExit(0 if has_grant('session-a', 'Ab12') is False else 1)",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr


def test_sender_failure_reveals_nothing_and_creates_no_grant(tmp_path: Path) -> None:
    """A sender failure returns code_not_sent, no order field, and no grant."""
    folder = _seed(tmp_path)
    result = request_order_code(
        "Ab12", sender=_FailingSender(), now=_NOW, data_dir=folder
    )

    assert result == {"error": "code_not_sent"}
    for key in ("status", "order_date", "items", "total_brl", "email", "code"):
        assert key not in result
    assert otp_repository._codes == []
    assert otp_repository._grants == {}
