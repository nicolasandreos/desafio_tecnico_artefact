"""Load paths and credentials from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_SECRET_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OS_SECURITY_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM",
)


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Secret fields stay None when the environment omits them."""

    openai_api_key: str | None
    openai_model: str | None
    os_security_key: str | None
    resend_api_key: str | None
    resend_from: str | None
    data_dir: Path
    sqlite_path: Path
    session_db_path: Path
    chroma_path: Path
    outbox_dir: Path


def load_settings() -> Settings:
    """Return settings from the environment, loading a local .env file first."""
    _load_dotenv(Path(".env"))
    return Settings(
        openai_api_key=_optional("OPENAI_API_KEY"),
        openai_model=_optional("OPENAI_MODEL"),
        os_security_key=_optional("OS_SECURITY_KEY"),
        resend_api_key=_optional("RESEND_API_KEY"),
        resend_from=_optional("RESEND_FROM"),
        data_dir=Path(os.environ.get("DATA_DIR", "data")),
        sqlite_path=Path(os.environ.get("SQLITE_PATH", "var/emporio.db")),
        session_db_path=Path(os.environ.get("SESSION_DB_PATH", "var/sessions.db")),
        chroma_path=Path(os.environ.get("CHROMA_PATH", "var/chroma")),
        outbox_dir=Path(os.environ.get("OUTBOX_DIR", "var/outbox")),
    )


def _optional(name: str) -> str | None:
    """Return a non-empty environment value, or None when it is unset."""
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    return stripped


def _load_dotenv(path: Path) -> None:
    """Set missing environment keys from a KEY=VALUE file."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, raw_value = line.split("=", 1)
        key = name.strip()
        if key not in _SECRET_NAMES and key not in {
            "DATA_DIR",
            "SQLITE_PATH",
            "SESSION_DB_PATH",
            "CHROMA_PATH",
            "OUTBOX_DIR",
        }:
            continue
        value = raw_value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
