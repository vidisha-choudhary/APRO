"""APRO External Provider Adapters package."""

from apro.providers.exceptions import (
    ProviderAmbiguousResultError,
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderConfigurationError,
    ProviderCredentialError,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderRateLimitError,
    ProviderRejectedError,
    ProviderRequestValidationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnsupportedProviderOperationError,
)

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
