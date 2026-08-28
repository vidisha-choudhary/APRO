"""Centralized configuration manager for APRO using Pydantic Settings."""

import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("apro.config")


class Settings(BaseSettings):
    """Centralized configuration settings for the APRO application.

    Pydantic Settings automatically resolves values from environment variables
    and loads defaults or overrides from a local .env file.
    """

    # Application settings
    APP_ENV: str = Field(default="development")
    APP_HOST: str = Field(default="127.0.0.1")
    APP_PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")

    # Razorpay Webhook Configuration (Phase 01)
    RAZORPAY_WEBHOOK_SECRET: str | None = Field(default=None)

    # Database Configuration (Phase 2) - No default credential string
    DATABASE_URL: str | None = Field(default=None)

    # Settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Load and return the application configuration settings."""
    try:
        settings = Settings()
        logger.info(
            "Configuration loaded successfully. Environment: %s", settings.APP_ENV
        )
        return settings
    except Exception as e:
        logger.error("Configuration validation error: %s", e)
        raise e


# Instantiate a global settings object for convenience
settings: Settings = get_settings()
