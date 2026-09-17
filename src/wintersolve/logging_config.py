"""Quiet-by-default logging.

WinterSolve writes reports to stdout, so diagnostics go to stderr and only
warnings show unless ``--verbose`` raises the level. Loggers never propagate
to the root logger, which keeps host applications' logging untouched when
WinterSolve is used as a library.
"""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str = "wintersolve") -> logging.Logger:
    """Return the named logger, creating and configuring it on first use."""
    if name not in _loggers:
        _loggers[name] = _create_logger(name)
    return _loggers[name]


def _create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT))
        logger.addHandler(handler)
    return logger


def set_log_level(level: int) -> None:
    """Change the level of every WinterSolve logger created so far."""
    for logger in _loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def configure_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    date_format: str | None = None,
) -> None:
    """Set the level and, optionally, the message format for all WinterSolve loggers."""
    set_log_level(level)
    if format_string is None:
        return
    formatter = logging.Formatter(format_string, datefmt=date_format)
    for logger in _loggers.values():
        for handler in logger.handlers:
            handler.setFormatter(formatter)
