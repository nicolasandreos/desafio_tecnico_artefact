"""Expose the store profile. The tool takes no arguments and does not add facts."""

from emporio_agent.services.store_service import get_store_context as read_store_context


def get_store_context() -> dict[str, str]:
    """Return the supplied store profile text."""
    return read_store_context()
