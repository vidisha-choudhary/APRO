"""Security, credential redaction, and secret masking utilities for Razorpay."""

import re
from typing import Any

SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "authorization",
        "key_secret",
        "secret",
        "api_key",
        "apikey",
        "password",
        "token",
        "signature",
        "x_razorpay_signature",
        "client_secret",
    }
)


def mask_secret(value: str | None) -> str:
    """Mask a secret string preserving only minimal prefix for debugging."""
    if not value:
        return "[REDACTED]"
    if len(value) <= 8:
        return "[REDACTED]"
    return f"{value[:4]}...[REDACTED]...{value[-2:]}"


def sanitize_dict(
    data: dict[str, Any], known_secrets: set[str] | None = None
) -> dict[str, Any]:
    """Recursively sanitize dictionary by redacting sensitive keys and secrets."""
    sanitized: dict[str, Any] = {}
    known = known_secrets or set()

    for k, v in data.items():
        k_lower = k.lower().replace("-", "_")
        if k_lower in SENSITIVE_FIELD_NAMES:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v, known_secrets=known)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_dict(item, known_secrets=known)
                if isinstance(item, dict)
                else sanitize_text(str(item), known_secrets=known)
                if isinstance(item, str)
                else item
                for item in v
            ]
        elif isinstance(v, str):
            sanitized[k] = sanitize_text(v, known_secrets=known)
        else:
            sanitized[k] = v

    return sanitized


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Sanitize HTTP request/response headers."""
    clean: dict[str, str] = {}
    for k, v in headers.items():
        k_lower = k.lower().replace("-", "_")
        if k_lower in SENSITIVE_FIELD_NAMES or "auth" in k_lower:
            clean[k] = "[REDACTED]"
        else:
            clean[k] = v
    return clean


def sanitize_text(text: str, known_secrets: set[str] | None = None) -> str:
    """Scrub known secret values and authorization tokens from text."""
    if not text:
        return text

    scrubbed = text
    # Redact Basic auth headers or Bearer tokens
    scrubbed = re.sub(
        r"Basic\s+[A-Za-z0-9+/=]+", "Basic [REDACTED]", scrubbed, flags=re.IGNORECASE
    )
    scrubbed = re.sub(
        r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]", scrubbed, flags=re.IGNORECASE
    )

    # Redact known secrets if passed
    if known_secrets:
        for sec in known_secrets:
            if sec and len(sec) > 3 and sec in scrubbed:
                scrubbed = scrubbed.replace(sec, "[REDACTED]")

    return scrubbed


__all__ = [
    "SENSITIVE_FIELD_NAMES",
    "mask_secret",
    "sanitize_dict",
    "sanitize_headers",
    "sanitize_text",
]
