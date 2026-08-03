"""Tests for the referral catalog and the agent's referral tool."""

import json

import pytest

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    OREGON_LAW_CENTER_PHONE_NUMBER,
)
from tenantfirstaid.langchain_tools import get_legal_aid_referrals
from tenantfirstaid.referrals import (
    REFERRALS,
    REFERRALS_BY_ID,
    HoursBlock,
    Referral,
    _validate_referrals,
)


class TestReferralsCatalog:
    def test_referrals_load_and_validate(self):
        assert len(REFERRALS) == 4
        assert all(isinstance(r, Referral) for r in REFERRALS)

    def test_ids_are_unique(self):
        ids = [r.id for r in REFERRALS]
        assert len(ids) == len(set(ids))

    def test_referrals_by_id_matches_referrals(self):
        assert set(REFERRALS_BY_ID) == {r.id for r in REFERRALS}

    def test_duplicate_ids_fail_validation(self):
        duplicate = REFERRALS[1].model_copy(update={"id": REFERRALS[0].id})
        with pytest.raises(ValueError, match="Referral IDs must be unique"):
            _validate_referrals([REFERRALS[0], duplicate])

    def test_unknown_referral_fields_fail_validation(self):
        data = REFERRALS[0].model_dump() | {"phon": "555"}
        with pytest.raises(ValueError):
            Referral.model_validate(data)

    def test_hours_require_24_hour_times(self):
        with pytest.raises(ValueError):
            HoursBlock(days=["monday"], start="9am", end="5pm")

    def test_hours_end_must_be_after_start(self):
        with pytest.raises(ValueError):
            HoursBlock(days=["monday"], start="17:00", end="09:00")

    def test_required_ids_fail_validation_when_missing(self):
        without_laso = [referral for referral in REFERRALS if referral.id != "laso"]
        with pytest.raises(ValueError, match=r"missing required id\(s\)"):
            _validate_referrals(without_laso)

    def test_laso_phone_matches_system_prompt_phone(self):
        """The system prompt's OREGON_LAW_CENTER_PHONE_NUMBER must be sourced
        from the same referral record shown on the Referrals page, so the two
        can't drift apart."""
        assert OREGON_LAW_CENTER_PHONE_NUMBER == "888-585-9638"
        assert REFERRALS_BY_ID["laso"].phone == "888-585-9638"
        assert OREGON_LAW_CENTER_PHONE_NUMBER in DEFAULT_INSTRUCTIONS


class TestGetLegalAidReferralsTool:
    def test_returns_all_catalog_records(self):
        result = get_legal_aid_referrals.invoke({})
        parsed = json.loads(result)
        assert len(parsed) == len(REFERRALS)
        assert {r["id"] for r in parsed} == {r.id for r in REFERRALS}

    def test_returns_json_matching_catalog(self):
        tool_data = json.loads(get_legal_aid_referrals.invoke({}))
        catalog_data = [
            referral.model_dump(mode="json", exclude_none=True)
            for referral in REFERRALS
        ]
        assert tool_data == catalog_data
