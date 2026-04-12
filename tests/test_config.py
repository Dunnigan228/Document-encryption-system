"""
Tests for CFG-01, CFG-02, CFG-03 (app/config.py — pydantic-settings BaseSettings).
"""
import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


class TestCFG01DefaultsAndEnvReads:
    """CFG-01: Service reads all deployment settings from environment variables."""

    def test_defaults(self):
        s = Settings()
        assert s.port == 8000
        assert s.host == "0.0.0.0"
        assert s.enable_ui is True
        assert s.max_file_size_mb == 50
        assert s.file_ttl_seconds == 3600
        assert s.cors_origins == "*"
        assert s.temp_dir == "/tmp/enc_service"

    def test_env_override_max_file_size(self, monkeypatch):
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "25")
        s = Settings()
        assert s.max_file_size_mb == 25

    def test_env_override_enable_ui_false(self, monkeypatch):
        monkeypatch.setenv("ENABLE_UI", "false")
        s = Settings()
        assert s.enable_ui is False

    def test_env_override_port(self, monkeypatch):
        monkeypatch.setenv("PORT", "9000")
        s = Settings()
        assert s.port == 9000

    def test_env_override_cors_origins(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
        s = Settings()
        assert s.cors_origins == "https://example.com"


class TestCFG02FailFastValidation:
    """CFG-02: Service validates config at startup and fails fast on misconfiguration."""

    def test_invalid_max_file_size_zero(self, monkeypatch):
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "0")
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_port_type(self, monkeypatch):
        monkeypatch.setenv("PORT", "not_a_number")
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_ttl_zero(self, monkeypatch):
        monkeypatch.setenv("FILE_TTL_SECONDS", "0")
        with pytest.raises(ValidationError):
            Settings()


class TestCFG03CryptoSettingsUntouched:
    """CFG-03: Existing crypto constants in config/settings.py remain separate and untouched."""

    def test_crypto_settings_importable(self):
        from config.settings import Settings as CryptoSettings
        assert CryptoSettings.MAX_FILE_SIZE == 500 * 1024 * 1024

    def test_crypto_constants_importable(self):
        from config.constants import CryptoConstants
        assert CryptoConstants.MAGIC_NUMBER == b'DOCENC'
        assert CryptoConstants.KDF_ITERATIONS == 600000
