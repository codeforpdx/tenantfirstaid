"""Authored text the agent serves, and the values substituted into it.

Genuinely constant: nothing here is read from the environment or varies by
deployment. The application's *configuration*, which is none of those things,
lives in :mod:`tenantfirstaid.config` -- importing that costs a complete, valid
environment, and a letter template is no reason to require one.
"""

from pathlib import Path
from typing import Final

from .referrals import REFERRALS_BY_ID

# Sourced from the "laso" entry in referrals_data.json — the single source of
# truth shared with the agent and the Referrals page, so the phone number can't
# drift between the system prompt and the referral catalog.
_laso_phone = REFERRALS_BY_ID["laso"].phone
if _laso_phone is None:
    raise ValueError("referrals_data.json 'laso' entry has no phone number")
OREGON_LAW_CENTER_PHONE_NUMBER: Final[str] = _laso_phone

RESPONSE_WORD_LIMIT: Final = 350
"""Target word limit for model responses."""

_SYSTEM_PROMPT_PATH: Final = Path(__file__).parent / "system_prompt.md"
"""File path to the system prompt template."""


def _load_system_prompt() -> str:
    """Load the system prompt from the external markdown file.

    Reads system_prompt.md and substitutes placeholders for RESPONSE_WORD_LIMIT
    and OREGON_LAW_CENTER_PHONE_NUMBER.

    Returns:
        System prompt string with placeholders substituted.

    Raises:
        FileNotFoundError: If the system prompt file cannot be read.
    """
    template = _SYSTEM_PROMPT_PATH.read_text()
    return template.format(
        RESPONSE_WORD_LIMIT=RESPONSE_WORD_LIMIT,
        OREGON_LAW_CENTER_PHONE_NUMBER=OREGON_LAW_CENTER_PHONE_NUMBER,
    )


DEFAULT_INSTRUCTIONS: Final = _load_system_prompt()
"""Default system prompt with placeholders substituted for word limit and law center phone number."""

_LETTER_TEMPLATE_PATH: Final = Path(__file__).parent / "letter_template.md"
"""File path to the letter template."""

LETTER_TEMPLATE: Final = _LETTER_TEMPLATE_PATH.read_text()
"""Letter template markdown with placeholder fields for the agent to fill in."""
