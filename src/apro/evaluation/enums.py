"""Enumerations for APRO Phase 15 evaluation."""

from enum import StrEnum


class MetricSchemaVersion(StrEnum):
    """Supported metric schema versions."""

    V1_0 = "1.0.0"


class EvaluationConfigVersion(StrEnum):
    """Supported evaluation configuration versions."""

    V1_0 = "1.0.0"


class EvaluationCaseStatus(StrEnum):
    """Case accounting and eligibility classifications for benchmark cases."""

    ELIGIBLE = "ELIGIBLE"
    EXCLUDED = "EXCLUDED"
    MISSING_REQUIRED_ARTIFACT = "MISSING_REQUIRED_ARTIFACT"
    INVALID_CASE = "INVALID_CASE"
    DUPLICATE_CASE = "DUPLICATE_CASE"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"
    CENSORED = "CENSORED"


class TerminalDisposition(StrEnum):
    """Terminal disposition classifications for benchmark cases."""

    RECOVERED = "RECOVERED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"
    PENDING_WAITING = "PENDING_WAITING"
    UNKNOWN = "UNKNOWN"


class BaselineType(StrEnum):
    """Baseline strategy types for benchmark comparison."""

    NO_INTERVENTION = "NO_INTERVENTION"
    FIXED_RETRY = "FIXED_RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    FIXED_ESCALATION = "FIXED_ESCALATION"
    HISTORICAL_HUMAN = "HISTORICAL_HUMAN"
    RANDOM_ACTION = "RANDOM_ACTION"
    ORACLE_UPPER_BOUND = "ORACLE_UPPER_BOUND"


class EvaluationFailureCategory(StrEnum):
    """Explicit failure categories for evaluation errors."""

    DATASET_INVALID = "DATASET_INVALID"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    STATISTICAL_COMPUTATION_ERROR = "STATISTICAL_COMPUTATION_ERROR"
    REPORT_GENERATION_ERROR = "REPORT_GENERATION_ERROR"
    PERSISTENCE_ERROR = "PERSISTENCE_ERROR"
    SAFETY_INVARIANT_VIOLATION = "SAFETY_INVARIANT_VIOLATION"
    CHEATING_VIOLATION = "CHEATING_VIOLATION"


class MultipleComparisonPolicy(StrEnum):
    """Supported multiple hypothesis testing correction policies."""

    NONE = "NONE"
    HOLM = "HOLM"
    BONFERRONI = "BONFERRONI"
    BENJAMINI_HOCHBERG = "BENJAMINI_HOCHBERG"


class CensoringPolicy(StrEnum):
    """Handling policies for pending or right-censored cases."""

    EXCLUDE = "EXCLUDE"
    RIGHT_CENSOR = "RIGHT_CENSOR"
    ZERO_RECOVERY = "ZERO_RECOVERY"


class MissingDataPolicy(StrEnum):
    """Handling policies for missing artifacts."""

    EXCLUDE_CASE = "EXCLUDE_CASE"
    FLAG_INCOMPLETE = "FLAG_INCOMPLETE"
    IMPUTE_ZERO = "IMPUTE_ZERO"


class MetricComparisonLabel(StrEnum):
    """Label for metric comparison nature."""

    BENCHMARK_ASSOCIATION = "BENCHMARK_ASSOCIATION"
    RANDOMIZED_CAUSAL_EFFECT = "RANDOMIZED_CAUSAL_EFFECT"
