"""Configuration schema and validation for Razorpay TEST mode."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apro.providers.exceptions import (
    ProviderConfigurationError,
    ProviderCredentialError,
)
from apro.providers.razorpay.security import mask_secret


class RazorpayTestModeConfig(BaseModel):
    """Immutable configuration for Razorpay TEST mode provider transport."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key_id: str = Field(description="Razorpay TEST Key ID (e.g. rzp_test_...)")
    key_secret: str = Field(description="Razorpay TEST Key Secret")
    base_url: str = Field(
        default="https://api.razorpay.com",
        description="Base URL for Razorpay API or local test stub",
    )
    timeout_seconds: float = Field(default=10.0, gt=0.0, le=60.0)
    max_transport_retries: int = Field(default=0, ge=0, le=3)
    environment: str = Field(default="test")

    @field_validator("key_id")
    @classmethod
    def validate_key_id(cls, v: str) -> str:
        if not v or not v.strip():
            msg = "Razorpay key_id cannot be empty."
            raise ProviderCredentialError(msg)
        cleaned = v.strip()
        if cleaned.startswith("rzp_live_") or "live" in cleaned.lower():
            msg = (
                f"Production credentials ('{cleaned[:8]}...') are prohibited in "
                "RazorpayTestModeConfig. Only TEST credentials allowed."
            )
            raise ProviderCredentialError(msg)
        if not cleaned.startswith("rzp_test_"):
            msg = (
                f"Invalid key_id '{cleaned[:12]}...'. Razorpay TEST keys must start "
                "with 'rzp_test_'."
            )
            raise ProviderCredentialError(msg)
        return cleaned

    @field_validator("key_secret")
    @classmethod
    def validate_key_secret(cls, v: str) -> str:
        if not v or not v.strip():
            msg = "Razorpay key_secret cannot be empty."
            raise ProviderCredentialError(msg)
        cleaned = v.strip()
        if len(cleaned) < 4:
            msg = "Razorpay key_secret is too short to be valid."
            raise ProviderCredentialError(msg)
        return cleaned

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v.lower() not in ("test", "test_mode", "simulation_stub"):
            msg = (
                f"Invalid environment '{v}'. Only 'test' or 'test_mode' "
                "is supported in Phase 12."
            )
            raise ProviderConfigurationError(msg)
        return v.lower()

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            msg = f"base_url must start with http:// or https://, got '{v}'"
            raise ProviderConfigurationError(msg)

        host = (parsed.hostname or "").lower()
        allowed_exact_hosts = {
            "api.razorpay.com",
            "localhost",
            "127.0.0.1",
            "testserver",
            "mock",
        }
        if host not in allowed_exact_hosts:
            msg = (
                f"Untrusted or invalid base_url host '{host}'. "
                "Real TEST mode only accepts 'api.razorpay.com' "
                "or local/injected test stub hosts "
                "(localhost, 127.0.0.1, testserver, mock)."
            )
            raise ProviderConfigurationError(msg)

        return v.rstrip("/")

    def get_secret_set(self) -> set[str]:
        """Return raw secret strings that must be redacted from outputs."""
        return {self.key_secret}

    def __repr__(self) -> str:
        return (
            f"RazorpayTestModeConfig("
            f"key_id='{self.key_id}', "
            f"key_secret='{mask_secret(self.key_secret)}', "
            f"base_url='{self.base_url}', "
            f"timeout_seconds={self.timeout_seconds}, "
            f"environment='{self.environment}')"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Dump model with key_secret masked by default for safety."""
        data = super().model_dump(*args, **kwargs)
        if "key_secret" in data:
            data["key_secret"] = mask_secret(self.key_secret)
        return data


__all__ = ["RazorpayTestModeConfig"]
