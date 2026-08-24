import pytest
from pydantic import ValidationError

from apro.config import Settings


def test_settings_default_values() -> None:
    """Test that configuration defaults are correctly initialized."""
    settings = Settings()
    assert settings.APP_ENV == "development"
    assert settings.APP_HOST == "127.0.0.1"
    assert settings.APP_PORT == 8000
    assert settings.LOG_LEVEL == "INFO"


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables override configuration defaults."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()
    assert settings.APP_ENV == "production"
    assert settings.APP_PORT == 9000
    assert settings.LOG_LEVEL == "DEBUG"


def test_settings_validation_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that invalid types for config fields trigger ValidationError."""
    monkeypatch.setenv("APP_PORT", "not-an-integer")
    with pytest.raises(ValidationError):
        Settings()
