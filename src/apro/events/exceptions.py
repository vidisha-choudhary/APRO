"""Exceptions for APRO Phase 3 Canonical Event Pipeline."""

from apro.domain.exceptions import DomainException


class EventPipelineError(DomainException):
    """Base exception for event pipeline processing failures."""


class InvalidSignatureError(EventPipelineError):
    """Raised when HMAC signature verification fails."""


class MalformedPayloadError(EventPipelineError):
    """Raised when incoming webhook payload is malformed or invalid."""


class DuplicateEventError(EventPipelineError):
    """Raised when duplicate provider event ID is detected."""


class UnresolvedPaymentError(EventPipelineError):
    """Raised when provider payment ID cannot be mapped to APRO internal payment."""


class UnsupportedEventError(EventPipelineError):
    """Raised when authenticated webhook event type is not supported."""
