"""Audit service managing event emission, sanitization, and persistence for Phase 14."""

import uuid
from datetime import UTC, datetime
from typing import Any

from apro.audit.correlation import get_correlation_context
from apro.audit.enums import AuditEventType
from apro.audit.exceptions import AuditPersistenceError
from apro.audit.logging import get_structured_logger
from apro.audit.sanitization import TelemetrySanitizer
from apro.domain.enums import AuditActor, RecoveryCaseStatus
from apro.domain.models import (
    AuditEvent,
    Execution,
    Outcome,
    RecoveryCase,
)
from apro.persistence.unit_of_work import UnitOfWork

AUDIT_NAMESPACE = uuid.UUID("a7e8f0a1-2b3c-4d5e-6f7a-8b9c0d1e2f3a")


def compute_audit_event_id(
    case_id: str,
    event_type: str,
    source_id: str | None = None,
    sequence: int = 1,
) -> str:
    """Deterministically compute an audit event ID for deduplication."""
    src = source_id or "none"
    name = f"apro:audit:{case_id}:{event_type}:{src}:{sequence}"
    return str(uuid.uuid5(AUDIT_NAMESPACE, name))


class AuditService:
    """Core service for capturing and persisting authoritative audit events."""

    def __init__(self) -> None:
        self.logger = get_structured_logger("apro.audit.service")
        self._in_memory_events: list[AuditEvent] = []
        self._seen_event_ids: set[str] = set()

    def record_event_sync(
        self,
        case_id: str,
        event_type: AuditEventType | str,
        actor: AuditActor = AuditActor.SYSTEM,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        source_id: str | None = None,
        sequence: int = 1,
        uow: Any | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        """Synchronously record in-memory audit event and structured log."""
        now = timestamp or datetime.now(UTC)
        ev_type_str = (
            event_type.value if hasattr(event_type, "value") else str(event_type)
        )

        corr = get_correlation_context()
        resolved_trace_id = correlation_id or corr.trace_id or corr.case_id or case_id

        resolved_cycle = (
            corr.cycle_id if sequence == 1 and corr.cycle_id is not None else sequence
        )
        if isinstance(resolved_cycle, str):
            try:
                resolved_sequence = int(resolved_cycle)
            except ValueError:
                resolved_sequence = 1
        elif isinstance(resolved_cycle, int):
            resolved_sequence = resolved_cycle
        else:
            resolved_sequence = 1

        event_id = compute_audit_event_id(
            case_id=case_id,
            event_type=ev_type_str,
            source_id=source_id,
            sequence=resolved_sequence,
        )

        # Check duplicate delivery in-memory
        if event_id in self._seen_event_ids:
            for existing in self._in_memory_events:
                if existing.audit_event_id == event_id:
                    return existing

        sanitized_payload = TelemetrySanitizer.sanitize(payload or {})
        if "cycle_number" not in sanitized_payload and resolved_sequence:
            sanitized_payload["cycle_number"] = resolved_sequence

        audit_event = AuditEvent(
            audit_event_id=event_id,
            case_id=case_id,
            event_type=ev_type_str,
            actor=actor,
            timestamp=now,
            payload=sanitized_payload,
            correlation_id=resolved_trace_id,
        )

        # Attach to active UnitOfWork session if available
        from apro.persistence.unit_of_work import get_current_uow

        active_uow = uow or get_current_uow()
        session = (
            getattr(active_uow, "session", None) if active_uow is not None else None
        )
        if session is not None:
            try:
                from apro.persistence.mapper import audit_event_to_orm

                orm = audit_event_to_orm(audit_event)
                session.add(orm)
            except Exception as exc:
                self.logger.error(
                    "AUDIT_UOW_ATTACH_FAILED",
                    case_id=case_id,
                    entity_id=event_id,
                    metadata={"error": str(exc)},
                )
                raise AuditPersistenceError(
                    f"Failed to attach audit event to UnitOfWork session: {exc}"
                ) from exc

        self._in_memory_events.append(audit_event)
        self._seen_event_ids.add(event_id)

        # Emit operational log
        self.logger.info(
            event_name=ev_type_str,
            case_id=case_id,
            trace_id=resolved_trace_id,
            cycle_id=corr.cycle_id or resolved_sequence,
            entity_id=source_id or event_id,
            metadata=sanitized_payload,
        )

        return audit_event

    async def record_event(
        self,
        case_id: str,
        event_type: AuditEventType | str,
        actor: AuditActor = AuditActor.SYSTEM,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        source_id: str | None = None,
        sequence: int = 1,
        uow: UnitOfWork | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        """Record and persist an audit event with sanitization and deduplication."""
        audit_event = self.record_event_sync(
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            correlation_id=correlation_id,
            source_id=source_id,
            sequence=sequence,
            uow=uow,
            timestamp=timestamp,
        )

        # If uow was explicitly supplied, flush to ensure immediate availability
        if uow is not None and getattr(uow, "session", None) is not None:
            try:
                await uow.flush()
            except Exception as exc:
                self.logger.error(
                    "AUDIT_PERSISTENCE_FAILED",
                    case_id=case_id,
                    entity_id=audit_event.audit_event_id,
                    metadata={"error": str(exc)},
                )
                raise AuditPersistenceError(
                    f"Failed to persist audit event: {exc}"
                ) from exc

        return audit_event

    async def record_case_created(
        self,
        case: RecoveryCase,
        trigger_event_id: str | None = None,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record RECOVERY_CASE_CREATED event."""
        return await self.record_event(
            case_id=case.case_id,
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            payload={
                "payment_id": case.payment_id,
                "customer_id": case.customer_id,
                "initial_status": str(
                    case.status.value if hasattr(case.status, "value") else case.status
                ),
                "recovery_amount": case.recovery_amount,
                "trigger_event_id": trigger_event_id,
            },
            source_id=case.case_id,
            sequence=1,
            uow=uow,
        )

    async def record_case_state_changed(
        self,
        case_id: str,
        old_state: RecoveryCaseStatus | str,
        new_state: RecoveryCaseStatus | str,
        reason: str | None = None,
        sequence: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record CASE_STATE_CHANGED event."""
        return await self.record_event(
            case_id=case_id,
            event_type=AuditEventType.CASE_STATE_CHANGED,
            actor=AuditActor.SYSTEM,
            payload={
                "old_state": str(
                    old_state.value if hasattr(old_state, "value") else old_state
                ),
                "new_state": str(
                    new_state.value if hasattr(new_state, "value") else new_state
                ),
                "reason": reason,
            },
            source_id=f"{old_state}->{new_state}",
            sequence=sequence,
            uow=uow,
        )

    async def record_diagnosis(
        self,
        diagnosis: Any,
        case_id: str,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record DIAGNOSIS_CREATED event."""
        raw_cat = getattr(
            diagnosis,
            "category",
            getattr(diagnosis, "failure_category", "UNKNOWN"),
        )
        cat_str = raw_cat.value if hasattr(raw_cat, "value") else str(raw_cat)

        return await self.record_event(
            case_id=case_id,
            event_type=AuditEventType.DIAGNOSIS_CREATED,
            actor=AuditActor.MODEL,
            payload={
                "diagnosis_id": getattr(diagnosis, "diagnosis_id", ""),
                "failure_category": cat_str,
                "confidence": getattr(diagnosis, "confidence", 1.0),
                "model_name": getattr(diagnosis, "model_name", "diagnosis_engine"),
                "model_version": getattr(diagnosis, "model_version", "1.0.0"),
                "dataset_version": getattr(diagnosis, "dataset_version", "dataset-v1"),
                "cycle_number": cycle_number,
            },
            source_id=getattr(diagnosis, "diagnosis_id", f"diag_{cycle_number}"),
            sequence=cycle_number,
            uow=uow,
        )

    async def record_predictions(
        self,
        predictions: list[Any],
        case_id: str,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record PREDICTION_CREATED event."""
        preds_summary = []
        for p in predictions:
            raw_act = getattr(p, "action_type", getattr(p, "action", "UNKNOWN"))
            act_str = raw_act.value if hasattr(raw_act, "value") else str(raw_act)
            prob = getattr(
                p,
                "success_probability",
                getattr(p, "predicted_recovery_probability", 0.0),
            )
            erv = getattr(p, "expected_recovery_value", 0)
            ver = getattr(p, "model_version", "1.0.0")
            preds_summary.append(
                {
                    "action_type": act_str,
                    "predicted_recovery_probability": prob,
                    "expected_recovery_value": erv,
                    "model_version": ver,
                }
            )

        return await self.record_event(
            case_id=case_id,
            event_type=AuditEventType.PREDICTION_CREATED,
            actor=AuditActor.MODEL,
            payload={
                "predictions_count": len(predictions),
                "predictions": preds_summary,
                "cycle_number": cycle_number,
            },
            source_id=f"preds_{cycle_number}",
            sequence=cycle_number,
            uow=uow,
        )

    def record_decision_sync(
        self,
        decision: Any,
        candidate_actions: list[dict[str, Any]] | None = None,
        cycle_number: int = 1,
        uow: Any | None = None,
    ) -> AuditEvent:
        """Synchronously record DECISION_CREATED event."""
        meta = getattr(decision, "metadata", {}) or {}
        candidates = candidate_actions or meta.get("candidate_actions", [])
        raw_act = getattr(
            decision,
            "selected_action",
            getattr(decision, "recommended_action", "UNKNOWN"),
        )
        act_str = raw_act.value if hasattr(raw_act, "value") else str(raw_act)

        corr = get_correlation_context()
        resolved_cycle = (
            corr.cycle_id
            if cycle_number == 1 and corr.cycle_id is not None
            else cycle_number
        )
        if isinstance(resolved_cycle, str):
            try:
                seq = int(resolved_cycle)
            except ValueError:
                seq = 1
        elif isinstance(resolved_cycle, int):
            seq = resolved_cycle
        else:
            seq = 1

        return self.record_event_sync(
            case_id=getattr(
                decision, "case_id", getattr(decision, "recovery_case_id", "")
            ),
            event_type=AuditEventType.DECISION_CREATED,
            actor=AuditActor.MODEL,
            payload={
                "decision_id": getattr(decision, "decision_id", ""),
                "selected_action": act_str,
                "expected_recovery_value": getattr(
                    decision, "expected_recovery_value", None
                ),
                "model_name": getattr(decision, "model_name", "decision_engine"),
                "model_version": getattr(
                    decision,
                    "model_version",
                    getattr(decision, "decision_model_version", "1.0.0"),
                ),
                "dataset_version": getattr(decision, "dataset_version", "dataset-v1"),
                "feature_schema_version": getattr(
                    decision, "feature_schema_version", "1.0"
                ),
                "candidate_actions": candidates,
                "cycle_number": seq,
            },
            source_id=getattr(decision, "decision_id", f"dec_{seq}"),
            sequence=seq,
            uow=uow,
        )

    async def record_decision(
        self,
        decision: Any,
        candidate_actions: list[dict[str, Any]] | None = None,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record DECISION_CREATED event."""
        meta = getattr(decision, "metadata", {}) or {}
        candidates = candidate_actions or meta.get("candidate_actions", [])
        raw_act = getattr(
            decision,
            "selected_action",
            getattr(decision, "recommended_action", "UNKNOWN"),
        )
        act_str = raw_act.value if hasattr(raw_act, "value") else str(raw_act)

        corr = get_correlation_context()
        resolved_cycle = (
            corr.cycle_id
            if cycle_number == 1 and corr.cycle_id is not None
            else cycle_number
        )
        if isinstance(resolved_cycle, str):
            try:
                seq = int(resolved_cycle)
            except ValueError:
                seq = 1
        elif isinstance(resolved_cycle, int):
            seq = resolved_cycle
        else:
            seq = 1

        return await self.record_event(
            case_id=getattr(
                decision, "case_id", getattr(decision, "recovery_case_id", "")
            ),
            event_type=AuditEventType.DECISION_CREATED,
            actor=AuditActor.MODEL,
            payload={
                "decision_id": getattr(decision, "decision_id", ""),
                "selected_action": act_str,
                "expected_recovery_value": getattr(
                    decision, "expected_recovery_value", None
                ),
                "model_name": getattr(decision, "model_name", "decision_engine"),
                "model_version": getattr(
                    decision,
                    "model_version",
                    getattr(decision, "decision_model_version", "1.0.0"),
                ),
                "dataset_version": getattr(decision, "dataset_version", "dataset-v1"),
                "feature_schema_version": getattr(
                    decision, "feature_schema_version", "1.0"
                ),
                "candidate_actions": candidates,
                "cycle_number": seq,
            },
            source_id=getattr(decision, "decision_id", f"dec_{seq}"),
            sequence=seq,
            uow=uow,
        )

    def record_policy_decision_sync(
        self,
        policy_decision: Any,
        cycle_number: int = 1,
        uow: Any | None = None,
    ) -> AuditEvent:
        """Synchronously record POLICY_DECISION_CREATED event."""
        raw_rules = getattr(
            policy_decision,
            "rules_triggered",
            getattr(policy_decision, "triggered_rules", []),
        )
        rules = [str(r.value if hasattr(r, "value") else r) for r in (raw_rules or [])]

        raw_outcome = getattr(
            policy_decision,
            "policy_outcome",
            getattr(policy_decision, "result", "UNKNOWN"),
        )
        if raw_outcome is not None and hasattr(raw_outcome, "value"):
            outcome_str = str(raw_outcome.value)
        else:
            outcome_str = str(raw_outcome or "UNKNOWN")

        raw_eff = getattr(policy_decision, "effective_action", None)
        if raw_eff is not None and hasattr(raw_eff, "value"):
            effective_str = str(raw_eff.value)
        else:
            effective_str = str(raw_eff or "UNKNOWN")

        raw_reason_code = getattr(
            policy_decision,
            "reason_code",
            getattr(policy_decision, "reason", "REASON_UNSPECIFIED"),
        )
        if raw_reason_code is not None and hasattr(raw_reason_code, "value"):
            reason_code_str = str(raw_reason_code.value)
        else:
            reason_code_str = str(raw_reason_code or "REASON_UNSPECIFIED")

        ruleset_ver = getattr(
            policy_decision,
            "rule_set_version",
            getattr(policy_decision, "ruleset_version", "policy-rules-v1"),
        )
        approval_req = getattr(
            policy_decision,
            "approval_required",
            getattr(policy_decision, "requires_human_approval", False),
        )

        corr = get_correlation_context()
        resolved_cycle = (
            corr.cycle_id
            if cycle_number == 1 and corr.cycle_id is not None
            else cycle_number
        )
        if isinstance(resolved_cycle, str):
            try:
                seq = int(resolved_cycle)
            except ValueError:
                seq = 1
        elif isinstance(resolved_cycle, int):
            seq = resolved_cycle
        else:
            seq = 1

        return self.record_event_sync(
            case_id=getattr(policy_decision, "case_id", ""),
            event_type=AuditEventType.POLICY_DECISION_CREATED,
            actor=AuditActor.POLICY,
            payload={
                "policy_decision_id": getattr(
                    policy_decision, "policy_decision_id", ""
                ),
                "decision_id": getattr(policy_decision, "decision_id", ""),
                "result": outcome_str,
                "effective_action": effective_str,
                "reason_code": reason_code_str,
                "rules_triggered": rules,
                "policy_version": getattr(policy_decision, "policy_version", "1.0.0"),
                "ruleset_version": ruleset_ver,
                "requires_human_approval": approval_req,
                "cycle_number": seq,
            },
            source_id=getattr(policy_decision, "policy_decision_id", f"pol_{seq}"),
            sequence=seq,
            uow=uow,
        )

    async def record_policy_decision(
        self,
        policy_decision: Any,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record POLICY_DECISION_CREATED event."""
        raw_rules = getattr(
            policy_decision,
            "rules_triggered",
            getattr(policy_decision, "triggered_rules", []),
        )
        rules = [str(r.value if hasattr(r, "value") else r) for r in (raw_rules or [])]

        raw_outcome = getattr(
            policy_decision,
            "policy_outcome",
            getattr(policy_decision, "result", "UNKNOWN"),
        )
        if raw_outcome is not None and hasattr(raw_outcome, "value"):
            outcome_str = str(raw_outcome.value)
        else:
            outcome_str = str(raw_outcome or "UNKNOWN")

        raw_eff = getattr(policy_decision, "effective_action", None)
        if raw_eff is not None and hasattr(raw_eff, "value"):
            effective_str = str(raw_eff.value)
        else:
            effective_str = str(raw_eff or "UNKNOWN")

        raw_reason_code = getattr(
            policy_decision,
            "reason_code",
            getattr(policy_decision, "reason", "REASON_UNSPECIFIED"),
        )
        if raw_reason_code is not None and hasattr(raw_reason_code, "value"):
            reason_code_str = str(raw_reason_code.value)
        else:
            reason_code_str = str(raw_reason_code or "REASON_UNSPECIFIED")

        ruleset_ver = getattr(
            policy_decision,
            "rule_set_version",
            getattr(policy_decision, "ruleset_version", "policy-rules-v1"),
        )
        approval_req = getattr(
            policy_decision,
            "approval_required",
            getattr(policy_decision, "requires_human_approval", False),
        )

        corr = get_correlation_context()
        resolved_cycle = (
            corr.cycle_id
            if cycle_number == 1 and corr.cycle_id is not None
            else cycle_number
        )
        if isinstance(resolved_cycle, str):
            try:
                seq = int(resolved_cycle)
            except ValueError:
                seq = 1
        elif isinstance(resolved_cycle, int):
            seq = resolved_cycle
        else:
            seq = 1

        return await self.record_event(
            case_id=getattr(policy_decision, "case_id", ""),
            event_type=AuditEventType.POLICY_DECISION_CREATED,
            actor=AuditActor.POLICY,
            payload={
                "policy_decision_id": getattr(
                    policy_decision, "policy_decision_id", ""
                ),
                "decision_id": getattr(policy_decision, "decision_id", ""),
                "result": outcome_str,
                "effective_action": effective_str,
                "reason_code": reason_code_str,
                "rules_triggered": rules,
                "policy_version": getattr(policy_decision, "policy_version", "1.0.0"),
                "ruleset_version": ruleset_ver,
                "requires_human_approval": approval_req,
                "cycle_number": seq,
            },
            source_id=getattr(policy_decision, "policy_decision_id", f"pol_{seq}"),
            sequence=seq,
            uow=uow,
        )

    async def record_execution_started(
        self,
        execution: Execution,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record EXECUTION_STARTED event."""
        executor = getattr(
            execution,
            "execution_type",
            getattr(execution, "executor_name", "UNKNOWN"),
        )
        return await self.record_event(
            case_id=execution.case_id,
            event_type=AuditEventType.EXECUTION_STARTED,
            actor=AuditActor.EXECUTOR,
            payload={
                "execution_id": execution.execution_id,
                "action_id": execution.action_id,
                "execution_mode": str(
                    execution.execution_mode.value
                    if hasattr(execution.execution_mode, "value")
                    else execution.execution_mode
                ),
                "executor_name": executor,
                "cycle_number": cycle_number,
            },
            source_id=execution.execution_id,
            sequence=cycle_number,
            uow=uow,
        )

    async def record_execution_completed(
        self,
        execution: Execution,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record EXECUTION_COMPLETED event."""
        return await self.record_event(
            case_id=execution.case_id,
            event_type=AuditEventType.EXECUTION_COMPLETED,
            actor=AuditActor.EXECUTOR,
            payload={
                "execution_id": execution.execution_id,
                "status": str(
                    execution.status.value
                    if hasattr(execution.status, "value")
                    else execution.status
                ),
                "provider_reference": execution.provider_reference,
                "cycle_number": cycle_number,
            },
            source_id=f"{execution.execution_id}_completed",
            sequence=cycle_number,
            uow=uow,
        )

    async def record_outcome(
        self,
        outcome: Outcome,
        cycle_number: int = 1,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record OUTCOME_PROCESSED event."""
        return await self.record_event(
            case_id=outcome.case_id,
            event_type=AuditEventType.OUTCOME_PROCESSED,
            actor=AuditActor.SYSTEM,
            payload={
                "outcome_id": outcome.outcome_id,
                "execution_id": outcome.execution_id,
                "outcome_type": str(
                    outcome.type.value
                    if hasattr(outcome.type, "value")
                    else outcome.type
                ),
                "amount_recovered": outcome.amount_recovered,
                "evidence_reference": outcome.evidence_reference,
                "cycle_number": cycle_number,
            },
            source_id=outcome.outcome_id,
            sequence=cycle_number,
            uow=uow,
        )

    async def record_re_evaluation(
        self,
        case_id: str,
        cycle_number: int,
        reason: str,
        uow: UnitOfWork | None = None,
    ) -> AuditEvent:
        """Record RE_EVALUATION_STARTED event."""
        return await self.record_event(
            case_id=case_id,
            event_type=AuditEventType.RE_EVALUATION_STARTED,
            actor=AuditActor.SYSTEM,
            payload={
                "cycle_number": cycle_number,
                "reason": reason,
            },
            source_id=f"reeval_{cycle_number}",
            sequence=cycle_number,
            uow=uow,
        )

    def get_in_memory_events(self, case_id: str | None = None) -> list[AuditEvent]:
        """Return captured in-memory audit events."""
        if case_id:
            return [ev for ev in self._in_memory_events if ev.case_id == case_id]
        return list(self._in_memory_events)

    def clear(self) -> None:
        """Clear in-memory state."""
        self._in_memory_events.clear()
        self._seen_event_ids.clear()
