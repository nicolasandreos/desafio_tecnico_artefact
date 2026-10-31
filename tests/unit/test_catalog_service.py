"""Catalog search returns recorded price and stock, or a clear miss."""

from pathlib import Path

import pytest

from emporio_agent.services.catalog_service import search_products
from tests.unit.support import insert_category, insert_product, open_database

_HIDDEN = ("email", "phone", "created_at", "description", "specs", "payment_method")


def _catalog(tmp_path: Path, rows: list[dict[str, object]]):
    """Load categories and products into a temporary database."""
    connection = open_database(tmp_path / "catalog.db")
    insert_category(connection, 5, "Violões")
    insert_category(connection, 9, "Ukuleles")
    for row in rows:
        insert_product(connection, **row)
    connection.commit()
    return connection


def test_one_match_returns_recorded_fields(tmp_path: Path) -> None:
    """One name match returns name, category, price, stock, and status."""
    connection = _catalog(
        tmp_path,
        [
            {
                "product_id": 1,
                "name": "Yamaha C40 Nylon Natural",
                "category_id": 5,
                "price_brl": "599.9",
                "stock_quantity": 12,
                "description": "uniquezebra description only",
                "specs": '{"color":"only-in-specs"}',
                "created_at": "2021-03-15",
            }
        ],
    )

    result = search_products("yamaha c40", connection=connection)

    assert list(result) == ["matches"]
    match = result["matches"][0]
    assert match["name"] == "Yamaha C40 Nylon Natural"
    assert match["category_name"] == "Violões"
    assert match["price_brl"] == 599.9
    assert match["stock_quantity"] == 12
    assert match["status"] == "active"
    for key in _HIDDEN:
        assert key not in match


def test_description_and_specs_do_not_match(tmp_path: Path) -> None:
    """A word that appears only in the description or specs is not a match."""
    connection = _catalog(
        tmp_path,
        [
            {
                "product_id": 1,
                "name": "Alpha Body",
                "category_id": 5,
                "description": "uniquezebra",
                "specs": '{"finish":"only-in-specs"}',
            }
        ],
    )

    assert search_products("uniquezebra", connection=connection) == {
        "error": "not_found"
    }
    assert search_products("only-in-specs", connection=connection) == {
        "error": "not_found"
    }


def test_two_to_five_matches_return_each_product(tmp_path: Path) -> None:
    """Two to five name matches are all returned."""
    rows = [
        {
            "product_id": index,
            "name": f"Guitar Model {index}",
            "category_id": 5,
            "price_brl": str(index),
            "stock_quantity": index,
        }
        for index in range(1, 6)
    ]
    connection = _catalog(tmp_path, rows)

    result = search_products("Guitar", connection=connection)

    assert len(result["matches"]) == 5
    assert {item["name"] for item in result["matches"]} == {row["name"] for row in rows}


def test_more_than_five_matches_are_too_broad(tmp_path: Path) -> None:
    """More than five matches return the count and no product rows."""
    rows = [
        {"product_id": index, "name": f"Guitar Model {index}", "category_id": 5}
        for index in range(1, 7)
    ]
    connection = _catalog(tmp_path, rows)

    result = search_products("Guitar", connection=connection)

    assert result["error"] == "too_broad"
    assert result["match_count"] == 6
    assert "matches" not in result
    assert "Guitar Model 1" not in str(result)


def test_zero_matches_and_empty_table_are_not_found(tmp_path: Path) -> None:
    """No name match, including an empty loaded table, is not_found."""
    connection = _catalog(
        tmp_path,
        [{"product_id": 1, "name": "Yamaha C40", "category_id": 5}],
    )
    assert search_products("Not A Product", connection=connection) == {
        "error": "not_found"
    }

    empty = open_database(tmp_path / "empty.db")
    empty.commit()
    assert search_products("Yamaha", connection=empty) == {"error": "not_found"}


def test_unreadable_database_is_unavailable(tmp_path: Path) -> None:
    """A file that is not a database is unavailable, not an empty match."""
    bad = tmp_path / "bad.db"
    bad.write_text("this is not sqlite", encoding="utf-8")

    result = search_products("Yamaha", database_path=bad)

    assert result == {"error": "unavailable"}


def test_repeated_query_returns_the_same_price_and_stock(tmp_path: Path) -> None:
    """The same query against unchanged rows returns the same recorded numbers."""
    connection = _catalog(
        tmp_path,
        [
            {
                "product_id": 1,
                "name": "Yamaha C40",
                "category_id": 5,
                "price_brl": "599.9",
                "stock_quantity": 12,
            }
        ],
    )

    first = search_products("Yamaha C40", connection=connection)
    second = search_products("Yamaha C40", connection=connection)

    assert first == second
    assert first["matches"][0]["price_brl"] == 599.9
    assert first["matches"][0]["stock_quantity"] == 12


@pytest.mark.parametrize(
    ("price_brl", "stock_quantity"),
    [
        ("599.9", 12),
        (None, 12),
        ("599.9", None),
        (None, None),
    ],
)
def test_null_price_and_stock_stay_null(
    tmp_path: Path,
    price_brl: str | None,
    stock_quantity: int | None,
) -> None:
    """A missing price or stock stays JSON null and is not zero."""
    connection = _catalog(
        tmp_path,
        [
            {
                "product_id": 1,
                "name": "Null Case",
                "category_id": 5,
                "price_brl": price_brl,
                "stock_quantity": stock_quantity,
            }
        ],
    )

    match = search_products("Null Case", connection=connection)["matches"][0]

    assert "price_brl" in match
    assert "stock_quantity" in match
    assert match["price_brl"] == (599.9 if price_brl == "599.9" else None)
    assert match["stock_quantity"] == stock_quantity
    assert match["price_brl"] != 0
    assert match["stock_quantity"] != 0


def test_query_must_be_trimmed_and_at_most_200_characters(tmp_path: Path) -> None:
    """An empty, untrimmed, or oversized query is invalid_input."""
    connection = _catalog(
        tmp_path,
        [{"product_id": 1, "name": "Yamaha C40", "category_id": 5}],
    )

    assert search_products("", connection=connection) == {"error": "invalid_input"}
    assert search_products("  Yamaha  ", connection=connection) == {
        "error": "invalid_input"
    }
    assert search_products("a" * 201, connection=connection) == {
        "error": "invalid_input"
    }
