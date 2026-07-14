import os
import pytest
from src.config import get_settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    # Force default settings for testing
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "changeme"
    
    # Clear the lru_cache for settings to ensure they reload with test env vars
    get_settings.cache_clear()
