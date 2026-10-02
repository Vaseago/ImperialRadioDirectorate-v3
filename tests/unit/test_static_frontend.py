"""Unit tests for the Phase 6 static frontend mount — confirms `index.html`
and its JS assets are served, with no-cache headers, and that API routes
still take precedence over the catch-all static mount."""

from __future__ import annotations

from fastapi.testclient import TestClient

from web.app import create_app


def test_index_html_is_served_at_root(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Imperial Radio Directorate" in resp.text


def test_static_js_asset_is_served_with_no_cache_header(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/js/app.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-cache"


def test_api_routes_still_take_precedence_over_static_mount(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/api/music/stations")
    assert resp.status_code == 200
    assert resp.json() == {"stations": []}
