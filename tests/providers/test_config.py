"""Tests for Razorpay TEST mode configuration validation and security."""

import pytest
from pydantic import ValidationError

from apro.providers.exceptions import (
    ProviderConfigurationError,
    ProviderCredentialError,
)
from apro.providers.razorpay.config import RazorpayTestModeConfig


def test_valid_test_configuration() -> None:
    """Verify valid test credentials pass configuration validation."""
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_1234567890abcdef",
        key_secret="secret_test_xyz123456",
        base_url="https://api.razorpay.com",
        timeout_seconds=5.0,
    )
    assert cfg.key_id == "rzp_test_1234567890abcdef"
    assert cfg.key_secret == "secret_test_xyz123456"
    assert cfg.timeout_seconds == 5.0
    assert cfg.environment == "test"


def test_production_live_key_rejected() -> None:
    """Verify production key (rzp_live_) is rejected with ProviderCredentialError."""
    with pytest.raises((ProviderCredentialError, ValidationError)):
        RazorpayTestModeConfig(
            key_id="rzp_live_1234567890abcdef",
            key_secret="live_secret_xyz123456",
        )


def test_non_rzp_test_prefix_rejected() -> None:
    """Verify non-rzp_test_ keys (e.g. test_12345, key_12345) are rejected."""
    invalid_keys = [
        "test_12345",
        "key_12345",
        "rzp_12345",
        "stripe_test_12345",
        "invalid_key_prefix",
    ]
    for k in invalid_keys:
        with pytest.raises((ProviderCredentialError, ValidationError)) as exc_info:
            RazorpayTestModeConfig(
                key_id=k,
                key_secret="valid_secret_123",
            )
        assert "must start with 'rzp_test_'" in str(exc_info.value)


def test_empty_credentials_rejected() -> None:
    """Verify empty key_id or key_secret is rejected."""
    with pytest.raises((ProviderCredentialError, ValidationError)):
        RazorpayTestModeConfig(
            key_id="",
            key_secret="valid_secret_123",
        )
    with pytest.raises((ProviderCredentialError, ValidationError)):
        RazorpayTestModeConfig(
            key_id="rzp_test_12345",
            key_secret="",
        )


def test_invalid_environment_rejected() -> None:
    """Verify non-test environment names are rejected."""
    with pytest.raises((ProviderConfigurationError, ValidationError)):
        RazorpayTestModeConfig(
            key_id="rzp_test_12345",
            key_secret="secret_12345",
            environment="production",
        )


def test_invalid_base_url_rejected() -> None:
    """Verify invalid base_url without http(s) schema is rejected."""
    with pytest.raises((ProviderConfigurationError, ValidationError)):
        RazorpayTestModeConfig(
            key_id="rzp_test_12345",
            key_secret="secret_12345",
            base_url="ftp://api.razorpay.com",
        )


def test_malicious_domain_urls_rejected() -> None:
    """Verify malicious suffix, prefix, and untrusted domains are rejected."""
    malicious_urls = [
        "https://api.razorpay.com.evil.com",
        "http://localhost.evil.com",
        "https://evil-api.razorpay.com",
        "https://api.razorpay.com.attacker.org/v1",
        "https://127.0.0.1.attacker.org",
        "https://evil.razorpay.com",
    ]
    for url in malicious_urls:
        with pytest.raises((ProviderConfigurationError, ValidationError)):
            RazorpayTestModeConfig(
                key_id="rzp_test_12345",
                key_secret="secret_12345",
                base_url=url,
            )


def test_secret_masking_in_repr_and_dump() -> None:
    """Verify secret is masked in repr, str, and model_dump()."""
    raw_secret = "super_secret_test_key_999"
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_12345",
        key_secret=raw_secret,
    )
    repr_str = repr(cfg)
    assert raw_secret not in repr_str
    assert "[REDACTED]" in repr_str

    dump_dict = cfg.model_dump()
    assert dump_dict["key_secret"] != raw_secret
    assert "[REDACTED]" in dump_dict["key_secret"]
