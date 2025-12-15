"""
ensure that only keys that should exist are readable
ensure that symbols are read-only
"""

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    OREGON_LAW_CENTER_PHONE_NUMBER,
)


def test_default_instructions_contains_oregon_law_center_phone():
    assert OREGON_LAW_CENTER_PHONE_NUMBER in DEFAULT_INSTRUCTIONS


def test_default_instructions_contains_citation_links():
    assert "https://oregon.public.law/statutes" in DEFAULT_INSTRUCTIONS
    assert 'target="_blank"' in DEFAULT_INSTRUCTIONS


def test_import_constants():
    from tenantfirstaid.constants import SINGLETON

    assert SINGLETON is not None
