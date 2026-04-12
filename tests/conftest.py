"""
Shared fixtures for all Phase 1 tests.
"""
import pytest
from app.config import get_settings


@pytest.fixture(autouse=False)
def clear_settings_cache():
    """Clear the lru_cache on get_settings before and after each test that needs it."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
