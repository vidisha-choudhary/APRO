"""Tests proving production/live mode is unavailable and rejected."""

import pytest
from pydantic import ValidationError

from apro.execution.exceptions import ExecutorNotFoundError
from apro.execution.registry import DEFAULT_EXECUTOR_REGISTRY
from apro.providers.exceptions import ProviderCredentialError
from apro.providers.razorpay.config import RazorpayTestModeConfig


def test_production_credentials_strictly_rejected() -> None:
    """Verify live credentials fail closed at configuration validation."""
    with pytest.raises((ProviderCredentialError, ValidationError)):
        RazorpayTestModeConfig(
            key_id="rzp_live_production_key_123",
            key_secret="live_secret_456",
        )


def test_no_production_mode_in_default_registry() -> None:
    """Verify default registry contains no production/live modes."""
    registered = DEFAULT_EXECUTOR_REGISTRY.list_registered()
    for entry in registered:
        assert "LIVE" not in entry["mode"].upper()
        assert "PROD" not in entry["mode"].upper()


def test_unregistered_mode_fails_closed() -> None:
    """Verify querying an unsupported mode raises ExecutorNotFoundError."""
    with pytest.raises(ExecutorNotFoundError):
        DEFAULT_EXECUTOR_REGISTRY.get("RETRY", "RAZORPAY_LIVE_MODE")
