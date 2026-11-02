"""Catalog search returns recorded price and stock, or a clear miss."""

from pathlib import Path

import pytest

from emporio_agent.services.catalog_service import (
    list_product_categories,
    search_products,
    search_products_by_brand,
)
from emporio_agent.tools.catalog_tools import (
    search_products_by_brand as search_brand_tool,
)
from tests.unit.support import write_table

_HIDDEN = ("email", "phone", "created_at", "description", "specs", "payment_method")
_PRODUCT_COLUMNS = [
    "product_id",
    "name",
    "category_id",
    "price_brl",
    "stock_quantity",
    "status",
    "description",
    "specs",
    "created_at",
]


def _catalog(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    """Write categories and products as CSV files."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "categories",
        [
            {"category_id": 5, "name": "Violões", "description": None},
            {"category_id": 9, "name": "Ukuleles", "description": None},
        ],
    )
    write_table(folder, "products", [_product(row) for row in rows])
    return folder


def _product(row: dict[str, object]) -> dict[str, object]:
    """Fill the same product defaults the old insert helper used."""
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "category_id": row.get("category_id"),
        "price_brl": row["price_brl"] if "price_brl" in row else "10.00",
        "stock_quantity": row["stock_quantity"] if "stock_quantity" in row else 1,
        "status": row.get("status", "active"),
        "description": row.get("description"),
        "specs": row.get("specs"),
        "created_at": row.get("created_at", "2020-01-01"),
    }


def test_one_match_returns_recorded_fields(tmp_path: Path) -> None:
    """One name match returns name, category, price, stock, and status."""
    folder = _catalog(
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

    result = search_products("yamaha c40", data_dir=folder)

    assert list(result) == ["matches"]
    match = result["matches"][0]
    assert match["name"] == "Yamaha C40 Nylon Natural"
    assert match["category_name"] == "Violões"
    assert match["price_brl"] == 599.9
    assert match["stock_quantity"] == 12
    assert match["status"] == "active"
    for key in _HIDDEN:
        assert key not in match


def test_singular_category_word_matches_the_plural_category(tmp_path: Path) -> None:
    """violão matches category Violões when the product name omits that word."""
    folder = _catalog(
        tmp_path,
        [
            {
                "product_id": 81,
                "name": "Yamaha C40 Nylon Natural",
                "category_id": 5,
                "description": "Violão clássico com tampo em Spruce.",
            }
        ],
    )

    result = search_products("violão", data_dir=folder)

    assert result["matches"][0]["name"] == "Yamaha C40 Nylon Natural"
    assert result["matches"][0]["category_name"] == "Violões"


def test_category_word_over_five_products_is_too_broad(tmp_path: Path) -> None:
    """A category word that hits more than five products stays too_broad."""
    rows = [
        {"product_id": index, "name": f"Model {index}", "category_id": 5}
        for index in range(1, 7)
    ]
    folder = _catalog(tmp_path, rows)

    result = search_products("violão", data_dir=folder)

    assert result["error"] == "too_broad"
    assert result["match_count"] == 6
    assert "matches" not in result


def test_description_in_another_category_does_not_match(tmp_path: Path) -> None:
    """A description that only mentions violão is not a catalog match."""
    folder = _catalog(
        tmp_path,
        [
            {
                "product_id": 128,
                "name": "Kala KA-B Barítono Mogno",
                "category_id": 9,
                "description": "uma ponte entre o ukulele e o violão",
            }
        ],
    )

    assert search_products("violão", data_dir=folder) == {"error": "not_found"}


def test_supplied_catalog_treats_violao_as_too_broad() -> None:
    """The store catalog has many violões, so the word is too broad, not missing."""
    data_dir = Path(__file__).resolve().parents[2] / "data"

    result = search_products("violão", data_dir=data_dir)

    assert result["error"] == "too_broad"
    assert result["match_count"] == 35
    assert "Yamaha C40 Nylon Natural" not in str(result)


def test_description_and_specs_do_not_match(tmp_path: Path) -> None:
    """A word that appears only in the description or specs is not a match."""
    folder = _catalog(
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

    assert search_products("uniquezebra", data_dir=folder) == {
        "error": "not_found"
    }
    assert search_products("only-in-specs", data_dir=folder) == {
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
    folder = _catalog(tmp_path, rows)

    result = search_products("Guitar", data_dir=folder)

    assert len(result["matches"]) == 5
    assert {item["name"] for item in result["matches"]} == {row["name"] for row in rows}


def test_more_than_five_matches_are_too_broad(tmp_path: Path) -> None:
    """More than five matches return the count and no product rows."""
    rows = [
        {"product_id": index, "name": f"Guitar Model {index}", "category_id": 5}
        for index in range(1, 7)
    ]
    folder = _catalog(tmp_path, rows)

    result = search_products("Guitar", data_dir=folder)

    assert result["error"] == "too_broad"
    assert result["match_count"] == 6
    assert "matches" not in result
    assert "Guitar Model 1" not in str(result)


def test_zero_matches_and_empty_table_are_not_found(tmp_path: Path) -> None:
    """No name match, including an empty loaded table, is not_found."""
    folder = _catalog(
        tmp_path,
        [{"product_id": 1, "name": "Yamaha C40", "category_id": 5}],
    )
    assert search_products("Not A Product", data_dir=folder) == {
        "error": "not_found"
    }

    empty = tmp_path / "empty"
    write_table(empty, "products", [], columns=_PRODUCT_COLUMNS)
    assert search_products("Yamaha", data_dir=empty) == {"error": "not_found"}


def test_unreadable_csv_is_unavailable(tmp_path: Path) -> None:
    """A products file that is not a CSV is unavailable, not an empty match."""
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "desafio_tecnico_ai_eng - products.csv").write_text(
        "this is not a csv\nnope\n",
        encoding="utf-8",
    )

    result = search_products("Yamaha", data_dir=bad)

    assert result == {"error": "unavailable"}


def test_repeated_query_returns_the_same_price_and_stock(tmp_path: Path) -> None:
    """The same query against unchanged rows returns the same recorded numbers."""
    folder = _catalog(
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

    first = search_products("Yamaha C40", data_dir=folder)
    second = search_products("Yamaha C40", data_dir=folder)

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
    folder = _catalog(
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

    match = search_products("Null Case", data_dir=folder)["matches"][0]

    assert "price_brl" in match
    assert "stock_quantity" in match
    assert match["price_brl"] == (599.9 if price_brl == "599.9" else None)
    assert match["stock_quantity"] == stock_quantity
    assert match["price_brl"] != 0
    assert match["stock_quantity"] != 0


def test_query_must_be_trimmed_and_at_most_200_characters(tmp_path: Path) -> None:
    """An empty, untrimmed, or oversized query is invalid_input."""
    folder = _catalog(
        tmp_path,
        [{"product_id": 1, "name": "Yamaha C40", "category_id": 5}],
    )

    assert search_products("", data_dir=folder) == {"error": "invalid_input"}
    assert search_products("  Yamaha  ", data_dir=folder) == {
        "error": "invalid_input"
    }
    assert search_products("a" * 201, data_dir=folder) == {
        "error": "invalid_input"
    }


def test_categories_include_one_with_no_product(tmp_path: Path) -> None:
    """Every named category is listed, even when it has no product."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "categories",
        [
            {
                "category_id": 6,
                "name": "Instrumentos de Sopro (Madeiras)",
                "description": "Flautas e clarinetes",
            },
            {
                "category_id": 5,
                "name": "Violões",
                "description": "Violões clássicos, folk e eletroacústicos",
            },
        ],
    )
    write_table(
        folder,
        "products",
        [_product({"product_id": 81, "name": "Yamaha C40", "category_id": 5})],
    )

    result = list_product_categories(data_dir=folder)

    assert result == {
        "categories": [
            {
                "name": "Violões",
                "description": "Violões clássicos, folk e eletroacústicos",
            },
            {
                "name": "Instrumentos de Sopro (Madeiras)",
                "description": "Flautas e clarinetes",
            },
        ]
    }


