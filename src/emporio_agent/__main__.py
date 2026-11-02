"""Serve the Emporio da Musica assistant with AgentOS."""

import os
import sys
from pathlib import Path

# Running this file as a script puts its folder first on sys.path. That folder
# contains logging.py, which would replace the standard-library logging module.
_package_dir = Path(__file__).resolve().parent
sys.path[:] = [
    entry
    for entry in sys.path
    if not entry or Path(entry).resolve() != _package_dir
]
_src = str(_package_dir.parent)
if _src not in sys.path:
    sys.path.insert(0, _src)

from agno.os import AgentOS  # noqa: E402

from emporio_agent.agent.assistant import build_agent  # noqa: E402
from emporio_agent.config import check_essential_settings, load_settings  # noqa: E402


def create_agent_os() -> AgentOS:
    """Build AgentOS with tracing, the scheduler, MCP, and file tools left off."""
    settings = load_settings()
    os.environ.pop("OS_SECURITY_KEY", None)
    check_essential_settings(settings)
    agent = build_agent()
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
