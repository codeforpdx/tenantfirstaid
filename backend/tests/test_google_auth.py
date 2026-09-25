"""Tests for how credential-loading failures are reported.

The message matters more than usual here. It is the first thing a new
contributor sees when they have not authenticated yet, and the value it is
describing may itself be a secret -- so the tests below pin both halves: say
something actionable when the value cannot be a credential, and say nothing
about it when it might be.
"""

import pytest

from tenantfirstaid.google_auth import load_gcp_credentials


class TestMissingCredentialsFile:
    def test_a_path_that_does_not_exist_says_so_and_names_the_fix(self):
        """Previously reported as a JSON parse error, which described neither
        the problem nor anything the reader could act on.
        """
        with pytest.raises(ValueError) as excinfo:
            load_gcp_credentials("/nonexistent/application_default_credentials.json")

        message = str(excinfo.value)
        assert "does not exist" in message
        assert "/nonexistent/application_default_credentials.json" in message
        assert "gcloud-login" in message

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param(
                '"type": "service_account", "private_key": "-----BEGIN PRIVATE KEY-----"',
                id="truncated-inline-json-without-a-leading-brace",
            ),
            pytest.param(
                '  {"type": "service_account"',
                id="leading-whitespace-and-unterminated",
            ),
        ],
    )
    def test_a_value_that_might_be_a_secret_is_never_echoed(self, raw):
        """The missing-file message quotes the value, so it must fire only on
        something that cannot be a credential. A *truncated* secret is exactly
        the value that may lack a leading brace, so the brace alone cannot be
        the discriminator -- whitespace and quote characters are.
        """
        with pytest.raises(ValueError) as excinfo:
            load_gcp_credentials(raw)

        message = str(excinfo.value)
        assert "private_key" not in message
        assert "BEGIN PRIVATE KEY" not in message
        assert "does not exist" not in message

    def test_well_formed_json_is_still_judged_on_its_type(self):
        """The path branch must not swallow a value the parser can explain."""
        with pytest.raises(ValueError, match="Unsupported credential type: bogus"):
            load_gcp_credentials('{"type": "bogus"}')
