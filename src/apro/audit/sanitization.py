"""Centralized telemetry sanitization boundary for Phase 14."""

import re
from collections.abc import Mapping, Sequence
from typing import Any

# Sensitive key patterns to redact completely (case-insensitive)
SENSITIVE_KEY_SUBSTRINGS = (
    "authorization",
    "auth",
    "api_key",
    "key_id",
    "key_secret",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "database_url",
    "connection_string",
    "secret",
    "credential",
    "cookie",
    "card_number",
    "cvv",
    "pan",
    "pin",
    "signature",
    "private_key",
    "rzp_test_secret",
    "rzp_live_secret",
)

# Simulator latent truth fields to strip from telemetry
SIMULATOR_LATENT_KEYS = (
    "potential_outcomes",
    "oracle_action",
    "hidden_recoverability",
    "latent",
    "oracle",
)

SECRET_PATTERNS = [
    re.compile(r"sentinel_phase14_secret_[a-zA-Z0-9_]+", re.IGNORECASE),
    re.compile(r"sentinel_[a-zA-Z0-9_]+_secret_[a-zA-Z0-9_]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]+", re.IGNORECASE),
    re.compile(r"Basic\s+[a-zA-Z0-9=+/]+", re.IGNORECASE),
    re.compile(r"postgresql(\+[a-z0-9]+)?://[^:]+:([^@]+)@", re.IGNORECASE),
    re.compile(
        r"(?:secret|password|api_key|key_secret|token)\s*[:=]\s*[^\s,;)]+",
        re.IGNORECASE,
    ),
    re.compile(r"rzp_(?:test|live)_[a-zA-Z0-9_]+", re.IGNORECASE),
]

# PII Patterns
EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b")
PHONE_PATTERN = re.compile(
    r"\b(\+?[0-9]{1,3}[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
)

REDACTED_VALUE = "[REDACTED]"


class TelemetrySanitizer:
    """Centralized sanitization for logs, audit payloads, exceptions, and traces."""

    @classmethod
    def sanitize(cls, data: Any, max_depth: int = 10) -> Any:
        """Recursively sanitize any Python data structure."""
        if max_depth <= 0:
            return "[TRUNCATED_DEPTH]"

        if data is None:
            return None

        if isinstance(data, (bool, int, float)):
            return data

        if isinstance(data, str):
            return cls.sanitize_string(data)

        if isinstance(data, Mapping):
            sanitized_dict: dict[str, Any] = {}
            for key, val in data.items():
                str_key = str(key)
                lower_key = str_key.lower()

                # Check if key is a simulator latent field
                if any(latent in lower_key for latent in SIMULATOR_LATENT_KEYS):
                    continue

                # Check if key is sensitive
                if any(sens in lower_key for sens in SENSITIVE_KEY_SUBSTRINGS):
                    sanitized_dict[str_key] = REDACTED_VALUE
                else:
                    sanitized_dict[str_key] = cls.sanitize(val, max_depth - 1)
            return sanitized_dict

        if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
            return [cls.sanitize(item, max_depth - 1) for item in data]

        if isinstance(data, (set, frozenset)):
            return [
                cls.sanitize(item, max_depth - 1)
                for item in sorted(str(x) for x in data)
            ]

        if isinstance(data, BaseException):
            return cls.sanitize_exception(data)

        if hasattr(data, "model_dump") and callable(data.model_dump):
            return cls.sanitize(data.model_dump(), max_depth - 1)

        if hasattr(data, "__dict__"):
            return cls.sanitize(vars(data), max_depth - 1)

        return cls.sanitize_string(str(data))

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Sanitize strings for embedded secrets, credentials, tokens, and PII."""
        if not text:
            return text

        result = text
        for pattern in SECRET_PATTERNS:
            result = pattern.sub(REDACTED_VALUE, result)

        # Mask email: u***@domain.com
        def mask_email(match: re.Match[str]) -> str:
            user, domain = match.group(1), match.group(2)
            masked_user = user[0] + "***" if len(user) > 0 else "***"
            return f"{masked_user}@{domain}"

        result = EMAIL_PATTERN.sub(mask_email, result)

        # Mask phone numbers: ***-***-1234
        def mask_phone(match: re.Match[str]) -> str:
            raw = match.group(0)
            return "***-***-" + raw[-4:] if len(raw) >= 4 else "[REDACTED_PHONE]"

        return PHONE_PATTERN.sub(mask_phone, result)

    @classmethod
    def sanitize_exception(cls, exc: BaseException) -> dict[str, Any]:
        """Produce safe structured exception telemetry."""
        return {
            "exception_type": exc.__class__.__name__,
            "message": cls.sanitize_string(str(exc)),
            "details": cls.sanitize_string(repr(exc)),
        }


def sanitize_telemetry(data: Any) -> Any:
    """Convenience functional interface for telemetry sanitization."""
    return TelemetrySanitizer.sanitize(data)
