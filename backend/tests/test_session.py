import pytest
from flask import Flask
from tenantfirstaid.session import TenantSession, InitSessionView
from typing import Dict, Any


@pytest.fixture
def mock_valkey_ping_nop(mocker):
    """Mock the Valkey class with the db_con.ping() method."""
    mock_valkey_client = mocker.Mock()
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_valkey_client)
    mock_valkey_client.ping = mocker.Mock()
    return mock_valkey_client


@pytest.fixture
def mock_valkey(mock_valkey_ping_nop, mocker):
    _data: Dict[str, str] = {}

    mock_valkey_ping_nop.set = mocker.Mock(
        side_effect=lambda key, value: _data.update({key: value})
    )

    mock_valkey_ping_nop.get = mocker.Mock(side_effect=lambda key: _data[key])

    return mock_valkey_ping_nop


@pytest.fixture
def mock_environ(monkeypatch):
    monkeypatch.setenv("DB_HOST", "8.8.8.8")
    monkeypatch.setenv("DB_PORT", "8888")
    monkeypatch.setenv("DB_PASSWORD", "test_password")
    monkeypatch.setenv("DB_USE_SSL", "false")


def test_session_init_success(mocker, mock_environ):
    test_data = {
        "city": "Test City",
        "state": "Test State",
    }

    mock_valkey_client = mocker.Mock()
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_valkey_client)
    mock_valkey_client.ping = mocker.Mock()

    tenant_session = TenantSession()
    app = Flask(__name__)
    app.add_url_rule(
        "/api/init",
        view_func=InitSessionView.as_view("init", tenant_session),
        methods=["POST"],
    )
    app.secret_key = "test_secret_key"  # Set a secret key for session management

    with app.test_request_context("/api/init", method="POST", json=test_data) as reqctx:
        assert (
            reqctx.session.get("session_id") is None
        )  # Ensure session_id is NOT set in the request context (before dispatch)
        response = app.full_dispatch_request()
        assert response.status_code == 200  # Ensure the response is successful
        assert (
            reqctx.session.get("session_id") is not None
        )  # Ensure session_id is set in the request context


def test_session_init_ping_exception(mocker, capsys):
    # Patch Valkey so that ping raises an exception
    mock_client = mocker.Mock()
    mock_client.ping = mocker.Mock(side_effect=Exception("Ping failed"))
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_client)
    # Should not raise, but print the exception
    _obj = TenantSession()
    captured = capsys.readouterr()
    assert "Ping failed" in captured.out


def test_session_get_unknown_session_id(mocker, mock_environ):
    test_data = {"city": "Test City", "state": "Test State", "messages": []}

    mock_valkey_client = mocker.Mock()
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_valkey_client)
    mock_valkey_client.ping = mocker.Mock()

    tenant_session = TenantSession()
    app = Flask(__name__)
    app.add_url_rule(
        "/api/init",
        view_func=InitSessionView.as_view("init", tenant_session),
        methods=["POST"],
    )
    app.secret_key = "test_secret_key"  # Set a secret key for session management

    with app.test_request_context("/api/init", method="POST", json=test_data) as reqctx:
        assert (
            reqctx.session.get("session_id") is None
        )  # Ensure session_id is NOT set in the request context (before dispatch)
        assert tenant_session.get() == {
            "city": "",
            "state": "",
            "messages": [],
        }


def test_session_set_and_get(mocker, mock_environ, mock_valkey):
    test_data_obj: Dict[str, Any] = {
        "city": "Test City",
        "state": "Test State",
        "messages": ["this is message 1", "this is message 2"],
    }

    tenant_session = TenantSession()
    app = Flask(__name__)
    app.add_url_rule(
        "/api/init",
        view_func=InitSessionView.as_view("init", tenant_session),
        methods=["POST"],
    )
    app.secret_key = "test_secret_key"  # Set a secret key for session management

    with app.test_request_context("/api/init", method="POST", json=test_data_obj):
        response = app.full_dispatch_request()
        assert response.status_code == 200  # Ensure the response is successful
        session_id = response.json["session_id"]
        assert session_id is not None  # Ensure session_id is set
        assert isinstance(session_id, str)  # Ensure session_id is a string

        tenant_session.set(session_id, test_data_obj)
        assert tenant_session.get() == test_data_obj


def test_session_set_some_and_get_none(mocker, mock_environ, mock_valkey):
    test_data_obj: Dict[str, Any] = {
        "city": "Test City",
        "state": "Test State",
        "messages": ["this is message 1", "this is message 2"],
    }

    tenant_session = TenantSession()
    app = Flask(__name__)
    app.add_url_rule(
        "/api/init",
        view_func=InitSessionView.as_view("init", tenant_session),
        methods=["POST"],
    )
    app.secret_key = "test_secret_key"  # Set a secret key for session management

    # Simulate no data for the session (i.e. network error or similar)
    mock_valkey.get.side_effect = lambda key: None

    with app.test_request_context("/api/init", method="POST", json=test_data_obj):
        response = app.full_dispatch_request()
        assert response.status_code == 200  # Ensure the response is successful
        session_id = response.json["session_id"]
        assert session_id is not None  # Ensure session_id is set
        assert isinstance(session_id, str)  # Ensure session_id is a string

        tenant_session.set(session_id, test_data_obj)
        assert tenant_session.get() == {
            "city": "",
            "state": "",
            "messages": [],
        }
