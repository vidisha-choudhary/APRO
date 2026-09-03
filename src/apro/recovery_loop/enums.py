"""Enum definitions and schema versions for APRO Phase 13 Recovery Loop."""

from enum import StrEnum

RECOVERY_LOOP_SCHEMA_VERSION = "recovery-loop-schema-v1"
OUTCOME_PROCESSOR_VERSION = "outcome-processor-v1"
DISPOSITION_RESOLVER_VERSION = "disposition-resolver-v1"
RE_EVALUATION_CONTEXT_SCHEMA_VERSION = "re-evaluation-context-v1"


class RecoveryLoopDisposition(StrEnum):
    """Explicit disposition produced by the recovery loop after processing an
    outcome.
    """

    WAIT_FOR_OUTCOME = "WAIT_FOR_OUTCOME"
    RE_EVALUATE = "RE_EVALUATE"
    STOP = "STOP"
    ESCALATE = "ESCALATE"
    COMPLETE = "COMPLETE"


class EvidenceType(StrEnum):
    """Classification of the normalized evidence presented to the recovery loop."""

    PAYMENT_EVENT = "PAYMENT_EVENT"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    PROVIDER_EVIDENCE = "PROVIDER_EVIDENCE"
    SIMULATION_OUTCOME = "SIMULATION_OUTCOME"
    MANUAL_EVIDENCE = "MANUAL_EVIDENCE"


class LoopTerminationReason(StrEnum):
    """Reason for terminating or halting adaptive loop progression."""

    RECOVERY_CONFIRMED = "RECOVERY_CONFIRMED"
    ATTEMPT_LIMIT_EXCEEDED = "ATTEMPT_LIMIT_EXCEEDED"
    INTERVENTION_LIMIT_EXCEEDED = "INTERVENTION_LIMIT_EXCEEDED"
    SAME_ACTION_LIMIT_EXCEEDED = "SAME_ACTION_LIMIT_EXCEEDED"
    NO_ELIGIBLE_ACTIONS = "NO_ELIGIBLE_ACTIONS"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    PAYMENT_CAPTURED_RACE = "PAYMENT_CAPTURED_RACE"
    CASE_EXPIRED = "CASE_EXPIRED"
    HUMAN_ESCALATION_REQUIRED = "HUMAN_ESCALATION_REQUIRED"
    EXPLICIT_STOP = "EXPLICIT_STOP"
    UNRECOVERABLE_FAILURE = "UNRECOVERABLE_FAILURE"


class EvidenceProvenance(StrEnum):
    """Provenance tracking for outcome evidence."""

    RAZORPAY = "RAZORPAY"
    SIMULATOR = "SIMULATOR"
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"
