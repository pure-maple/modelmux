"""Centralized logging configuration for modelmux.

Usage:
    from modelmux.log import setup_logging
    setup_logging()  # reads MODELMUX_LOG_LEVEL env var

Supports:
    - MODELMUX_LOG_LEVEL env var (DEBUG, INFO, WARNING, ERROR)
    - MODELMUX_LOG_FORMAT env var ("text" or "json")
    - Programmatic configuration via setup_logging(level=, fmt=)
"""

from __future__ import annotations

import json
import logging
import os
import time


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
        return json.dumps(entry, ensure_ascii=False)


_TEXT_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
_DATE_FORMAT = "%H:%M:%S"

_configured = False


def setup_logging(
    level: str = "",
    fmt: str = "",
) -> None:
    """Configure the modelmux logger hierarchy.

    Args:
        level: Log level (DEBUG/INFO/WARNING/ERROR). Defaults to
            MODELMUX_LOG_LEVEL env var, then WARNING.
        fmt: Format type ("text" or "json"). Defaults to
            MODELMUX_LOG_FORMAT env var, then "text".
    """
    global _configured
    if _configured:
        return
    _configured = True

    level = level or os.environ.get("MODELMUX_LOG_LEVEL", "WARNING")
    fmt = fmt or os.environ.get("MODELMUX_LOG_FORMAT", "text")

    log_level = getattr(logging, level.upper(), logging.WARNING)
    root_logger = logging.getLogger("modelmux")
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    if fmt == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, datefmt=_DATE_FORMAT))

    root_logger.addHandler(handler)
