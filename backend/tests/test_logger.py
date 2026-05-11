"""Unit tests for tenantfirstaid.logger helpers."""

import ast
import logging
from pathlib import Path
from typing import Iterator

import pytest

from tenantfirstaid import logger as logger_module
from tenantfirstaid.logger import temporary_formatted_handler


@pytest.fixture
def isolated_logger(request) -> Iterator[logging.Logger]:
    """Yield a logger whose name is unique to the test, then tear it down.

    Python's `logging.getLogger(name)` interns logger objects in
    `Manager.loggerDict` for the life of the process; without explicit
    cleanup, every test would leak a named logger.
    """
    name = f"test.tfa.{request.node.name}"
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = True
    try:
        yield logger
    finally:
        logger.handlers.clear()
        logging.Logger.manager.loggerDict.pop(name, None)


def test_logger_module_does_not_import_constants():
    # logger.py must stay free of project imports so that constants.py
    # (which imports logger) can't create an import cycle.
    source = Path(logger_module.__file__).read_text()
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("tenantfirstaid"):
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # Catches both absolute (`from tenantfirstaid.X import Y`) and
            # relative (`from .X import Y`) forms.
            if node.level > 0 or (node.module or "").startswith("tenantfirstaid"):
                offenders.append(node.module or f"(relative level {node.level})")
    assert not offenders, (
        f"tenantfirstaid.logger must not import from the project; found: {offenders}"
    )


class TestTemporaryFormattedHandler:
    def test_attaches_handler_inside_block(self, isolated_logger):
        pre = list(isolated_logger.handlers)
        with temporary_formatted_handler(isolated_logger):
            assert len(isolated_logger.handlers) == len(pre) + 1
            assert isinstance(isolated_logger.handlers[-1], logging.StreamHandler)
            assert isolated_logger.handlers[-1].formatter is not None

    def test_suspends_propagation_inside_block(self, isolated_logger):
        isolated_logger.propagate = True
        with temporary_formatted_handler(isolated_logger):
            assert isolated_logger.propagate is False

    def test_restores_state_on_exit(self, isolated_logger):
        isolated_logger.propagate = True
        pre_handlers = list(isolated_logger.handlers)
        with temporary_formatted_handler(isolated_logger):
            pass
        assert isolated_logger.handlers == pre_handlers
        assert isolated_logger.propagate is True

    def test_restores_state_on_exception(self, isolated_logger):
        isolated_logger.propagate = True
        pre_handlers = list(isolated_logger.handlers)
        try:
            with temporary_formatted_handler(isolated_logger):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert isolated_logger.handlers == pre_handlers
        assert isolated_logger.propagate is True

    def test_preserves_prior_propagate_setting(self, isolated_logger):
        # When the caller has already disabled propagation, the context manager
        # must leave it disabled on exit (not flip it back to True).
        isolated_logger.propagate = False
        with temporary_formatted_handler(isolated_logger):
            assert isolated_logger.propagate is False
        assert isolated_logger.propagate is False

    def test_emits_record_through_temporary_handler(self, isolated_logger):
        # Sanity check that the attached handler actually formats the record
        # using the project format (timestamp + bracketed level + logger name).
        # Force isatty()->False so the assertion is deterministic regardless
        # of how the test is invoked (terminal vs. CI capture).
        import io
        from unittest.mock import patch

        isolated_logger.setLevel(logging.WARNING)
        with patch("sys.stderr.isatty", return_value=False):
            with temporary_formatted_handler(isolated_logger):
                # Redirect the handler's stream to a buffer so we can read the output.
                handler = isolated_logger.handlers[-1]
                buf = io.StringIO()
                assert isinstance(handler, logging.StreamHandler)
                handler.stream = buf
                isolated_logger.warning("hello %s", "world")
        out = buf.getvalue()
        assert "[WARNING]" in out
        assert "\033[" not in out, "expected no ANSI escapes when isatty=False"
        assert isolated_logger.name in out
        assert "hello world" in out
