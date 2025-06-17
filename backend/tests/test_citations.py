import pytest
from flask import Flask
from tenantfirstaid.citations import get_citation, SECTIONS


@pytest.fixture
def app():
    app = Flask(__name__)
    app.add_url_rule("/api/citation", view_func=get_citation, methods=["GET"])
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_citation_success(client):
    # Use a valid section from SECTIONS
    section = next(iter(SECTIONS))
    response = client.get(f"/api/citation?section={section}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["section"] == section
    assert data["text"] == SECTIONS[section]


def test_get_citation_missing_param(client):
    response = client.get("/api/citation")
    assert response.status_code == 400
    assert b"missing query param" in response.data


def test_get_citation_unknown_section(client):
    response = client.get("/api/citation?section=notarealsection")
    assert response.status_code == 404
    assert b"not found" in response.data


def test_get_citation_empty_section_param(client):
    response = client.get("/api/citation?section=")
    assert response.status_code == 400
    assert b"missing query param" in response.data
