"""Tests for secret isolation, header scrubbing, and redaction verification."""

from apro.providers.razorpay.security import (
    mask_secret,
    sanitize_dict,
    sanitize_headers,
    sanitize_text,
)


def test_mask_secret_output() -> None:
    """Verify secret strings are securely masked."""
    assert mask_secret("short") == "[REDACTED]"
    masked = mask_secret("rzp_test_secret_123456789")
    assert "rzp_" in masked
    assert "89" in masked
    assert "secret" not in masked
    assert "[REDACTED]" in masked


def test_sanitize_dict_redacts_sensitive_keys() -> None:
    """Verify dictionary scrubber redacts sensitive field names."""
    data = {
        "user_id": "usr_123",
        "key_secret": "raw_secret_value",
        "authorization": "Basic abc123xyz",
        "nested": {
            "api_key": "raw_nested_api_key",
            "amount": 50000,
        },
    }
    cleaned = sanitize_dict(data)
    assert cleaned["user_id"] == "usr_123"
    assert cleaned["key_secret"] == "[REDACTED]"
    assert cleaned["authorization"] == "[REDACTED]"
    assert cleaned["nested"]["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["amount"] == 50000


def test_sanitize_headers_redacts_auth() -> None:
    """Verify header scrubber redacts authorization headers."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic cnpwX3Rlc3RfMTIzOnNlY3JldDEyMw==",
        "X-Custom-Header": "safe_value",
    }
    clean = sanitize_headers(headers)
    assert clean["Content-Type"] == "application/json"
    assert clean["Authorization"] == "[REDACTED]"
    assert clean["X-Custom-Header"] == "safe_value"


def test_sanitize_text_redacts_known_secrets() -> None:
    """Verify text scrubber removes known secret strings."""
    raw_secret = "super_confidential_secret_key_999"
    text = f"An error occurred with secret {raw_secret} during connection."
    clean = sanitize_text(text, {raw_secret})
    assert raw_secret not in clean
    assert "[REDACTED]" in clean
