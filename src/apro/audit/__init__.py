"""Phase 14 — Audit & Observability Module Public API."""

from apro.audit.correlation import (
    CorrelationContext,
    async_correlation_scope,
    clear_correlation_context,
    correlation_scope,
    generate_trace_id,
    get_correlation_context,
    reset_correlation_context,
    set_correlation_context,
)
from apro.audit.enums import (
    AUDIT_SCHEMA_VERSION,
    TRACE_SCHEMA_VERSION,
    AuditCompleteness,
    AuditComponent,
    AuditEventType,
    AuditLogLevel,
)
from apro.audit.exceptions import (
    AuditCorrelationError,
    AuditError,
    AuditImmutabilityError,
    AuditIntegrityError,
    AuditNotFoundError,
    AuditPersistenceError,
    AuditSecurityError,
)
from apro.audit.integrity import AuditIntegrityChecker
from apro.audit.logging import (
    LogCaptureHandler,
    StructuredJSONFormatter,
    StructuredLogger,
    get_structured_logger,
    get_telemetry_failure_count,
    reset_telemetry_failure_count,
)
from apro.audit.models import (
    CaseAuditTrace,
    CycleTraceRecord,
    DecisionTraceRecord,
    ExecutionTraceRecord,
    OutcomeTraceRecord,
    PolicyTraceRecord,
    StructuredLogEntry,
)
from apro.audit.reconstruction import CaseReconstructionService
from apro.audit.sanitization import TelemetrySanitizer, sanitize_telemetry
from apro.audit.service import AuditService, compute_audit_event_id
from apro.audit.tracing import (
    build_decision_trace,
    build_execution_trace,
    build_outcome_trace,
    build_policy_trace,
)

__all__ = [
    # Enums & Constants
    "AUDIT_SCHEMA_VERSION",
    "TRACE_SCHEMA_VERSION",
    "AuditCompleteness",
    "AuditComponent",
    "AuditEventType",
    "AuditLogLevel",
    # Exceptions
    "AuditError",
    "AuditPersistenceError",
    "AuditIntegrityError",
    "AuditNotFoundError",
    "AuditSecurityError",
    "AuditImmutabilityError",
    "AuditCorrelationError",
    # Sanitization
    "TelemetrySanitizer",
    "sanitize_telemetry",
    # Correlation
    "CorrelationContext",
    "get_correlation_context",
    "set_correlation_context",
    "reset_correlation_context",
    "clear_correlation_context",
    "correlation_scope",
    "async_correlation_scope",
    "generate_trace_id",
    # Logging
    "StructuredLogger",
    "StructuredJSONFormatter",
    "LogCaptureHandler",
    "get_structured_logger",
    "get_telemetry_failure_count",
    "reset_telemetry_failure_count",
    # Models
    "StructuredLogEntry",
    "DecisionTraceRecord",
    "PolicyTraceRecord",
    "ExecutionTraceRecord",
    "OutcomeTraceRecord",
    "CycleTraceRecord",
    "CaseAuditTrace",
    # Tracing
    "build_decision_trace",
    "build_policy_trace",
    "build_execution_trace",
    "build_outcome_trace",
    # Integrity
    "AuditIntegrityChecker",
    # Service & Reconstruction
    "AuditService",
    "compute_audit_event_id",
    "CaseReconstructionService",
]
