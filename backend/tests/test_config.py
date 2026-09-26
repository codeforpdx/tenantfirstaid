"""Tests for the composed application configuration singleton."""

import logging
import re
from unittest.mock import patch

import pytest

from tenantfirstaid.config import _AppConfig
from tenantfirstaid.google_models import Gemini25ModelConfig, ModelConfig


class TestAppConfig:
    @pytest.fixture
    def no_env_file(self):
        # Force the "no .env" code path so the test relies purely on the
        # ambient os.environ injected by patch.dict.
        with patch("tenantfirstaid.google_auth.Path.exists", return_value=False):
            yield

    @pytest.fixture
    def silence_missing_env_warning(self, caplog):
        # The "no .env" path emits a warning; tests that don't want to assert
        # on it can opt into this fixture to keep test output clean.
        caplog.set_level(logging.CRITICAL, logger="tenantfirstaid.google_auth")

    REQUIRED_ENV = {
        "MODEL_NAME": "gemini-2.5-pro",
        "VERTEX_AI_DATASTORE_LAWS": "test-datastore",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/creds.json",
    }

    @patch.dict("os.environ", REQUIRED_ENV, clear=False)
    def test_init_with_all_vars(self, no_env_file, silence_missing_env_warning):
        singleton = _AppConfig()
        assert singleton.MODEL_NAME == "gemini-2.5-pro"
        assert singleton.GOOGLE_CLOUD_PROJECT == "test-project"
        assert singleton.VERTEX_AI_DATASTORES["laws"] == "test-datastore"

    @pytest.mark.parametrize("missing_var", REQUIRED_ENV.keys())
    def test_missing_required_var_raises(
        self, missing_var, no_env_file, silence_missing_env_warning
    ):
        env = {k: v for k, v in self.REQUIRED_ENV.items() if k != missing_var}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="environment variable is not set"):
                _AppConfig()

    @pytest.mark.parametrize(
        "identity_var",
        [
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ],
    )
    def test_whitespace_only_identity_var_is_treated_as_unset(
        self, identity_var, no_env_file, silence_missing_env_warning
    ):
        """Otherwise it is carried into a resource path and fails much later."""
        env = {**self.REQUIRED_ENV, identity_var: "   "}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match=f"\\[{identity_var}\\]"):
                _AppConfig()

    def test_surrounding_whitespace_is_stripped(
        self, no_env_file, silence_missing_env_warning
    ):
        env = {**self.REQUIRED_ENV, "GOOGLE_CLOUD_PROJECT": "  test-project\n"}
        with patch.dict("os.environ", env, clear=True):
            assert _AppConfig().GOOGLE_CLOUD_PROJECT == "test-project"

    def test_missing_env_file_emits_warning_with_resolved_path(
        self, no_env_file, caplog
    ):
        caplog.set_level(logging.WARNING, logger="tenantfirstaid.google_auth")
        with patch.dict("os.environ", self.REQUIRED_ENV, clear=False):
            _AppConfig()
        warnings = [r for r in caplog.records if r.name == "tenantfirstaid.google_auth"]
        assert warnings, "expected a warning when .env is missing"
        msg = warnings[-1].getMessage()
        assert "No .env file found" in msg
        # The resolved path is absolute and ends at the package's sibling .env.
        # Assert the suffix only, not the parent directory name, so the test holds
        # regardless of where the app is installed (e.g. backend/ on the host vs
        # /app in the ci container image).
        assert re.search(r"/\.env, proceeding\b", msg)

    def test_missing_laws_datastore_raises(
        self, no_env_file, silence_missing_env_warning
    ):
        env = {
            **self.REQUIRED_ENV,
            "VERTEX_AI_DATASTORE_OREGONLAWHELP": "store-1",
        }
        del env["VERTEX_AI_DATASTORE_LAWS"]
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="VERTEX_AI_DATASTORE_LAWS"):
                _AppConfig()


def test_model_config_values():
    """Pin model config values that affect legal advice quality.

    Low temperature and top_p produce consistent, citation-heavy responses
    rather than creative ones. Changing these accidentally could degrade the
    quality of legal guidance, so this test should break loudly.
    """
    from tenantfirstaid.config import SINGLETON

    assert SINGLETON.MODEL_TEMPERATURE == 0.1
    assert SINGLETON.TOP_P == 0.1
    assert SINGLETON.MAX_TOKENS == 65535
    assert isinstance(SINGLETON.SAFETY_SETTINGS, dict)
    assert len(SINGLETON.SAFETY_SETTINGS) == 5


class TestModelFamilyDispatch:
    """`MODEL_NAME` selects a family, and an unknown one must not run on 2.5's settings."""

    @pytest.fixture(autouse=True)
    def no_env_file(self, caplog):
        caplog.set_level(logging.CRITICAL, logger="tenantfirstaid.google_auth")
        with patch("tenantfirstaid.google_auth.Path.exists", return_value=False):
            yield

    @pytest.mark.parametrize("model_name", ["gemini-2.5-pro", "gemini-2.5-flash"])
    def test_gemini_25_names_resolve_to_the_25_family(self, model_name):
        with patch.dict("os.environ", {"MODEL_NAME": model_name}, clear=True):
            config = ModelConfig.from_env()
        assert isinstance(config, Gemini25ModelConfig)
        assert config.model_name == model_name
        assert config.thinking_budget == Gemini25ModelConfig.THINKING_BUDGET_DYNAMIC

    @pytest.mark.parametrize(
        "model_name", ["gemini-3-pro", "gemini-2.0-flash", "gpt-4", "gemini"]
    )
    def test_unimplemented_family_raises(self, model_name):
        # Refused rather than silently given 2.5-shaped settings: a 3.x model
        # expects a discrete thinking level, so thinking_budget would not apply.
        with patch.dict("os.environ", {"MODEL_NAME": model_name}, clear=True):
            with pytest.raises(
                NotImplementedError, match="not a supported model family"
            ):
                ModelConfig.from_env()

    def test_missing_model_name_raises_value_error_not_notimplemented(self):
        # An unset variable is a configuration error, not an unsupported family.
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="MODEL_NAME"):
                ModelConfig.from_env()

    def test_surrounding_whitespace_is_stripped(self):
        """The same treatment GcpEnvironment.from_env gives its variables --
        otherwise a value like " gemini-2.5-pro" fails the prefix match below
        with a confusing "unsupported family" error instead of resolving.
        """
        with patch.dict("os.environ", {"MODEL_NAME": " gemini-2.5-pro\n"}, clear=True):
            config = ModelConfig.from_env()
        assert config.model_name == "gemini-2.5-pro"

    def test_whitespace_only_is_treated_as_unset(self):
        with patch.dict("os.environ", {"MODEL_NAME": "   "}, clear=True):
            with pytest.raises(ValueError, match="MODEL_NAME"):
                ModelConfig.from_env()
