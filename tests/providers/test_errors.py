"""Tests for Razorpay error classification and taxonomy."""

import json

from apro.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderRateLimitError,
    ProviderRejectedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from apro.providers.razorpay.errors import classify_razorpay_error, parse_razorpay_error


def test_parse_razorpay_structured_error() -> None:
    """Verify extracting error details from Razorpay JSON payload."""
    payload = json.dumps(
        {
            "error": {
                "code": "BAD_REQUEST_ERROR",
                "description": "Invalid phone number format",
                "source": "customer",
                "step": "validation",
                "reason": "invalid_phone",
            }
        }
    )
    code, desc, reason = parse_razorpay_error(400, payload)
    assert code == "BAD_REQUEST_ERROR"
    assert "Invalid phone number" in desc
    assert reason == "invalid_phone"


def test_classify_razorpay_400_rejection() -> None:
    """Verify HTTP 400 maps to ProviderRejectedError."""
    err = classify_razorpay_error(
        400, b'{"error":{"code":"BAD_REQUEST_ERROR","description":"bad"}}'
    )
    assert isinstance(err, ProviderRejectedError)


def test_classify_razorpay_401_authentication_error() -> None:
    """Verify HTTP 401 maps to ProviderAuthenticationError."""
    err = classify_razorpay_error(
        401, b'{"error":{"code":"BAD_REQUEST_ERROR","description":"auth failed"}}'
    )
    assert isinstance(err, ProviderAuthenticationError)


def test_classify_razorpay_403_authorization_error() -> None:
    """Verify HTTP 403 maps to ProviderAuthorizationError."""
    err = classify_razorpay_error(
        403, b'{"error":{"code":"FORBIDDEN","description":"forbidden"}}'
    )
    assert isinstance(err, ProviderAuthorizationError)


def test_classify_razorpay_429_rate_limit() -> None:
    """Verify HTTP 429 maps to ProviderRateLimitError."""
    err = classify_razorpay_error(
        429, b'{"error":{"code":"RATE_LIMIT_EXCEEDED","description":"slow down"}}'
    )
    assert isinstance(err, ProviderRateLimitError)


def test_classify_razorpay_500_unavailable() -> None:
    """Verify HTTP 500/502/503 maps to ProviderUnavailableError."""
    err = classify_razorpay_error(
        500, b'{"error":{"code":"GATEWAY_ERROR","description":"server error"}}'
    )
    assert isinstance(err, ProviderUnavailableError)


def test_classify_razorpay_504_timeout() -> None:
    """Verify HTTP 504 maps to ProviderTimeoutError."""
    err = classify_razorpay_error(504, b"Gateway Timeout")
    assert isinstance(err, ProviderTimeoutError)
