"""
Tests for UI-01 (ENABLE_UI toggle), app startup, and core endpoint reachability.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture
def client_ui_enabled(monkeypatch, clear_settings_cache):
    """TestClient with ENABLE_UI=true."""
    monkeypatch.setenv("ENABLE_UI", "true")
    get_settings.cache_clear()
    # Re-import app after env change
    import importlib
    import app.main as app_module
    importlib.reload(app_module)
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def client_ui_disabled(monkeypatch, clear_settings_cache):
    """TestClient with ENABLE_UI=false."""
    monkeypatch.setenv("ENABLE_UI", "false")
    get_settings.cache_clear()
    import importlib
    import app.main as app_module
    importlib.reload(app_module)
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def client(clear_settings_cache):
    """Default TestClient (ENABLE_UI=true by default)."""
    from app.main import app
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestUI01UIToggle:
    """UI-01: ENABLE_UI=true -> HTML root, ENABLE_UI=false -> JSON root."""

    def test_ui_enabled_returns_html(self, client_ui_enabled):
        resp = client_ui_enabled.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_ui_disabled_returns_json(self, client_ui_disabled):
        resp = client_ui_disabled.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "service" in data
        assert data["service"] == "Document Encryption API"


class TestEndpointReachability:
    """Verify all migrated endpoints are registered (not 404/405)."""

    def test_encrypt_endpoint_exists(self, client):
        # POST with no body -> 422 Unprocessable Entity (not 404 Not Found)
        resp = client.post("/api/encrypt")
        assert resp.status_code == 422

    def test_decrypt_endpoint_exists(self, client):
        resp = client.post("/api/decrypt")
        assert resp.status_code == 422

    def test_download_unknown_file_returns_404(self, client):
        resp = client.get("/api/download/nonexistent-id/encrypted")
        assert resp.status_code == 404
