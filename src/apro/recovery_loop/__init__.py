"""APRO Phase 13 — Outcome & Adaptive Recovery Loop package."""

from apro.recovery_loop.context import (
    ReEvaluationContextBuilder,
    compute_re_evaluation_id,
)
from apro.recovery_loop.controller import RecoveryLoopController
from apro.recovery_loop.dispositions import DispositionResolver
from apro.recovery_loop.enums import (
    DISPOSITION_RESOLVER_VERSION,
    OUTCOME_PROCESSOR_VERSION,
    RE_EVALUATION_CONTEXT_SCHEMA_VERSION,
    RECOVERY_LOOP_SCHEMA_VERSION,
    EvidenceProvenance,
    EvidenceType,
    LoopTerminationReason,
    RecoveryLoopDisposition,
)
from apro.recovery_loop.exceptions import (
    CaptureRaceDetectedError,
    EntityMismatchError,
    IdempotentOutcomeDuplicateError,
    InvalidOutcomeEvidenceError,
    RecoveryLoopError,
    StalePolicyDecisionError,
    TerminalCaseReopenError,
    UnboundedLoopError,
)
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.history import ActionHistoryService
from apro.recovery_loop.models import (
    ActionHistoryRecord,
    AdaptiveCycleResult,
    OutcomeEvidence,
    OutcomeProcessingResult,
    ReEvaluationContext,
)
from apro.recovery_loop.outcomes import OutcomeProcessor, compute_outcome_id

__all__ = [
    "DISPOSITION_RESOLVER_VERSION",
    "OUTCOME_PROCESSOR_VERSION",
    "RE_EVALUATION_CONTEXT_SCHEMA_VERSION",
    "RECOVERY_LOOP_SCHEMA_VERSION",
    "ActionHistoryRecord",
    "ActionHistoryService",
    "AdaptiveCycleResult",
    "CaptureRaceDetectedError",
    "DispositionResolver",
    "EntityMismatchError",
    "EvidenceProvenance",
    "EvidenceType",
    "IdempotentOutcomeDuplicateError",
    "InvalidOutcomeEvidenceError",
    "LoopSafetyGuard",
    "LoopTerminationReason",
    "OutcomeEvidence",
    "OutcomeProcessingResult",
    "OutcomeProcessor",
    "ReEvaluationContext",
    "ReEvaluationContextBuilder",
    "RecoveryLoopController",
    "RecoveryLoopDisposition",
    "RecoveryLoopError",
    "StalePolicyDecisionError",
    "TerminalCaseReopenError",
    "UnboundedLoopError",
    "compute_outcome_id",
    "compute_re_evaluation_id",
]
