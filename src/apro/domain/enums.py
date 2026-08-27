"""Domain vocabularies and enums for APRO."""

from enum import StrEnum


class PaymentStatus(StrEnum):
    """Initial payment status vocabulary."""

    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class RecoveryCaseStatus(StrEnum):
    """RecoveryCase state vocabulary."""

    NEW = "NEW"
    DIAGNOSING = "DIAGNOSING"
    EVALUATING = "EVALUATING"
    DECISION_PENDING = "DECISION_PENDING"
    POLICY_CHECK = "POLICY_CHECK"
    ACTION_APPROVED = "ACTION_APPROVED"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    RECOVERED = "RECOVERED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"


class RecoveryActionType(StrEnum):
    """RecoveryAction type vocabulary."""

    RETRY = "RETRY"
    ALTERNATE_RECOVERY = "ALTERNATE_RECOVERY"
    OUTREACH = "OUTREACH"
    ESCALATE = "ESCALATE"
    STOP = "STOP"


class RecoveryActionStatus(StrEnum):
    """RecoveryAction status vocabulary."""

    CANDIDATE = "CANDIDATE"
    RECOMMENDED = "RECOMMENDED"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PolicyDecisionResult(StrEnum):
    """PolicyDecision outcome result vocabulary."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"


class ExecutionStatus(StrEnum):
    """Execution status vocabulary."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class ExecutionMode(StrEnum):
    """Execution environment mode vocabulary."""

    RAZORPAY_TEST_MODE = "RAZORPAY_TEST_MODE"
    SIMULATION = "SIMULATION"
    INTERNAL = "INTERNAL"


class OutcomeType(StrEnum):
    """Observed outcome type vocabulary."""

    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"


class AuditActor(StrEnum):
    """Audit actor vocabulary."""

    SYSTEM = "SYSTEM"
    MODEL = "MODEL"
    POLICY = "POLICY"
    EXECUTOR = "EXECUTOR"
    HUMAN = "HUMAN"
    RAZORPAY = "RAZORPAY"
    SIMULATOR = "SIMULATOR"


class FailureCategory(StrEnum):
    """Failure diagnosis taxonomy vocabulary."""

    TRANSIENT = "TRANSIENT"
    BANK_SIDE = "BANK_SIDE"
    CUSTOMER_SIDE = "CUSTOMER_SIDE"
    AUTHENTICATION = "AUTHENTICATION"
    PAYMENT_METHOD = "PAYMENT_METHOD"
    GATEWAY = "GATEWAY"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"
