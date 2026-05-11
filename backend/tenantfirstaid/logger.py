"""Project-wide logging configuration.

Importing this module is side-effect-free; call `configure_logging()` from an
entrypoint (e.g. `constants.py` at first import, or a CLI script) to install
a single stderr handler with the colorized format used across the codebase.
"""

import logging
import os
import sys
from contextlib import contextmanager
from typing import Iterator


class _ColoredLevelFormatter(logging.Formatter):
    """Formatter that colorizes the level name when emitting to a TTY.

    Colors are only applied when the handler's stream is a TTY, so log files
    and CI captures stay free of ANSI escapes.
    """

    _LEVEL_COLORS = {
        logging.WARNING: "\033[33m",  # Yellow.
        logging.ERROR: "\033[31m",  # Red.
        logging.CRITICAL: "\033[1;31m",  # Bold red.
    }
    _RESET = "\033[0m"

    def __init__(self, fmt: str, use_color: bool) -> None:
        super().__init__(fmt)
        self._use_color = use_color

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


def configure_logging() -> None:
    """Install a single stderr handler with a consistent colorized format.

    Idempotent: if the root logger already has a handler, this is a no-op so
    we don't double-log under pytest, gunicorn, or repeated imports.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        _ColoredLevelFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            use_color=sys.stderr.isatty(),
        )
    )
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if os.getenv("ENV") == "dev" else logging.INFO)


@contextmanager
def temporary_formatted_handler(logger: logging.Logger) -> Iterator[None]:
    """Attach the project formatter to `logger` for the duration of the block.

    Useful at module-import time when the root logger has not yet been
    configured by an entrypoint, but a module wants its own warnings to
    appear in the project format. Propagation is suspended inside the block
    so the message is not also emitted via Python's `lastResort` handler.
    """
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        _ColoredLevelFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            use_color=sys.stderr.isatty(),
        )
    )
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.propagate = previous_propagate
