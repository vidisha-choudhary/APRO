"""Domain exception hierarchy for Phase 14 Audit & Observability."""


class AuditError(Exception):
    """Base exception for all Phase 14 audit and observability errors."""


class AuditPersistenceError(AuditError):
    """Raised when durable audit event persistence fails."""


class AuditIntegrityError(AuditError):
    """Raised when an audit trace violates causal or referential integrity."""


class AuditNotFoundError(AuditError):
    """Raised when an audit record or reconstructed trace cannot be found."""


class AuditSecurityError(AuditError):
    """Raised when an unsafe condition is detected in telemetry."""


class AuditImmutabilityError(AuditError):
    """Raised when mutation is attempted on an immutable audit record."""


class AuditCorrelationError(AuditError):
    """Raised when correlation context propagation fails or is inconsistent."""
