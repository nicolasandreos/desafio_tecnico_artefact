"""Policy answers are retrieved passages, not operational facts."""

from emporio_agent.services.policy_service import search_policies

_SOURCE = "políticas_da_loja.pdf"


def test_matching_passage_returns_text_and_source() -> None:
    """A matching passage exposes text and source only."""

    def searcher(question: str) -> list[dict[str, str]]:
        assert "devolu" in question.casefold()
        return [
            {
                "text": "O prazo de devolução é de 7 dias.",
                "source": _SOURCE,
                "price_brl": 1,
            }
        ]

    result = search_policies("Como funciona a devolução?", searcher=searcher)

    assert result == {
        "passages": [{"text": "O prazo de devolução é de 7 dias.", "source": _SOURCE}]
    }


def test_no_matching_passage_is_not_found() -> None:
    """An empty search result is not_found."""
    result = search_policies("procedimento inexistente", searcher=lambda question: [])

    assert result == {"error": "not_found"}


def test_missing_index_is_unavailable() -> None:
    """A missing index is unavailable."""

    def searcher(question: str) -> list[dict[str, str]]:
        raise FileNotFoundError("store_policies")

    assert search_policies("devolução", searcher=searcher) == {"error": "unavailable"}


def test_passages_are_not_price_stock_order_or_discount_facts() -> None:
    """A passage is not copied into price, stock, order, or discount fields."""

    def searcher(question: str) -> list[dict[str, str]]:
        return [
            {
                "text": "O desconto não está neste texto. Status entregue.",
                "source": _SOURCE,
            }
        ]

    result = search_policies("qual a política?", searcher=searcher)

    assert set(result) == {"passages"}
    assert set(result["passages"][0]) == {"text", "source"}
    for key in (
        "price_brl",
        "stock_quantity",
        "status",
        "discount_percent",
        "total_brl",
    ):
        assert key not in result


def test_question_must_be_present_trimmed_and_within_500_characters() -> None:
    """An empty, untrimmed, or oversized question is invalid_input."""
    assert search_policies("", searcher=lambda question: []) == {
        "error": "invalid_input"
    }
    assert search_policies("  devolução  ", searcher=lambda question: []) == {
        "error": "invalid_input"
    }
    assert search_policies("a" * 501, searcher=lambda question: []) == {
        "error": "invalid_input"
    }
