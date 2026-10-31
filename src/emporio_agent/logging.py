"""English error logs with secrets removed before they are written."""

from __future__ import annotations

import logging
import os
import re

_LOGGER_NAME = "emporio_agent"

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(\d{2}\)[\s-]?)?\d{4,5}-\d{4}")
_CODE = re.compile(r"\b\d{6}\b")
_API_KEY = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b")

_DROPPED_FIELDS = frozenset(
    {
        "api_key",
        "openai_api_key",
        "email",
        "phone",
        "code",
        "ownership_code",
        "smtp_password",
        "password",
        "os_security_key",
    }
)

_ENV_SECRETS = (
    "OPENAI_API_KEY",
    "OS_SECURITY_KEY",
    "SMTP_PASSWORD",
    "SMTP_USER",
)


def get_logger() -> logging.Logger:
    """Return the process logger used for ingest, mail, and order failures."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    if not any(isinstance(item, _RedactionFilter) for item in logger.filters):
        logger.addFilter(_RedactionFilter())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


def redact(text: str) -> str:
    """Remove API keys, email addresses, phone numbers, and six-digit codes."""
    cleaned = _API_KEY.sub("[redacted]", text)
    cleaned = _EMAIL.sub("[redacted]", cleaned)
    cleaned = _PHONE.sub("[redacted]", cleaned)
    cleaned = _CODE.sub("[redacted]", cleaned)
    for name in _ENV_SECRETS:
        secret = os.environ.get(name, "")
        if len(secret) >= 8 and secret in cleaned:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def log_failure(error_code: str, **details: object) -> None:
    """Log an English failure line that keeps the error code and safe details."""
    parts = [f"error_code={error_code}"]
    for key, value in details.items():
        if key.lower() in _DROPPED_FIELDS:
            continue
        parts.append(f"{key}={value}")
    get_logger().error(redact(" ".join(parts)))


class _RedactionFilter(logging.Filter):
    """Apply redaction to any record that reaches this logger."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True after the message has been redacted."""
        record.msg = redact(str(record.msg))
        if isinstance(record.args, tuple):
            record.args = tuple(redact(str(item)) for item in record.args)
        elif record.args:
            record.args = redact(str(record.args))
        return True
