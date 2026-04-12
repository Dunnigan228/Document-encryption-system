"""
Phase 3 API-hardening test suite.

Tests API-01 (consistent error response format D-01), API-02 (correct HTTP status codes),
API-03 (CORS credentials fix), and security fixes (D-09 / CR-01 password_generated removal).

Plan 01 scope:
  - TestAPI03CORS and TestSecurityFixes should go GREEN after Task 2.
  - TestAPI01ErrorFormat and TestAPI02StatusCodes remain RED until Plan 02 hardens the routes.
"""
import importlib

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(clear_settings_cache):
    """Default TestClient using the already-loaded app module."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_wildcard_cors(monkeypatch, clear_settings_cache):
    """TestClient with CORS_ORIGINS='*' (wildcard — credentials must be False)."""
    monkeypatch.setenv("CORS_ORIGINS", "*")
    get_settings.cache_clear()
    import app.main as app_module
    importlib.reload(app_module)
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def client_explicit_cors(monkeypatch, clear_settings_cache):
    """TestClient with CORS_ORIGINS='https://example.com' (explicit — credentials allowed)."""
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
    get_settings.cache_clear()
    import app.main as app_module
    importlib.reload(app_module)
    with TestClient(app_module.app) as c:
        yield c


# ---------------------------------------------------------------------------
# TestAPI01ErrorFormat — verifies D-01 structured error body on all error paths
# All tests in this class are RED until Plan 02 hardens the routes.
# ---------------------------------------------------------------------------


class TestAPI01ErrorFormat:
    """API-01: every error response has top-level error_code, message, and detail fields."""

    def test_413_has_error_code_field(self, client, monkeypatch):
        """413 response must contain error_code == 'FILE_TOO_LARGE' (RED until Plan 02)."""
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
        get_settings.cache_clear()
        oversized = b"x" * 2_097_152  # 2 MB
        resp = client.post(
            "/api/encrypt",
            files={"file": ("test.txt", oversized, "text/plain")},
            data={"password": "testpass"},
        )
        assert resp.status_code == 413
        body = resp.json()
        assert body.get("error_code") == "FILE_TOO_LARGE"

    def test_413_has_message_field(self, client, monkeypatch):
        """413 response must contain a 'message' key (RED until Plan 02)."""
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
        get_settings.cache_clear()
        oversized = b"x" * 2_097_152
        resp = client.post(
            "/api/encrypt",
            files={"file": ("test.txt", oversized, "text/plain")},
            data={"password": "testpass"},
        )
        assert resp.status_code == 413
        body = resp.json()
        assert "message" in body

    def test_415_has_error_code_field(self, client):
        """415 response must contain error_code == 'UNSUPPORTED_FORMAT' (RED until Plan 02)."""
        resp = client.post(
            "/api/encrypt",
            files={"file": ("test.xyz", b"data", "application/octet-stream")},
            data={"password": "testpass"},
        )
        assert resp.status_code == 415
        body = resp.json()
        assert body.get("error_code") == "UNSUPPORTED_FORMAT"

    def test_404_has_error_code_field(self, client):
        """404 response must contain error_code == 'NOT_FOUND' (RED until Plan 02 wires handler)."""
        resp = client.get("/api/files/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
        body = resp.json()
        assert body.get("error_code") == "NOT_FOUND"

    def test_422_has_error_code_field(self, client):
        """422 response must contain error_code == 'VALIDATION_ERROR' (RED until handler wired)."""
        resp = client.post("/api/encrypt")  # no body at all
        assert resp.status_code == 422
        body = resp.json()
        assert body.get("error_code") == "VALIDATION_ERROR"

    def test_error_body_not_nested(self, client):
        """Error body must NOT have top-level 'detail' that is itself a dict with error_code.

        FastAPI's default 422 shape wraps errors under detail=[...].
        Our handler should replace that with a flat structure.
        """
        resp = client.post("/api/encrypt")
        body = resp.json()
        # The top-level 'detail' should not be a dict that contains 'error_code'
        detail = body.get("detail")
        assert not (isinstance(detail, dict) and "error_code" in detail), (
            "Error body is nested: detail contains error_code instead of being top-level"
        )


# ---------------------------------------------------------------------------
# TestAPI02StatusCodes — verifies HTTP status codes per API-02
# All tests in this class are RED until Plan 02 hardens the routes.
# ---------------------------------------------------------------------------


class TestAPI02StatusCodes:
    """API-02: correct HTTP status codes for each error scenario."""

    def test_oversized_file_returns_413(self, client, monkeypatch):
        """Oversized upload must return HTTP 413 (RED until Plan 02)."""
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
        get_settings.cache_clear()
        oversized = b"x" * 2_097_152
        resp = client.post(
            "/api/encrypt",
            files={"file": ("test.txt", oversized, "text/plain")},
            data={"password": "testpass"},
        )
        assert resp.status_code == 413

    def test_unsupported_format_returns_415(self, client):
        """Unsupported format must return HTTP 415, not 400 (RED until Plan 02)."""
        resp = client.post(
            "/api/encrypt",
            files={"file": ("test.xyz", b"data", "application/octet-stream")},
            data={"password": "testpass"},
        )
        assert resp.status_code == 415, (
            f"Expected 415, got {resp.status_code}. Current route raises 400 — Plan 02 will fix."
        )

    def test_unknown_file_id_returns_404(self, client):
        """Unknown file_id must return HTTP 404 (not 500)."""
        resp = client.get("/api/files/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_missing_fields_returns_422(self, client):
        """Missing required form fields must return HTTP 422."""
        resp = client.post("/api/encrypt")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestAPI03CORS — verifies CORS credentials fix per API-03 / D-08 / CR-04
# These tests should go GREEN after Task 2 (CORS fix in app/main.py).
# ---------------------------------------------------------------------------


class TestAPI03CORS:
    """API-03: CORS must not combine allow_credentials=True with wildcard origins."""

    def test_wildcard_origins_no_credentials(self, client_wildcard_cors):
        """When CORS_ORIGINS='*', preflight must NOT return Allow-Credentials: true."""
        resp = client_wildcard_cors.options(
            "/api/encrypt",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_credentials = resp.headers.get("access-control-allow-credentials", "")
        # Per CORS spec, allow_credentials must not be "true" when origin is wildcard
        assert allow_credentials.lower() != "true", (
            "Wildcard CORS must not set Allow-Credentials: true — security violation"
        )

    def test_explicit_origins_allow_credentials(self, client_explicit_cors):
        """When CORS_ORIGINS='https://example.com', preflight should allow credentials."""
        resp = client_explicit_cors.options(
            "/api/encrypt",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_credentials = resp.headers.get("access-control-allow-credentials", "")
        assert allow_credentials.lower() == "true", (
            "Explicit CORS origin should allow credentials"
        )


# ---------------------------------------------------------------------------
# TestSecurityFixes — schema-level security: D-09 / CR-01
# These tests should go GREEN after Task 2 (schema + handler changes).
# ---------------------------------------------------------------------------


class TestSecurityFixes:
    """Security fixes: password_generated removal and path traversal rejection."""

    def test_encrypt_response_has_no_password_field(self):
        """EncryptResponse must not expose password_generated (D-09 / CR-01)."""
        from app.schemas.common import EncryptResponse
        assert "password_generated" not in EncryptResponse.model_fields, (
            "password_generated field must be removed from EncryptResponse to prevent key leakage"
        )

    def test_path_traversal_filename_rejected_or_sanitized(self, client):
        """Upload with path-traversal filename must NOT return 202 (must be rejected)."""
        resp = client.post(
            "/api/encrypt",
            files={"file": ("../../etc/passwd", b"sensitive", "text/plain")},
            data={"password": "testpass"},
        )
        assert resp.status_code in (400, 415, 422), (
            f"Path traversal filename should be rejected (400/415/422), got {resp.status_code}"
        )
