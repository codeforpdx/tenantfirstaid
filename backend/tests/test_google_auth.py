"""Tests for how credential-loading failures are reported.

The message matters more than usual here. It is the first thing a new
contributor sees when they have not authenticated yet, and the value it is
describing may itself be a secret -- so the tests below pin both halves: say
something actionable when the value cannot be a credential, and say nothing
about it when it might be.
"""

import base64
import json

import pytest
from google.oauth2.credentials import Credentials

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

    def test_a_base64_encoded_key_is_never_echoed(self):
        """Base64 has neither whitespace nor quotes, so the test above passes it.

        Some secret stores inject service-account keys that way, and the value
        would otherwise have been quoted into the exception in full. The base64
        alphabet includes "/", so the fixture is chosen to contain one -- a
        separator alone must not be read as a path.
        """
        encoded = base64.b64encode(
            json.dumps(
                {"type": "service_account", "private_key": "s3cret", "pad": "??"}
            ).encode()
        ).decode()
        assert "/" in encoded and "." not in encoded, (
            "fixture must contain '/' but not '.'"
        )

        with pytest.raises(ValueError) as excinfo:
            load_gcp_credentials(encoded)

        message = str(excinfo.value)
        assert "does not exist" not in message
        assert encoded not in message

    def test_an_absurdly_long_path_is_truncated(self):
        """The shape tests are heuristics; the length bound is not.

        It is what keeps an encoding nobody anticipated from reaching the logs
        whole, so a value that looks like a path is still bounded.
        """
        raw = "/nonexistent/" + "a" * 500 + ".json"

        with pytest.raises(ValueError) as excinfo:
            load_gcp_credentials(raw)

        message = str(excinfo.value)
        assert "does not exist" in message
        assert raw not in message
        assert f"({len(raw)} characters)" in message

    def test_well_formed_json_is_still_judged_on_its_type(self):
        """The path branch must not swallow a value the parser can explain."""
        with pytest.raises(ValueError, match="Unsupported credential type: bogus"):
            load_gcp_credentials('{"type": "bogus"}')


class TestTildeExpansion:
    def test_a_tilde_prefixed_path_is_expanded(self, tmp_path, monkeypatch):
        """Neither `python-dotenv` nor `Path.is_file()` expand `~`, so a real
        file named that way previously fell through to the missing-file
        error even though it existed.
        """
        monkeypatch.setenv("HOME", str(tmp_path))
        creds_dir = tmp_path / ".config" / "gcloud"
        creds_dir.mkdir(parents=True)
        creds_file = creds_dir / "application_default_credentials.json"
        creds_file.write_text(
            json.dumps(
                {
                    "type": "authorized_user",
                    "client_id": "id",
                    "client_secret": "secret",
                    "refresh_token": "token",
                }
            )
        )

        credentials = load_gcp_credentials(
            "~/.config/gcloud/application_default_credentials.json"
        )

        assert isinstance(credentials, Credentials)
        assert credentials.refresh_token == "token"
