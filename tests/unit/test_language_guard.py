"""Non-Portuguese wording is refused before any store tool runs."""

from emporio_agent.language_guard import screen_language


def _spy_tools() -> tuple[dict[str, object], list[str]]:
    """Return tool spies and the list they append to when called."""
    called: list[str] = []

    def _record(name: str):
        def _tool(**kwargs: object) -> dict[str, str]:
            called.append(name)
            return {"called": name}

        return _tool

    tools = {
        "search_products": _record("search_products"),
        "search_promotions": _record("search_promotions"),
        "search_policies": _record("search_policies"),
        "request_order_code": _record("request_order_code"),
        "confirm_order_code": _record("confirm_order_code"),
        "get_order_details": _record("get_order_details"),
    }
    return tools, called


def test_english_question_is_refused_in_portuguese_without_tools() -> None:
    """An English question is refused and store tools stay idle."""
    tools, called = _spy_tools()

    result = screen_language("Where is the store?", tools)

    assert result["kind"] == "cannot-help"
    assert result["reason"] == "language"
    assert "portugu" in result["reply"].lower()
    assert "campo grande" not in result["reply"].lower()
    assert called == []


def test_portuguese_sentence_quoting_a_product_name_is_allowed() -> None:
    """A Portuguese sentence that quotes a product name is allowed."""
    tools, called = _spy_tools()

    result = screen_language("qual o preço do Taylor 110e", tools)

    assert result["reason"] == "allow"
    assert result.get("reply") is None
    assert called == []
