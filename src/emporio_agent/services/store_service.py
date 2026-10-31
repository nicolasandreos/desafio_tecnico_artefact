"""Read the short store profile. This service does not search products or orders."""

from __future__ import annotations

from pathlib import Path

from emporio_agent.config import load_settings


def get_store_context(profile_path: Path | None = None) -> dict[str, str]:
    """Return the profile text, or unavailable when no profile was supplied."""
    path = _profile_path(profile_path)
    if not path.is_file():
        return {"error": "unavailable"}
    return {"facts": path.read_text(encoding="utf-8")}


def _profile_path(profile_path: Path | None) -> Path:
    """Resolve an explicit profile path or the file in the data directory."""
    if profile_path is not None:
        return Path(profile_path)
    return load_settings().data_dir / "store_profile.md"
