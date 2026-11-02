"""Current promotions can be filtered by product name or category name."""

from pathlib import Path

from emporio_agent.services.promotion_service import search_promotions
from tests.unit.support import write_table

_PROMOTION_COLUMNS = [
    "promotion_id",
    "product_id",
    "discount_percent",
    "description",
    "is_active",
]


def _promotions(tmp_path: Path) -> Path:
    """Write two active promotions in different categories and one inactive row."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "categories",
        [
            {"category_id": 5, "name": "Violões", "description": None},
            {"category_id": 8, "name": "Ukuleles", "description": None},
        ],
    )
    write_table(
        folder,
        "products",
        [
            {
                "product_id": 94,
                "name": "Taylor 110e",
                "category_id": 5,
                "price_brl": "100",
            },
            {
                "product_id": 90,
                "name": "Crafter HT-100",
                "category_id": 5,
                "price_brl": "80",
            },
            {
                "product_id": 50,
                "name": "Ukulele Soprano",
                "category_id": 8,
                "price_brl": "40",
            },
        ],
    )
    write_table(
        folder,
        "promotions",
        [
            {
                "promotion_id": 1,
                "product_id": 94,
                "discount_percent": 8,
                "description": "Desconto Exclusivo",
                "is_active": 1,
            },
            {
                "promotion_id": 2,
                "product_id": 90,
                "discount_percent": 18,
                "description": "Desconto Exclusivo",
                "is_active": 1,
            },
            {
                "promotion_id": 3,
                "product_id": 50,
                "discount_percent": 10,
                "description": "Oferta Especial",
                "is_active": 1,
            },
            {
                "promotion_id": 4,
                "product_id": 94,
                "discount_percent": 50,
                "description": "Black Friday",
                "is_active": 0,
            },
        ],
    )
    return folder


def test_only_active_promotions_are_returned(tmp_path: Path) -> None:
    """An empty query returns every current promotion and no dates or sale price."""
    folder = _promotions(tmp_path)

    result = search_promotions("", data_dir=folder)

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
    folder = _promotions(tmp_path)

    result = search_promotions("Taylor 110e", data_dir=folder)

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
    folder = _promotions(tmp_path)

    result = search_promotions("Violões", data_dir=folder)

    names = [row["product_name"] for row in result["promotions"]]
    assert names == ["Crafter HT-100", "Taylor 110e"] or set(names) == {
        "Crafter HT-100",
        "Taylor 110e",
    }
    assert all(row["category_name"] == "Violões" for row in result["promotions"])
    assert "Ukulele Soprano" not in str(result)


def test_no_active_match_and_empty_table_are_not_found(tmp_path: Path) -> None:
    """Nothing active, including an empty table, is not_found."""
    folder = _promotions(tmp_path)
    assert search_promotions("Fender Stratocaster", data_dir=folder) == {
        "error": "not_found"
    }

    empty = tmp_path / "empty"
    write_table(empty, "promotions", [], columns=_PROMOTION_COLUMNS)
    assert search_promotions("", data_dir=empty) == {"error": "not_found"}
    assert search_promotions("Violões", data_dir=empty) == {"error": "not_found"}


def test_repeated_query_returns_the_same_rows(tmp_path: Path) -> None:
    """Unchanged promotion rows come back the same way on a repeated query."""
    folder = _promotions(tmp_path)

    assert search_promotions("Taylor", data_dir=folder) == search_promotions(
        "Taylor",
        data_dir=folder,
    )


def test_oversized_or_untrimmed_query_is_invalid(tmp_path: Path) -> None:
    """A query longer than 200 characters, or not trimmed, is invalid_input."""
    folder = _promotions(tmp_path)

    assert search_promotions("  Taylor  ", data_dir=folder) == {
        "error": "invalid_input"
    }
    assert search_promotions("   ", data_dir=folder) == {"error": "invalid_input"}
    assert search_promotions("a" * 201, data_dir=folder) == {
        "error": "invalid_input"
    }
