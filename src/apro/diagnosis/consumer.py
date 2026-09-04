"""Authoritative Phase 7 Failure Diagnosis consumption and audit boundary."""

from typing import Any

from apro.diagnosis.models import DiagnosisResult


class DiagnosisArtifactConsumer:
    """Authoritative consumer and bridge for Phase 7 normalized diagnosis artifacts.

    Observes and consumes Phase 7 failure diagnosis results and emits automatic
    audit events via AuditService at the authoritative Phase 7 boundary.
    """

    def __init__(self, audit_service: Any | None = None) -> None:
        self.audit_service = audit_service

    async def consume_diagnosis(
        self,
        diagnosis: DiagnosisResult | Any,
        case_id: str,
        cycle_number: int = 1,
        uow: Any | None = None,
    ) -> tuple[Any, Any | None]:
        """Consume an authoritative Phase 7 DiagnosisResult and emit an audit event."""
        audit_event = None
        if self.audit_service is not None:
            audit_event = await self.audit_service.record_diagnosis(
                diagnosis=diagnosis,
                case_id=case_id,
                cycle_number=cycle_number,
                uow=uow,
            )
        return diagnosis, audit_event
