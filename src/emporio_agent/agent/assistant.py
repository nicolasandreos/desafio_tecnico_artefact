"""Wire the one Emporio da Musica agent. This module holds no query rules."""

from __future__ import annotations

import os

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses

from emporio_agent.agent.instructions import INSTRUCTIONS
from emporio_agent.config import load_settings
from emporio_agent.guard_path import guard_pre_hook
from emporio_agent.tools.catalog_tools import search_products
from emporio_agent.tools.order_tools import (
    confirm_order_code,
    get_order_details,
    request_order_code,
)
from emporio_agent.tools.policy_tools import search_policies
from emporio_agent.tools.promotion_tools import search_promotions
from emporio_agent.tools.store_tools import get_store_context


def tool_list() -> list[object]:
    """Return the assistant tools. Later capabilities are appended here."""
    return [
        get_store_context,
        search_products,
        request_order_code,
        confirm_order_code,
        get_order_details,
        search_promotions,
        search_policies,
    ]


def build_agent() -> Agent:
    """Create the single agent with session history and the registered tools."""
    settings = load_settings()
    if not settings.openai_model:
        raise RuntimeError("OPENAI_MODEL is required to start the assistant")
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    settings.session_db_path.parent.mkdir(parents=True, exist_ok=True)
    agent = Agent(
        id="emporio-da-musica",
        name="Emporio da Musica",
        model=OpenAIResponses(id=settings.openai_model),
        tools=tool_list(),
        instructions=INSTRUCTIONS,
        db=SqliteDb(db_file=str(settings.session_db_path)),
        add_history_to_context=True,
        num_history_runs=10,
        search_knowledge=False,
        pre_hooks=[guard_pre_hook],
        telemetry=False,
    )
    return agent


def attach_guards(agent: Agent) -> None:
    """Register the message guard before the model and before any tool."""
    hooks = list(agent.pre_hooks or [])
    if guard_pre_hook not in hooks:
        agent.pre_hooks = [guard_pre_hook, *hooks]
