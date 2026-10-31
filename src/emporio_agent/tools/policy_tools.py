"""Validate a policy question and return the service result unchanged."""

from emporio_agent.services.policy_service import search_policies as search_passages


def search_policies(question: str) -> dict[str, object]:
    """Search store policies. The question must be trimmed and short."""
    if not isinstance(question, str) or question != question.strip() or question == "":
        return {"error": "invalid_input"}
    if len(question) > 500:
        return {"error": "invalid_input"}
    return search_passages(question)
