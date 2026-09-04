"""Tests for telemetry sanitization boundary and sensitive field redaction."""

from apro.audit.sanitization import (
    REDACTED_VALUE,
    TelemetrySanitizer,
    sanitize_telemetry,
)


def test_sanitize_nested_dictionary() -> None:
    """Sanitizer recursively redacts sensitive keys and removes latent truth."""
    raw_payload = {
        "case_id": "case_123",
        "api_key": "secret_key_999",
        "Authorization": "Bearer abc.def.ghi",
        "nested": {
            "password": "db_password_123",
            "card_number": "4111111111111111",
            "database_url": "postgresql://user:pass@localhost:5432/db",
            "safe_field": 42,
        },
        "potential_outcomes": {"oracle": True},
        "hidden_recoverability": 0.99,
        "oracle_action": "RETRY",
    }
    sanitized = sanitize_telemetry(raw_payload)

    assert sanitized["case_id"] == "case_123"
    assert sanitized["api_key"] == REDACTED_VALUE
    assert sanitized["Authorization"] == REDACTED_VALUE
    assert sanitized["nested"]["password"] == REDACTED_VALUE
    assert sanitized["nested"]["card_number"] == REDACTED_VALUE
    assert sanitized["nested"]["safe_field"] == 42
    # Latent truth keys removed
    assert "potential_outcomes" not in sanitized
    assert "hidden_recoverability" not in sanitized
    assert "oracle_action" not in sanitized


def test_sanitize_strings_and_sentinels() -> None:
    """Sanitizer redacts literal sentinel secrets and embedded tokens in strings."""
    secret_str = (
        "Error with sentinel_phase14_secret_87654321 occurred in Bearer my_token"
    )
    sanitized = TelemetrySanitizer.sanitize_string(secret_str)
    assert "sentinel_phase14_secret_87654321" not in sanitized
    assert "Bearer my_token" not in sanitized
    assert REDACTED_VALUE in sanitized


def test_sanitize_pii() -> None:
    """Sanitizer masks emails and phone numbers."""
    text = "Customer email john.doe@example.com and phone +1-555-123-4567"
    sanitized = TelemetrySanitizer.sanitize_string(text)
    assert "john.doe@example.com" not in sanitized
    assert "j***@example.com" in sanitized
    assert "***-***-4567" in sanitized


def test_sanitize_exception() -> None:
    """Sanitizer sanitizes exception objects and extracts structured telemetry."""
    exc = ValueError(
        "Database connection failed for postgresql://admin:secret123@127.0.0.1/db"
    )
    sanitized_exc = TelemetrySanitizer.sanitize_exception(exc)
    assert sanitized_exc["exception_type"] == "ValueError"
    assert "secret123" not in sanitized_exc["message"]
