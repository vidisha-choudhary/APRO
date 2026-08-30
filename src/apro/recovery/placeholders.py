"""Deterministic, AI-free placeholder boundaries for Phase 4."""

import uuid
from datetime import UTC, datetime

from apro.domain.enums import FailureCategory, RecoveryActionType
from apro.domain.models import ActionEvaluation, Diagnosis


class PlaceholderDiagnosisProvider:
    """Deterministic, local, AI-free diagnosis placeholder provider."""

    def get_diagnosis(self, case_id: str, now: datetime | None = None) -> Diagnosis:
        timestamp = now or datetime.now(UTC)
        return Diagnosis(
            diagnosis_id=str(uuid.uuid4()),
            case_id=case_id,
            category=FailureCategory.UNKNOWN,
            confidence=0.0,
            evidence=("PHASE4_PLACEHOLDER",),
            model_name="PHASE4_PLACEHOLDER",
            model_version="1.0",
            created_at=timestamp,
        )


class PlaceholderEvaluationProvider:
    """Deterministic, local, AI-free action evaluation placeholder provider."""

    def get_evaluation(
        self, case_id: str, now: datetime | None = None
    ) -> ActionEvaluation:
        timestamp = now or datetime.now(UTC)
        return ActionEvaluation(
            evaluation_id=str(uuid.uuid4()),
            case_id=case_id,
            action_type=RecoveryActionType.RETRY,
            success_probability=0.0,
            recoverable_amount=0,
            action_cost=0,
            expected_recovery_value=0,
            model_name="PHASE4_PLACEHOLDER",
            model_version="1.0",
            created_at=timestamp,
        )
