"""Error taxonomy mapping for Razorpay TEST mode responses."""

import json

from apro.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRejectedError,
    ProviderRequestValidationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from apro.providers.razorpay.models import RazorpayErrorResponse
from apro.providers.razorpay.security import sanitize_text


def parse_razorpay_error(
    status_code: int,
    raw_content: str | bytes,
    known_secrets: set[str] | None = None,
) -> tuple[str, str, str | None]:
    """Extract code, description, and reason from Razorpay error payload safely."""
    code = f"HTTP_{status_code}"
    description = f"HTTP status {status_code} returned by Razorpay API"
    reason = None

    if isinstance(raw_content, bytes):
        text_content = raw_content.decode("utf-8", errors="replace")
    else:
        text_content = str(raw_content)

    clean_text = sanitize_text(text_content, known_secrets)

    try:
        data = json.loads(clean_text)
        if isinstance(data, dict) and "error" in data:
            err_obj = RazorpayErrorResponse(**data).error
            code = err_obj.code
            description = err_obj.description
            reason = err_obj.reason
    except Exception:
        description = clean_text[:200] if clean_text else description

    return code, description, reason


def classify_razorpay_error(
    status_code: int,
    raw_content: str | bytes,
    known_secrets: set[str] | None = None,
) -> ProviderError:
    """Classify an HTTP error response from Razorpay into provider hierarchy."""
    code, description, reason = parse_razorpay_error(
        status_code, raw_content, known_secrets
    )
    detail_msg = f"Razorpay error [{code}]: {description}"
    if reason:
        detail_msg += f" (reason: {reason})"

    if status_code == 400:
        if "validation" in code.lower() or "invalid" in code.lower():
            return ProviderRequestValidationError(detail_msg)
        return ProviderRejectedError(detail_msg)
    if status_code == 401:
        return ProviderAuthenticationError(detail_msg)
    if status_code == 403:
        return ProviderAuthorizationError(detail_msg)
    if status_code == 429:
        return ProviderRateLimitError(detail_msg)
    if status_code in (500, 502, 503):
        return ProviderUnavailableError(detail_msg)
    if status_code == 504:
        return ProviderTimeoutError(detail_msg)

    if status_code >= 500:
        return ProviderUnavailableError(detail_msg)

    return ProviderRejectedError(detail_msg)


__all__ = [
    "classify_razorpay_error",
    "parse_razorpay_error",
]
