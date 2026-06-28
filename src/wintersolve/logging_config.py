from __future__ import annotations

import logging
import sys

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str = "wintersolve") -> logging.Logger:
    """Get or create a logger with the given name."""
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
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def set_log_level(level: int) -> None:
    """Set the log level for all wintersolve loggers."""
    for logger in _loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def configure_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    date_format: str | None = None,
) -> None:
    """Configure global logging for wintersolve."""
    for logger in _loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
            if format_string:
                handler.setFormatter(logging.Formatter(format_string, datefmt=date_format))


logger = get_logger()
