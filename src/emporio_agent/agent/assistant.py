"""Wire the one Emporio da Musica agent. This module holds no query rules."""

from __future__ import annotations

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.openai import OpenAIResponses

from emporio_agent.agent.instructions import INSTRUCTIONS
from emporio_agent.config import load_settings
from emporio_agent.knowledge.policy_knowledge import ensure_policy_index
from emporio_agent.tools.catalog_tools import (
    list_product_categories,
    search_products,
    search_products_by_brand,
)
from emporio_agent.tools.order_tools import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from emporio_agent.tools.promotion_tools import search_promotions
from emporio_agent.tools.store_tools import get_store_context


def tool_list() -> list:
    """Return the read-only assistant tools."""
    return [
        get_store_context,
        list_product_categories,
        search_products,
        search_products_by_brand,
        search_promotions,
        request_order_code,
        confirm_order_code,
        get_order_details,
    ]


def build_agent() -> Agent:
    """Create the agent after the policy index is complete.

    Raises:
        FileNotFoundError: The policy PDF is missing. No agent is returned.
    """
    settings = load_settings()
    knowledge = ensure_policy_index()
    return Agent(
        id="emporio-da-musica",
        name="Emporio da Musica",
        model=OpenAIResponses(id=str(settings.openai_model)),
        tools=tool_list(),
        instructions=INSTRUCTIONS,
        db=InMemoryDb(),
        knowledge=knowledge,
        add_history_to_context=True,
        num_history_runs=10,
        add_knowledge_to_context=True,
        search_knowledge=False,
        add_search_knowledge_instructions=False,
        update_knowledge=False,
        telemetry=False,
    )
