"""Authoritative Phase 8 Recovery Outcome Prediction consumption and audit boundary."""

from typing import Any

from apro.recovery_prediction.enums import RecoveryAction
from apro.recovery_prediction.models import OutcomePrediction


class PredictionArtifactConsumer:
    """Authoritative consumer and bridge for Phase 8 outcome prediction artifacts.

    Observes and consumes Phase 8 outcome predictions for candidate recovery actions
    and emits automatic audit events via AuditService at the authoritative Phase 8
    boundary.
    """

    def __init__(self, audit_service: Any | None = None) -> None:
        self.audit_service = audit_service

    async def consume_predictions(
        self,
        predictions: list[OutcomePrediction]
        | dict[RecoveryAction, OutcomePrediction]
        | Any,
        case_id: str,
        cycle_number: int = 1,
        uow: Any | None = None,
    ) -> tuple[Any, Any | None]:
        """Consume authoritative Phase 8 predictions and emit an audit event."""
        preds_list = (
            list(predictions.values())
            if isinstance(predictions, dict)
            else (predictions if isinstance(predictions, list) else [predictions])
        )
        audit_event = None
        if self.audit_service is not None and preds_list:
            audit_event = await self.audit_service.record_predictions(
                predictions=preds_list,
                case_id=case_id,
                cycle_number=cycle_number,
                uow=uow,
            )
        return predictions, audit_event
