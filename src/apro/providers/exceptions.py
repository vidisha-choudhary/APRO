"""Provider exception hierarchy for APRO external adapters."""


class ProviderError(Exception):
    """Base exception for all external provider adapter operations."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is invalid or missing."""


class ProviderCredentialError(ProviderError):
    """Raised when credentials are invalid or production keys in test mode."""


class ProviderRequestValidationError(ProviderError):
    """Raised when request payload fails validation prior to dispatch."""


class UnsupportedProviderOperationError(ProviderError):
    """Raised when operation is unsupported by the provider transport."""


class ProviderAuthenticationError(ProviderError):
    """Raised when provider rejects authentication credentials (e.g. 401)."""


class ProviderAuthorizationError(ProviderError):
    """Raised when provider rejects access permissions (e.g. 403)."""


class ProviderRateLimitError(ProviderError):
    """Raised when provider responds with rate limit exceeded (e.g. 429)."""


class ProviderRejectedError(ProviderError):
    """Raised when provider definitively rejects an operation (e.g. 400)."""


class ProviderUnavailableError(ProviderError):
    """Raised when provider returns a server-side error (e.g. HTTP 500/502/503)."""


class ProviderTimeoutError(ProviderError):
    """Raised when network transport or read times out (ambiguous state)."""


class ProviderMalformedResponseError(ProviderError):
    """Raised when provider response cannot be parsed or violates schema."""


class ProviderAmbiguousResultError(ProviderError):
    """Raised when execution result cannot be definitively determined."""


__all__ = [
    "ProviderAmbiguousResultError",
    "ProviderAuthenticationError",
    "ProviderAuthorizationError",
    "ProviderConfigurationError",
    "ProviderCredentialError",
    "ProviderError",
    "ProviderMalformedResponseError",
    "ProviderRateLimitError",
    "ProviderRejectedError",
    "ProviderRequestValidationError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "UnsupportedProviderOperationError",
]
