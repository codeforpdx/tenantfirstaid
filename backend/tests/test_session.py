import pytest
from tenantfirstaid.session import TenantSession


@pytest.fixture
def mock_valkey(mocker):
    """Mock the Valkey class with the db_con.ping(), db_con.get(), and db_con.set() methods."""
    mock_client = mocker.Mock()
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_client)

    _data = {}

    mock_client.set = mocker.Mock(
        side_effect=lambda key, value: _data.update({key: value})
    )
    mock_client.get = mocker.Mock(side_effect=lambda key: _data.get(key, None))
    mock_client.ping = mocker.Mock()
    return mock_client


@pytest.fixture
def mock_environ(monkeypatch):
    monkeypatch.setenv("DB_HOST", "8.8.8.8")
    monkeypatch.setenv("DB_PORT", "8888")
    monkeypatch.setenv("DB_PASSWORD", "test_password")
    monkeypatch.setenv("DB_USE_SSL", "false")


def test_session_set_and_get(mock_valkey, mock_environ):
    tenant_session = TenantSession()

    mock_valkey.get.return_value = '"test_value"'
    tenant_session.set("some_session_id", "test_value")
    value = tenant_session.get("some_session_id")
    assert value == "test_value"


def test_session_get_unknown_session_id(mock_valkey, mock_environ):
    tenant_session = TenantSession()

    mock_valkey.get.return_value = None
    value = tenant_session.get("some_session_id")
    assert value == []


def test_session_init_ping_exception(mocker, mock_environ, capsys):
    # Patch Valkey so that ping raises an exception
    mock_client = mocker.Mock()
    mock_client.ping = mocker.Mock(side_effect=Exception("Ping failed"))
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_client)
    # Should not raise, but print the exception
    _obj = TenantSession()
    captured = capsys.readouterr()
    assert "Ping failed" in captured.out
