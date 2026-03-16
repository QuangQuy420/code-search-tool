"""Structured logging configuration for production and development environments.

Provides:
- JSON logging in production (LOG_FORMAT=json)
- Human-readable text logging in development (default)
- Per-request tracing via request_id context variable
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


# Context variable for per-request tracing
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    _request_id_var.set(request_id)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON line."""
        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request_id if available
        request_id = get_request_id()
        if request_id:
            log_obj["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
                "taskName", "asctime"
            )
        }
        if extra_fields:
            log_obj.update(extra_fields)

        return json.dumps(log_obj)


class TextFormatter(logging.Formatter):
    """Text log formatter for human-readable output in development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as plain text."""
        # Base format
        formatted = super().format(record)

        # Add request_id if available
        request_id = get_request_id()
        if request_id:
            formatted = f"{formatted} [request_id={request_id}]"

        return formatted


def setup_logging() -> None:
    """Configure logging based on LOG_LEVEL and LOG_FORMAT environment variables.

    - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
    - LOG_FORMAT: text, json (default: text)

    In JSON mode, logs are emitted as JSON lines with structured fields.
    In text mode, logs use a human-readable format.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text").lower()

    # Validate log level
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Get or create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Set formatter based on LOG_FORMAT
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
