"""Calling the read-only tools does not change a CSV file."""

from pathlib import Path

import pytest

from emporio_agent.tools.catalog_tools import search_products
from emporio_agent.tools.order_tools import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from emporio_agent.tools.promotion_tools import search_promotions
from emporio_agent.tools.store_tools import get_store_context
from tests.unit.support import write_table


def _snapshot(folder: Path) -> dict[str, bytes]:
    """Return the bytes of every file under folder."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def test_read_only_tools_do_not_change_a_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Product, promotion, store, and order reads leave the CSV bytes unchanged."""
    write_table(
        tmp_path,
        "categories",
        [{"category_id": 1, "name": "Teclas", "description": ""}],
    )
    write_table(
        tmp_path,
        "products",
        [
            {
                "product_id": 1,
                "name": "Piano de Cauda",
                "category_id": 1,
                "price_brl": "999.0",
                "stock_quantity": 1,
                "status": "active",
            }
        ],
    )
    write_table(
        tmp_path,
        "customers",
        [{"customer_id": 3, "name": "Ada", "email": "buyer@example.com"}],
    )
    write_table(
        tmp_path,
        "orders",
        [
            {
                "order_id": "Ab12",
                "customer_id": 3,
                "order_date": "2025-10-15",
                "status": "delivered",
                "total_brl": "10",
            }
        ],
    )
    write_table(
        tmp_path,
        "order_items",
        [{"order_id": "Ab12", "product_id": 1, "quantity": 1}],
    )
    write_table(
        tmp_path,
        "promotions",
        [
            {
                "promotion_id": 1,
                "product_id": 1,
                "discount_percent": "10",
                "description": "Semana do piano",
                "is_active": 1,
            }
        ],
    )
    (tmp_path / "store_profile.md").write_text(
        "Emporio da Musica fica em Campo Grande.\n", encoding="utf-8"
    )
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    before = _snapshot(tmp_path)

    get_store_context()
    search_products("Piano")
    search_promotions("Piano")
    request_order_code("missing-order")
    confirm_order_code("missing-order", "000000")
    get_order_details("missing-order", ["status"])

    assert _snapshot(tmp_path) == before
