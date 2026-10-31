"""Run the language and scope guards before any tool or model call."""

from __future__ import annotations

from collections.abc import Mapping

from emporio_agent.language_guard import screen_language
from emporio_agent.scope_guard import screen_scope


def run_guard_path(
    message: str,
    tools: Mapping[str, object] | None = None,
) -> dict[str, str | None]:
    """Return a refusal, or allow, without reading or writing operational rows."""
    language = screen_language(message, tools)
    if language["reason"] != "allow":
        return language
    return screen_scope(message, tools)


def guard_pre_hook(run_input: object, **kwargs: object) -> None:
    """Stop the run before the model when the message must be refused."""
    del kwargs
    outcome = run_guard_path(_message_text(run_input))
    if outcome["reason"] == "allow":
        return
    from agno.exceptions import CheckTrigger, InputCheckError

    raise InputCheckError(
        str(outcome["reply"]),
        check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
    )


def _message_text(run_input: object) -> str:
    """Read the customer text from an agent run input."""
    reader = getattr(run_input, "input_content_string", None)
    if callable(reader):
        return str(reader())
    content = getattr(run_input, "input_content", "")
    if isinstance(content, str):
        return content
    return str(content)
