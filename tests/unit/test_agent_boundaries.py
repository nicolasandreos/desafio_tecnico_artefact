"""The agent retrieves policy text and exposes only the read-only tools."""

from agno.db.in_memory import InMemoryDb
from agno.knowledge.knowledge import Knowledge
from agno.run import RunContext
from agno.run.agent import RunOutput
from agno.session.agent import AgentSession

from emporio_agent.agent.assistant import build_agent

_TOOLS = [
    "get_store_context",
    "list_product_categories",
    "search_products",
    "search_products_by_brand",
    "search_promotions",
    "request_order_code",
    "confirm_order_code",
    "get_order_details",
]


def _tool_name(tool: object) -> str:
    """Return the name Agno will show the model."""
    name = getattr(tool, "__name__", None)
    if isinstance(name, str):
        return name
    named = getattr(tool, "name", None)
    if isinstance(named, str):
        return named
    entry = getattr(tool, "entrypoint", None)
    entry_name = getattr(entry, "__name__", None)
    if isinstance(entry_name, str):
        return entry_name
    raise AssertionError(type(tool))


def test_agent_uses_memory_and_the_read_only_tools(monkeypatch) -> None:
    """Knowledge is attached and the session store is in memory."""
    knowledge = Knowledge(max_results=4)
    monkeypatch.setattr(
        "emporio_agent.agent.assistant.ensure_policy_index",
        lambda: knowledge,
    )
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    agent = build_agent()
    resolved = agent.get_tools(
        run_response=RunOutput(),
        run_context=RunContext(run_id="run-1", session_id="session-1"),
        session=AgentSession(session_id="session-1"),
    )
    names = [_tool_name(tool) for tool in resolved]

    assert agent.add_knowledge_to_context is True
    assert agent.search_knowledge is False
    assert agent.add_search_knowledge_instructions is False
    assert agent.knowledge is knowledge
    assert agent.update_knowledge is False
    assert not agent.pre_hooks
    assert isinstance(agent.db, InMemoryDb)
    assert names == _TOOLS
    assert "search_knowledge_base" not in names
    assert "search_policies" not in names


def test_a_failed_index_does_not_start_the_agent(monkeypatch) -> None:
    """A failed policy index raises before an agent is returned."""

    def fail() -> Knowledge:
        raise FileNotFoundError("políticas_da_loja.pdf")

    monkeypatch.setattr("emporio_agent.agent.assistant.ensure_policy_index", fail)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    try:
        build_agent()
    except FileNotFoundError as exc:
        assert "políticas_da_loja.pdf" in str(exc)
    else:
        raise AssertionError("build_agent returned after the index failed")
