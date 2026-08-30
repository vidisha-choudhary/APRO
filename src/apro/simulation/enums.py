"""Simulation vocabularies and enums for APRO Phase 5."""

from enum import StrEnum


class ScenarioFamily(StrEnum):
    """Scenario family classification taxonomy."""

    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    BANK_SIDE_FAILURE = "BANK_SIDE_FAILURE"
    CUSTOMER_SIDE_FAILURE = "CUSTOMER_SIDE_FAILURE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    PAYMENT_METHOD_FAILURE = "PAYMENT_METHOD_FAILURE"
    GATEWAY_FAILURE = "GATEWAY_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class RecoverabilityClass(StrEnum):
    """Hidden ground-truth recoverability tier."""

    HIGHLY_RECOVERABLE = "HIGHLY_RECOVERABLE"
    MODERATELY_RECOVERABLE = "MODERATELY_RECOVERABLE"
    LOW_RECOVERABILITY = "LOW_RECOVERABILITY"
    NON_RECOVERABLE = "NON_RECOVERABLE"


class CustomerBehaviorClass(StrEnum):
    """Hidden customer responsiveness and behavior classification."""

    HIGHLY_RESPONSIVE = "HIGHLY_RESPONSIVE"
    NORMAL = "NORMAL"
    LOW_RESPONSIVENESS = "LOW_RESPONSIVENESS"
    UNPREDICTABLE = "UNPREDICTABLE"


class PaymentValueTier(StrEnum):
    """Payment transaction value tier."""

    LOW_VALUE = "LOW_VALUE"
    MEDIUM_VALUE = "MEDIUM_VALUE"
    HIGH_VALUE = "HIGH_VALUE"


class SimulatedPaymentMethod(StrEnum):
    """Supported payment methods for simulation."""

    CARD = "CARD"
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    OTHER_SUPPORTED_METHOD = "OTHER_SUPPORTED_METHOD"


class ScenarioDifficulty(StrEnum):
    """Scenario difficulty and ambiguity rating."""

    EASY = "EASY"
    AMBIGUOUS = "AMBIGUOUS"
    HARD = "HARD"
    ADVERSARIAL = "ADVERSARIAL"


class SimulatedActionType(StrEnum):
    """Candidate recovery actions for simulation."""

    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    OUTREACH = "OUTREACH"
    STOP = "STOP"
    ESCALATE = "ESCALATE"


class SimulatedOutcomeStatus(StrEnum):
    """Simulated outcome status vocabulary."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
