"""Unit tests for tenantfirstaid.logger helpers."""

import ast
import logging
import uuid
from pathlib import Path

from tenantfirstaid import logger as logger_module
from tenantfirstaid.logger import temporary_formatted_handler


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


def _fresh_logger() -> logging.Logger:
    """Return an isolated logger with a unique name and no handlers."""
    logger = logging.getLogger(f"test.tfa.{uuid.uuid4()}")
    logger.handlers.clear()
    logger.propagate = True
    return logger


class TestTemporaryFormattedHandler:
    def test_attaches_handler_inside_block(self):
        logger = _fresh_logger()
        pre = list(logger.handlers)
        with temporary_formatted_handler(logger):
            assert len(logger.handlers) == len(pre) + 1
            assert isinstance(logger.handlers[-1], logging.StreamHandler)
            assert logger.handlers[-1].formatter is not None

    def test_suspends_propagation_inside_block(self):
        logger = _fresh_logger()
        logger.propagate = True
        with temporary_formatted_handler(logger):
            assert logger.propagate is False

    def test_restores_state_on_exit(self):
        logger = _fresh_logger()
        logger.propagate = True
        pre_handlers = list(logger.handlers)
        with temporary_formatted_handler(logger):
            pass
        assert logger.handlers == pre_handlers
        assert logger.propagate is True

    def test_restores_state_on_exception(self):
        logger = _fresh_logger()
        logger.propagate = True
        pre_handlers = list(logger.handlers)
        try:
            with temporary_formatted_handler(logger):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert logger.handlers == pre_handlers
        assert logger.propagate is True

    def test_preserves_prior_propagate_setting(self):
        # When the caller has already disabled propagation, the context manager
        # must leave it disabled on exit (not flip it back to True).
        logger = _fresh_logger()
        logger.propagate = False
        with temporary_formatted_handler(logger):
            assert logger.propagate is False
        assert logger.propagate is False

    def test_emits_record_through_temporary_handler(self):
        # Sanity check that the attached handler actually formats the record
        # using the project format (timestamp + bracketed level + logger name).
        import io

        logger = _fresh_logger()
        logger.setLevel(logging.WARNING)
        with temporary_formatted_handler(logger):
            # Redirect the handler's stream to a buffer so we can read the output.
            handler = logger.handlers[-1]
            buf = io.StringIO()
            assert isinstance(handler, logging.StreamHandler)
            handler.stream = buf
            logger.warning("hello %s", "world")
        out = buf.getvalue()
        assert "[WARNING]" in out
        assert logger.name in out
        assert "hello world" in out
