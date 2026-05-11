"""Project-wide logging configuration.

Importing this module is side-effect-free; call `configure_logging()` from an
entrypoint (e.g. `constants.py` at first import, or a CLI script) to install
a single stderr handler with the colorized format used across the codebase.
"""

import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class _ColoredLevelFormatter(logging.Formatter):
    """Formatter that colorizes the level name when emitting to a TTY.

    The TTY check happens once at construction (based on `sys.stderr`), so
    log files and CI captures stay free of ANSI escapes.
    """

    _LEVEL_COLORS = {
        logging.WARNING: "\033[33m",  # Yellow.
        logging.ERROR: "\033[31m",  # Red.
        logging.CRITICAL: "\033[1;31m",  # Bold red.
    }
    _RESET = "\033[0m"

    def __init__(self) -> None:
        super().__init__(_FORMAT)
        self._use_color = sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        if self._use_color and record.levelno in self._LEVEL_COLORS:
            original = record.levelname
            record.levelname = (
                f"{self._LEVEL_COLORS[record.levelno]}{original}{self._RESET}"
            )
            try:
                return super().format(record)
            finally:
                record.levelname = original
        return super().format(record)


def _make_stderr_handler() -> logging.StreamHandler:
    """Build a stderr handler wired with the project formatter."""
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(_ColoredLevelFormatter())
    return handler


def configure_logging() -> None:
    """Install a single stderr handler with the project formatter.

    Idempotent: if the root logger already has a handler, this is a no-op so
    we don't double-log under pytest, gunicorn, or repeated imports.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    root.addHandler(_make_stderr_handler())
    root.setLevel(logging.DEBUG if os.getenv("ENV") == "dev" else logging.INFO)


@contextmanager
def temporary_formatted_handler(logger: logging.Logger) -> Iterator[None]:
    """Attach the project formatter to `logger` for the duration of the block.

    Useful at module-import time when the root logger has not yet been
    configured by an entrypoint, but a module wants its own warnings to
    appear in the project format. Propagation is suspended inside the block
    so the message is not also emitted via Python's `lastResort` handler.
    """
    handler = _make_stderr_handler()
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.propagate = previous_propagate
