from __future__ import annotations
import logging
import re
from typing import Any, Dict


REDACT_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9]{20,})"),  # API keys like OpenAI
]


def redact(value: str) -> str:
    redacted = value
    for pat in REDACT_PATTERNS:
        redacted = pat.sub("***", redacted)
    return redacted


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Ensure message string is redacted
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        # Redact exception info text if present
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger()
    logger.setLevel(level)
    # Clear existing handlers in reload scenarios
    logger.handlers.clear()

    handler = logging.StreamHandler()
    formatter = RedactingFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Reduce noisy loggers if needed
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
