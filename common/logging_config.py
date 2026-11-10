"""Process-wide logging setup."""

from __future__ import annotations

import logging
from logging.config import dictConfig

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def configure_logging(level: str = "INFO") -> None:
    """Configure console logging once for a process."""
    normalized = level.upper()
    if normalized not in _LEVELS:
        normalized = "INFO"
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                }
            },
            "root": {"handlers": ["console"], "level": normalized},
        }
    )
    logging.getLogger(__name__).debug("Logging configured at %s", normalized)
