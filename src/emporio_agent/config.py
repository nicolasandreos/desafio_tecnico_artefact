"""Load paths and credentials from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Secret fields stay None when the environment omits them."""

    openai_api_key: str | None
    openai_model: str | None
    resend_api_key: str | None
    resend_from: str | None
    data_dir: Path
    chroma_path: Path
    outbox_dir: Path


def load_settings() -> Settings:
    """Return settings from the environment, loading a local .env file first."""
    load_dotenv(".env")
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        openai_model=os.environ.get("OPENAI_MODEL"),
        resend_api_key=os.environ.get("RESEND_API_KEY"),
        resend_from=os.environ.get("RESEND_FROM"),
        data_dir=Path(os.environ.get("DATA_DIR", "data")),
        chroma_path=Path(os.environ.get("CHROMA_PATH", "var/chroma")),
        outbox_dir=Path(os.environ.get("OUTBOX_DIR", "var/outbox")),
    )


def check_essential_settings(settings: Settings) -> None:
    """Check if the essential settings are set."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to start the assistant")
    if not settings.openai_model:
        raise RuntimeError("OPENAI_MODEL is required to start the assistant")
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is required to start the assistant")
    if not settings.resend_from:
        raise RuntimeError("RESEND_FROM is required to start the assistant")
