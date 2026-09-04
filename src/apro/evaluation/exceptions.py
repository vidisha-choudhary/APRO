"""Exceptions for APRO Phase 15 evaluation."""

from apro.evaluation.enums import EvaluationFailureCategory


class EvaluationError(Exception):
    """Base exception for all evaluation subsystem errors."""

    def __init__(
        self,
        message: str,
        category: EvaluationFailureCategory = (
            EvaluationFailureCategory.REPORT_GENERATION_ERROR
        ),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category


class DatasetInvalidError(EvaluationError):
    """Raised when a benchmark dataset snapshot is corrupted, empty, or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.DATASET_INVALID)


class InsufficientSampleError(EvaluationError):
    """Raised when the sample size is too small for statistical evaluation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.INSUFFICIENT_SAMPLE)


class MissingArtifactError(EvaluationError):
    """Raised when required canonical lifecycle artifacts are missing from a case."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.MISSING_ARTIFACT)


class StatisticalComputationError(EvaluationError):
    """Raised when a numerical or statistical computation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message, EvaluationFailureCategory.STATISTICAL_COMPUTATION_ERROR
        )


class ReportGenerationError(EvaluationError):
    """Raised when report compilation or formatting fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.REPORT_GENERATION_ERROR)


class EvaluationPersistenceError(EvaluationError):
    """Raised when saving or loading evaluation artifacts fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.PERSISTENCE_ERROR)


class SafetyInvariantViolationError(EvaluationError):
    """Raised when a benchmark detects a safety invariant violation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.SAFETY_INVARIANT_VIOLATION)


class CheatingViolationError(EvaluationError):
    """Raised when offline oracle/evaluation truth leaks into runtime inputs."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EvaluationFailureCategory.CHEATING_VIOLATION)
