"""Enumerations and taxonomy constants for APRO Phase 7 Failure Diagnosis."""

from enum import StrEnum


class DiagnosisCategory(StrEnum):
    """Normalized APRO failure diagnosis categories (Taxonomy v1)."""

    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    BANK_SIDE_FAILURE = "BANK_SIDE_FAILURE"
    CUSTOMER_SIDE_FAILURE = "CUSTOMER_SIDE_FAILURE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    PAYMENT_METHOD_FAILURE = "PAYMENT_METHOD_FAILURE"
    GATEWAY_FAILURE = "GATEWAY_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


DIAGNOSIS_TAXONOMY_ORDER: tuple[DiagnosisCategory, ...] = (
    DiagnosisCategory.TRANSIENT_FAILURE,
    DiagnosisCategory.BANK_SIDE_FAILURE,
    DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
    DiagnosisCategory.AUTHENTICATION_FAILURE,
    DiagnosisCategory.PAYMENT_METHOD_FAILURE,
    DiagnosisCategory.GATEWAY_FAILURE,
    DiagnosisCategory.TIMEOUT,
    DiagnosisCategory.UNKNOWN_FAILURE,
)

DIAGNOSIS_TAXONOMY_VERSION: str = "diagnosis-taxonomy-v1"


class UncertaintyState(StrEnum):
    """Calibrated confidence and uncertainty states for Model A diagnosis."""

    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ABSTAIN = "ABSTAIN"


class DiagnosisAlgorithmType(StrEnum):
    """Classification algorithm identifiers for Model A and baseline models."""

    MAJORITY_CLASS = "MAJORITY_CLASS"
    PROVIDER_RULES = "PROVIDER_RULES"
    HISTORICAL_CONDITIONAL = "HISTORICAL_CONDITIONAL"
    NAIVE_BAYES = "NAIVE_BAYES"
    MULTINOMIAL_LOGISTIC_REGRESSION = "MULTINOMIAL_LOGISTIC_REGRESSION"
    DECISION_TREE = "DECISION_TREE"
    RANDOM_FOREST = "RANDOM_FOREST"
