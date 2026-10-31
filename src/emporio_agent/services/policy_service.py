"""Search policy passages. Passages are not price, stock, order, or promotion facts."""

from __future__ import annotations

from collections.abc import Callable

_MAX_QUESTION = 500
_PASSAGE_KEYS = ("text", "source")


def search_policies(
    question: str,
    *,
    searcher: Callable[[str], list[dict[str, object]]] | None = None,
) -> dict[str, object]:
    """Return passage text and source, or an error code."""
    if not _valid_question(question):
        return {"error": "invalid_input"}
    lookup = searcher if searcher is not None else _default_search
    try:
        found = lookup(question)
    except FileNotFoundError:
        return {"error": "unavailable"}
    except OSError:
        return {"error": "unavailable"}
    passages = [_passage(item) for item in found]
    if not passages:
        return {"error": "not_found"}
    return {"passages": passages}


def _valid_question(question: object) -> bool:
    """Return True when the question is a trimmed string of at most 500 characters."""
    if not isinstance(question, str):
        return False
    if question != question.strip() or question == "":
        return False
    return len(question) <= _MAX_QUESTION


def _passage(item: dict[str, object]) -> dict[str, object]:
    """Keep text and source. Operational keys on the raw hit are dropped."""
    return {key: item.get(key) for key in _PASSAGE_KEYS}


def _default_search(question: str) -> list[dict[str, object]]:
    """Search the policy index."""
    from emporio_agent.knowledge.policy_knowledge import search_passages

    return search_passages(question)
