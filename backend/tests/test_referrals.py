"""Tests for the referral catalog: validation, phone-number sourcing, the
GET /api/referrals endpoint, and the agent's get_legal_aid_referrals tool.
"""

import json

import pytest

from tenantfirstaid.app import app as flask_app
from tenantfirstaid.constants import OREGON_LAW_CENTER_PHONE_NUMBER
from tenantfirstaid.langchain_tools import get_legal_aid_referrals
from tenantfirstaid.referrals import REFERRALS, REFERRALS_BY_ID, Referral


@pytest.fixture
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


class TestReferralsCatalog:
    def test_referrals_load_and_validate(self):
        assert len(REFERRALS) == 4
        assert all(isinstance(r, Referral) for r in REFERRALS)

    def test_ids_are_unique(self):
        ids = [r.id for r in REFERRALS]
        assert len(ids) == len(set(ids))

    def test_referrals_by_id_matches_referrals(self):
        assert set(REFERRALS_BY_ID) == {r.id for r in REFERRALS}

    def test_laso_phone_matches_system_prompt_phone(self):
        """The system prompt's OREGON_LAW_CENTER_PHONE_NUMBER must be sourced
        from the same referral record shown on the Referrals page, so the two
        can't drift apart."""
        assert REFERRALS_BY_ID["laso"].phone == OREGON_LAW_CENTER_PHONE_NUMBER


class TestReferralsEndpoint:
    def test_get_referrals_returns_200(self, client):
        resp = client.get("/api/referrals")
        assert resp.status_code == 200

    def test_get_referrals_returns_all_records(self, client):
        resp = client.get("/api/referrals")
        data = resp.get_json()
        assert len(data) == len(REFERRALS)
        assert {r["id"] for r in data} == {r.id for r in REFERRALS}

    def test_referral_shape(self, client):
        resp = client.get("/api/referrals")
        data = resp.get_json()
        laso = next(r for r in data if r["id"] == "laso")
        assert laso["organization"] == "LASO"
        assert laso["phone"] == "888-585-9638"
        assert laso["geographic_scope"] == {"state": "or", "cities": []}


class TestGetLegalAidReferralsTool:
    def test_returns_json_matching_catalog(self):
        result = get_legal_aid_referrals.invoke({})
        parsed = json.loads(result)
        assert len(parsed) == len(REFERRALS)
        assert {r["id"] for r in parsed} == {r.id for r in REFERRALS}
