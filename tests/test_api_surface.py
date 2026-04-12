"""
Phase 4 API surface test scaffold.

Tests for API-04 (OpenAPI annotations), KEY-01/KEY-02 (key generation), INSP-01 (file inspection).

TestOpenAPIAnnotations — GREEN (docs live, schema has typed responses after Task 2).
TestKeyGeneration     — RED  (POST /api/keys/generate not registered yet — 404).
TestFileInspect       — RED  (POST /api/files/inspect not registered yet — 404).
"""
import io
import os
import struct

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper: minimal valid encrypted file bytes (matches CryptoConstants layout)
# ---------------------------------------------------------------------------

def _make_valid_enc_bytes() -> bytes:
    """Construct a minimal but structurally valid encrypted file header.

    Layout matches the verified binary format from RESEARCH.md / config/constants.py:
      0..5   magic         b'DOCENC'
      6..7   version       major=1, minor=0
      8..11  flags         uint32 LE  (0b00001111 = all standard flags)
      12..19 timestamp     uint64 LE
      20..23 separator     b'\\xFF\\xFE\\xFD\\xFC'
      24..25 file_type_len uint16 LE
      26..29 file_type     b'text'
      30..31 filename_len  uint16 LE
      32..39 filename      b'test.txt'
      40..47 original_size uint64 LE
      48..55 compressed_size uint64 LE
      56+    padding
    """
    buf = b""
    buf += b"DOCENC"                              # magic (6 bytes)
    buf += b"\x01\x00"                            # version major=1, minor=0 (2 bytes)
    buf += struct.pack("<I", 0b00001111)           # flags uint32 LE (4 bytes)
    buf += struct.pack("<Q", 1700000000)           # timestamp uint64 LE (8 bytes)
    buf += b"\xFF\xFE\xFD\xFC"                    # HEADER_SEPARATOR (4 bytes)
    buf += struct.pack("<H", 4) + b"text"         # file_type_len + file_type
    buf += struct.pack("<H", 8) + b"test.txt"     # filename_len + filename
    buf += struct.pack("<Q", 100)                  # original_size (8 bytes)
    buf += struct.pack("<Q", 80)                   # compressed_size (8 bytes)
    buf += b"\x00" * 100                           # padding
    return buf


# ---------------------------------------------------------------------------
# TestOpenAPIAnnotations — should be GREEN after Task 2
# ---------------------------------------------------------------------------

class TestOpenAPIAnnotations:
    """API-04: /docs available and OpenAPI schema includes new response model names."""

    def test_docs_endpoint_available(self):
        """GET /docs must return 200 with Swagger UI HTML."""
        resp = client.get("/docs")
        assert resp.status_code == 200, f"Expected 200 from /docs, got {resp.status_code}"
        assert "swagger" in resp.text.lower() or "openapi" in resp.text.lower(), (
            "/docs response does not look like Swagger UI"
        )

    def test_openapi_schema_has_typed_responses(self):
        """GET /openapi.json must include KeyGenerateResponse and InspectResponse in components."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        text = resp.text
        assert "KeyGenerateResponse" in text, (
            "OpenAPI schema missing KeyGenerateResponse — check schemas/common.py and route annotations"
        )
        assert "InspectResponse" in text, (
            "OpenAPI schema missing InspectResponse — check schemas/common.py and route annotations"
        )


# ---------------------------------------------------------------------------
# TestKeyGeneration — RED until Plan 02 registers POST /api/keys/generate
# ---------------------------------------------------------------------------

class TestKeyGeneration:
    """KEY-01 / KEY-02: RSA-4096 key pair generation endpoint."""

    def test_generate_keys_returns_200(self):
        """POST /api/keys/generate must return HTTP 200 (RED — route not registered yet)."""
        resp = client.post("/api/keys/generate")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Route not registered yet — RED state is correct."
        )

    def test_public_key_pem_format(self):
        """Returned public_key must be PEM starting with '-----BEGIN PUBLIC KEY-----'."""
        resp = client.post("/api/keys/generate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_key"].startswith("-----BEGIN PUBLIC KEY-----"), (
            f"public_key PEM header wrong: {data['public_key'][:50]}"
        )

    def test_private_key_pkcs8_pem_format(self):
        """Returned private_key must be PKCS8 PEM starting with '-----BEGIN PRIVATE KEY-----'."""
        resp = client.post("/api/keys/generate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["private_key"].startswith("-----BEGIN PRIVATE KEY-----"), (
            f"private_key PEM header wrong: {data['private_key'][:50]}"
        )

    def test_key_size_and_format_fields(self):
        """Response must contain key_size==4096 and format=='PEM'."""
        resp = client.post("/api/keys/generate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key_size"] == 4096, f"Expected key_size=4096, got {data.get('key_size')}"
        assert data["format"] == "PEM", f"Expected format='PEM', got {data.get('format')}"

    def test_no_files_written_to_disk(self, tmp_path, monkeypatch):
        """POST /api/keys/generate must not create any files in temp_dir (KEY-02: no server storage)."""
        monkeypatch.setenv("TEMP_DIR", str(tmp_path))
        from app.config import get_settings
        get_settings.cache_clear()

        files_before = set(str(p) for p in tmp_path.rglob("*") if p.is_file())
        client.post("/api/keys/generate")
        files_after = set(str(p) for p in tmp_path.rglob("*") if p.is_file())

        new_files = files_after - files_before
        assert not new_files, (
            f"Key generation wrote unexpected files to disk: {new_files}"
        )

        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# TestFileInspect — RED until Plan 02 registers POST /api/files/inspect
# ---------------------------------------------------------------------------

class TestFileInspect:
    """INSP-01: encrypted file header inspection without decryption key."""

    def test_inspect_valid_file_returns_200(self):
        """POST /api/files/inspect with a valid .enc file must return HTTP 200."""
        content = _make_valid_enc_bytes()
        resp = client.post(
            "/api/files/inspect",
            files={"file": ("test.enc", io.BytesIO(content), "application/octet-stream")},
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Route not registered yet — RED state is correct."
        )

    def test_inspect_response_has_required_fields(self):
        """Inspect response must include all required header metadata fields."""
        content = _make_valid_enc_bytes()
        resp = client.post(
            "/api/files/inspect",
            files={"file": ("test.enc", io.BytesIO(content), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "format_version", "original_filename", "file_type",
            "timestamp", "flags", "original_size", "compressed_size",
        ]
        for field in required_fields:
            assert field in data, f"Missing field '{field}' in inspect response"

    def test_inspect_invalid_file_returns_422(self):
        """POST /api/files/inspect with non-encrypted bytes must return HTTP 422."""
        resp = client.post(
            "/api/files/inspect",
            files={"file": ("bad.enc", io.BytesIO(b"NOTVALID"), "application/octet-stream")},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid file, got {resp.status_code}"
        )

    def test_inspect_truncated_file_returns_422(self):
        """POST /api/files/inspect with truncated bytes must return HTTP 422 (not 500)."""
        resp = client.post(
            "/api/files/inspect",
            files={"file": ("truncated.enc", io.BytesIO(b"\x00" * 5), "application/octet-stream")},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for truncated file, got {resp.status_code}. "
            "If 500, struct.error is not being caught in the inspect handler."
        )
