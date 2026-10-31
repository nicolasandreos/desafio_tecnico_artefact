"""Serve the Emporio da Musica assistant with AgentOS."""

import os
from typing import TYPE_CHECKING

from emporio_agent.agent.assistant import attach_guards, build_agent
from emporio_agent.config import load_settings
from emporio_agent.guard_path import guard_pre_hook

if TYPE_CHECKING:
    from agno.os import AgentOS


def create_agent_os() -> "AgentOS":
    """Build AgentOS with tracing, the scheduler, MCP, and file tools left off."""
    settings = load_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to start the assistant")
    if not settings.openai_model:
        raise RuntimeError("OPENAI_MODEL is required to start the assistant")
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.os_security_key:
        os.environ["OS_SECURITY_KEY"] = settings.os_security_key
    from agno.os import AgentOS

    agent = build_agent()
    attach_guards(agent)
    if guard_pre_hook not in list(agent.pre_hooks or []):
        agent.pre_hooks = [guard_pre_hook, *list(agent.pre_hooks or [])]
    return AgentOS(
        id="emporio-da-musica",
        agents=[agent],
        db=agent.db,
        tracing=False,
        scheduler=False,
        telemetry=False,
    )


def main() -> None:
    """Start the local AgentOS process."""
    agent_os = create_agent_os()
    app = agent_os.get_app()
    agent_os.serve(app=app, host="127.0.0.1", reload=False)


if __name__ == "__main__":
    main()
