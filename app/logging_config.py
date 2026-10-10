"""Structured logging configuration using Python's standard logging."""

from __future__ import annotations

import logging
import sys
from typing import Any


class CorrelationFilter(logging.Filter):
    """Inject correlation_id into log records if missing."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


class SensitiveDataFilter(logging.Filter):
    """Scrub sensitive fields from log messages."""

    SENSITIVE_KEYS = frozenset(
        [
            "password",
            "hashed_password",
            "jwt_secret",
            "smtp_password",
            "authorization",
            "token",
            "secret",
        ]
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {
                k: "***REDACTED***" if k.lower() in self.SENSITIVE_KEYS else v
                for k, v in record.args.items()
            }
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application-wide logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt=("%(asctime)s | %(levelname)-8s | %(name)s | " "cid=%(correlation_id)s | %(message)s"),
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with correlation filter applied."""
    logger = logging.getLogger(name)
    logger.addFilter(CorrelationFilter())
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **ctx: Any) -> None:
    """Log a message with additional context fields appended."""
    extra_str = " | ".join(f"{k}={v}" for k, v in ctx.items())
    full_message = f"{message} | {extra_str}" if extra_str else message
    getattr(logger, level.lower())(full_message)
