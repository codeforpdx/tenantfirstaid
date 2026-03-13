"""
ensure that only keys that should exist are readable
ensure that symbols are read-only
"""

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    LETTER_TEMPLATE,
    OREGON_LAW_CENTER_PHONE_NUMBER,
)


def test_default_instructions_contains_oregon_law_center_phone():
    assert OREGON_LAW_CENTER_PHONE_NUMBER in DEFAULT_INSTRUCTIONS


def test_default_instructions_contains_citation_links():
    assert "oregon.public.law" in DEFAULT_INSTRUCTIONS


def test_letter_template_contains_placeholders():
    assert "[Your Name]" in LETTER_TEMPLATE
    assert "[Your Street Address]" in LETTER_TEMPLATE
    assert "ORS 90.320" in LETTER_TEMPLATE


def test_import_constants():
    from tenantfirstaid.constants import SINGLETON

    assert SINGLETON is not None


def test_system_prompt_placeholders_are_substituted():
    """Ensure str.format() placeholders are resolved, not left raw."""
    assert "{RESPONSE_WORD_LIMIT}" not in DEFAULT_INSTRUCTIONS
    assert "{OREGON_LAW_CENTER_PHONE_NUMBER}" not in DEFAULT_INSTRUCTIONS


def test_system_prompt_has_no_stray_placeholders():
    """Guard against someone adding an unrecognised {placeholder} to system_prompt.md."""
    import re

    # Match {WORD} but not markdown links like [text](url) or tool names like `{text}`.
    stray = re.findall(r"(?<!\[)(?<!`)\{[A-Z_]+\}(?!`)(?!\])", DEFAULT_INSTRUCTIONS)
    assert stray == [], f"Unsubstituted placeholders found: {stray}"
