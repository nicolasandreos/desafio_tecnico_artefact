"""Policy passages are attached while the user message is built."""

from agno.agent import Agent
from agno.agent._messages import get_user_message
from agno.knowledge.document.base import Document
from agno.knowledge.knowledge import Knowledge
from agno.run.agent import RunOutput

_QUESTION = "Qual o prazo de devolução?"
_PASSAGE = "O prazo de devolução é de 7 dias."


def _agent(search) -> Agent:
    """Return an agent whose knowledge search is the supplied fake."""
    knowledge = Knowledge(max_results=4)
    knowledge.search = search
    return Agent(
        knowledge=knowledge,
        add_knowledge_to_context=True,
        search_knowledge=False,
    )


def _message(agent: Agent) -> str:
    """Build the user message the model would see. The chat model is not called."""
    message = get_user_message(agent, run_response=RunOutput(), input=_QUESTION)
    assert message is not None
    assert isinstance(message.content, str)
    return message.content


def test_fake_search_runs_on_the_customer_text_and_attaches_the_passage() -> None:
    """The customer text is the query, and the returned passage is attached."""
    seen: dict[str, object] = {}

    def search(query: str, max_results: int | None = None, **kwargs: object) -> list:
        seen["query"] = query
        seen["max_results"] = max_results
        return [Document(content=_PASSAGE)]

    content = _message(_agent(search))

    assert seen["query"] == _QUESTION
    assert seen["max_results"] == 4
    assert _QUESTION in content
    assert _PASSAGE in content


def test_empty_search_attaches_no_passage() -> None:
    """An empty result leaves the customer text without a knowledge passage."""

    def search(query: str, max_results: int | None = None, **kwargs: object) -> list:
        return []

    content = _message(_agent(search))

    assert content == _QUESTION
    assert "<references>" not in content


def test_failed_search_attaches_no_invented_passage() -> None:
    """A search error does not invent a passage."""

    def search(query: str, max_results: int | None = None, **kwargs: object) -> list:
        raise RuntimeError("search failed")

    content = _message(_agent(search))

    assert content == _QUESTION
    assert "search failed" not in content
