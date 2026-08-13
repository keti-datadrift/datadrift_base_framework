"""Smoke tests for the Round-15 ``ddoc serve`` GUI static assets."""
from __future__ import annotations

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    app = create_app(bind_info="testclient:0")
    return TestClient(app)


def test_index_html_served(client: TestClient):
    """GET / returns the GUI HTML, not the legacy JSON metadata."""
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "<title>ddoc" in body and "data doctor" in body
    # Tabs present
    for tab in ("Analyze drift", "Analyze EDA", "Examples", "Report", "Export", "Fetch"):
        assert tab in body, f"missing tab label: {tab}"


def test_static_app_js(client: TestClient):
    r = client.get("/static/app.js")
    assert r.status_code == 200
    ct = r.headers["content-type"].lower()
    assert "javascript" in ct or "ecmascript" in ct, ct
    assert "ddoc serve" in r.text  # banner comment in app.js


def test_static_style_css(client: TestClient):
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    assert "ddoc serve" in r.text  # banner comment in style.css


def test_healthz_still_json(client: TestClient):
    """The GUI page lives at / but /healthz must remain JSON for monitors."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["status"] == "healthy"


def test_static_404_for_missing_asset(client: TestClient):
    r = client.get("/static/does-not-exist.txt")
    assert r.status_code == 404
