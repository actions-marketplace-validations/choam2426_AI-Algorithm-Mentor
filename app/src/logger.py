"""Pretty, minimal logging utilities for AI Algorithm Mentor.

This module exposes a singleton `logger` instance with a colored,
emoji-based console formatter. The root logger is configured once
on import. Use `set_logger_level` to adjust the level at runtime.
"""

from __future__ import annotations

import logging
import sys


class PrettyFormatter(logging.Formatter):
    """Formatter that prints colored, emoji-enhanced log lines."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    EMOJIS = {
        "DEBUG": "🐛",
        "INFO": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        emoji = self.EMOJIS.get(record.levelname, "📋")

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        message = record.getMessage()

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return (
            f"{color}{emoji} [{timestamp}] "
            f"{record.levelname:<8} | {record.name:<20} | {message}{reset}"
        )


_configured: bool = False


def _configure_root_logger(level: str = "INFO") -> None:
    """Configure the root logger once with our pretty console handler."""
    global _configured
    if _configured:
        return

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(PrettyFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    _configured = True


def set_logger_level(level: str) -> None:
    """Set the root logger level. If not configured yet, configure first."""
    if not _configured:
        _configure_root_logger(level)
        return
    logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))


# Configure on import and expose a singleton logger
_configure_root_logger()
logger: logging.Logger = logging.getLogger("ai-algorithm-mentor")