def test_empty_category_table_is_not_found(tmp_path: Path) -> None:
    """An empty category table is not_found."""
    folder = tmp_path / "data"
    write_table(
        folder,
        "categories",
        [],
        columns=["category_id", "name", "description"],
    )

    assert list_product_categories(data_dir=folder) == {"error": "not_found"}


def test_brand_matches_a_whole_word_in_the_name(tmp_path: Path) -> None:
    """Yamaha matches the first word and a later word, not a description."""
    folder = _catalog(
        tmp_path,
        [
            {"product_id": 81, "name": "Yamaha C40 Nylon Natural", "category_id": 5},
            {
                "product_id": 139,
                "name": "Bateria Acústica Yamaha Kit 1 Studio",
                "category_id": 3,
            },
            {
                "product_id": 128,
                "name": "Kala KA-B Barítono Mogno",
                "category_id": 9,
                "description": "uma ponte entre o ukulele e o Yamaha",
            },
            {
                "product_id": 135,
                "name": "Music Man Bass 1X Electric Bass",
                "category_id": 2,
            },
        ],
    )
    write_table(
        folder,
        "categories",
        [
            {"category_id": 2, "name": "Baixos", "description": None},
            {"category_id": 3, "name": "Baterias e Percussão", "description": None},
            {"category_id": 5, "name": "Violões", "description": None},
            {"category_id": 9, "name": "Ukuleles", "description": None},
        ],
    )

    yamaha = search_products_by_brand("yamaha", data_dir=folder)
    music_man = search_products_by_brand("Music Man", data_dir=folder)

    assert {item["name"] for item in yamaha["matches"]} == {
        "Yamaha C40 Nylon Natural",
        "Bateria Acústica Yamaha Kit 1 Studio",
    }
    assert music_man["matches"][0]["name"] == "Music Man Bass 1X Electric Bass"
    assert search_products_by_brand("Pearl", data_dir=folder) == {"error": "not_found"}
    assert search_products_by_brand("", data_dir=folder) == {"error": "invalid_input"}


def test_supplied_catalog_lists_every_category_and_yamaha() -> None:
    """The store catalog lists every category and keeps every Yamaha product."""
    data_dir = Path(__file__).resolve().parents[2] / "data"

    categories = list_product_categories(data_dir=data_dir)
    yamaha = search_products_by_brand("Yamaha", data_dir=data_dir)
    names = {item["name"] for item in yamaha["matches"]}

    assert [item["name"] for item in categories["categories"]] == [
        "Guitarras",
        "Baixos",
        "Baterias e Percussão",
        "Teclados e Pianos",
        "Violões",
        "Instrumentos de Sopro (Madeiras)",
        "Instrumentos de Sopro (Metais)",
        "Cordas Orquestrais",
        "Ukuleles",
    ]
    assert "Yamaha C40 Nylon Natural" in names
    assert "Bateria Acústica Yamaha Kit 1 Studio" in names
    assert "Martin D-28 Dreadnought Natural" not in names
    assert len(names) > 5


def test_brand_tool_rejects_an_untrimmed_value() -> None:
    """The tool checks the brand before reading the catalog."""
    assert search_brand_tool("  Yamaha  ") == {"error": "invalid_input"}
