"""Current promotions can be filtered by product name or category name."""

from pathlib import Path

from emporio_agent.services.promotion_service import search_promotions
from tests.unit.support import insert_category, insert_product, open_database


def _promotions(tmp_path: Path):
    """Load two active promotions in different categories and one inactive row."""
    connection = open_database(tmp_path / "promotions.db")
    insert_category(connection, 5, "Violões")
    insert_category(connection, 8, "Ukuleles")
    insert_product(
        connection, product_id=94, name="Taylor 110e", category_id=5, price_brl="100"
    )
    insert_product(
        connection, product_id=90, name="Crafter HT-100", category_id=5, price_brl="80"
    )
    insert_product(
        connection, product_id=50, name="Ukulele Soprano", category_id=8, price_brl="40"
    )
    connection.executemany(
        """
        INSERT INTO promotions (
            promotion_id, product_id, discount_percent, description, is_active
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 94, 8, "Desconto Exclusivo", 1),
            (2, 90, 18, "Desconto Exclusivo", 1),
            (3, 50, 10, "Oferta Especial", 1),
            (4, 94, 50, "Black Friday", 0),
        ],
    )
    connection.commit()
    return connection


def test_only_active_promotions_are_returned(tmp_path: Path) -> None:
    """An empty query returns every current promotion and no dates or sale price."""
    connection = _promotions(tmp_path)

    result = search_promotions("", connection=connection)

    names = {row["product_name"] for row in result["promotions"]}
    assert names == {"Taylor 110e", "Crafter HT-100", "Ukulele Soprano"}
    for row in result["promotions"]:
        assert set(row) == {
            "product_name",
            "category_name",
            "discount_percent",
            "description",
        }
        assert "start" not in str(row)
        assert "end" not in str(row)
        assert "sale" not in row
        assert row["discount_percent"] in {8, 18, 10}
    assert "Black Friday" not in str(result)


def test_product_name_query_excludes_other_current_promotions(tmp_path: Path) -> None:
    """A product-name query keeps only current promotions for that name."""
    connection = _promotions(tmp_path)

    result = search_promotions("Taylor 110e", connection=connection)

    assert result["promotions"] == [
        {
            "product_name": "Taylor 110e",
            "category_name": "Violões",
            "discount_percent": 8,
            "description": "Desconto Exclusivo",
        }
    ]


def test_category_name_query_uses_the_product_category(tmp_path: Path) -> None:
    """A category query returns only current promotions in that category."""
    connection = _promotions(tmp_path)

    result = search_promotions("Violões", connection=connection)

    names = [row["product_name"] for row in result["promotions"]]
    assert names == ["Crafter HT-100", "Taylor 110e"] or set(names) == {
        "Crafter HT-100",
        "Taylor 110e",
    }
    assert all(row["category_name"] == "Violões" for row in result["promotions"])
    assert "Ukulele Soprano" not in str(result)


def test_no_active_match_and_empty_table_are_not_found(tmp_path: Path) -> None:
    """Nothing active, including an empty table, is not_found."""
    connection = _promotions(tmp_path)
    assert search_promotions("Fender Stratocaster", connection=connection) == {
        "error": "not_found"
    }

    empty = open_database(tmp_path / "empty.db")
    assert search_promotions("", connection=empty) == {"error": "not_found"}
    assert search_promotions("Violões", connection=empty) == {"error": "not_found"}


def test_repeated_query_returns_the_same_rows(tmp_path: Path) -> None:
    """Unchanged promotion rows come back the same way on a repeated query."""
    connection = _promotions(tmp_path)

    assert search_promotions("Taylor", connection=connection) == search_promotions(
        "Taylor",
        connection=connection,
    )


def test_oversized_or_untrimmed_query_is_invalid(tmp_path: Path) -> None:
    """A query longer than 200 characters, or not trimmed, is invalid_input."""
    connection = _promotions(tmp_path)

    assert search_promotions("  Taylor  ", connection=connection) == {
        "error": "invalid_input"
    }
    assert search_promotions("   ", connection=connection) == {"error": "invalid_input"}
    assert search_promotions("a" * 201, connection=connection) == {
        "error": "invalid_input"
    }
