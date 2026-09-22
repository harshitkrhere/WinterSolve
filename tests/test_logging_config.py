from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from wintersolve.logging_config import (
    DEFAULT_DATE_FORMAT,
    DEFAULT_FORMAT,
    configure_logging,
    get_logger,
    set_log_level,
)


@pytest.fixture(autouse=True)
def restore_defaults() -> Iterator[None]:
    """Logging is process-wide; put it back the way every other test expects."""
    yield
    configure_logging(
        level=logging.WARNING, format_string=DEFAULT_FORMAT, date_format=DEFAULT_DATE_FORMAT
    )


class TestLogging:
    def test_loggers_are_quiet_and_do_not_touch_the_root_logger(self) -> None:
        logger = get_logger("wintersolve.tests.quiet")

        assert logger.level == logging.WARNING
        assert logger.propagate is False
        assert get_logger("wintersolve.tests.quiet") is logger

    def test_set_log_level_reaches_loggers_and_their_handlers(self) -> None:
        logger = get_logger("wintersolve.tests.level")

        set_log_level(logging.DEBUG)

        assert logger.level == logging.DEBUG
        assert all(handler.level == logging.DEBUG for handler in logger.handlers)

    def test_configure_logging_can_change_the_message_format(self) -> None:
        logger = get_logger("wintersolve.tests.format")
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)

        configure_logging(level=logging.INFO, format_string="%(levelname)s %(message)s")

        assert logger.level == logging.INFO
        assert logger.handlers[0].format(record) == "INFO hello"
