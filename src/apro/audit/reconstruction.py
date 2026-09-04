"""Case audit reconstruction service for Phase 14."""

from typing import Any

from apro.audit.enums import (
    AUDIT_SCHEMA_VERSION,
    AuditEventType,
)
from apro.audit.exceptions import AuditNotFoundError
from apro.audit.integrity import AuditIntegrityChecker
from apro.audit.models import (
    CaseAuditTrace,
    CycleTraceRecord,
    DecisionTraceRecord,
    ExecutionTraceRecord,
    OutcomeTraceRecord,
    PolicyTraceRecord,
)
from apro.audit.sanitization import TelemetrySanitizer
from apro.audit.tracing import (
    build_decision_trace,
    build_execution_trace,
    build_outcome_trace,
    build_policy_trace,
)
from apro.domain.enums import ExecutionMode, ExecutionStatus, OutcomeType
from apro.domain.models import (
    AuditEvent,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PaymentEvent,
    RecoveryCase,
)
from apro.persistence.unit_of_work import UnitOfWork


class CaseReconstructionService:
    """Reconstructs complete, explainable audit traces for recovery cases."""

    @classmethod
    async def reconstruct_case(
        cls,
        case_id: str,
        uow: UnitOfWork | None = None,
        audit_events: list[AuditEvent] | None = None,
        case: RecoveryCase | None = None,
        payment: Payment | None = None,
        trigger_event: PaymentEvent | None = None,
        diagnosis: Diagnosis | None = None,
        decisions: list[Any] | None = None,
        policy_decisions: list[Any] | None = None,
        executions: list[Execution] | None = None,
        outcomes: list[Outcome] | None = None,
    ) -> CaseAuditTrace:
        """Reconstruct a complete CaseAuditTrace from persisted records."""
        events: list[AuditEvent] = []
        if uow is not None:
            # Query actual persisted database records
            events = await uow.audit_events.find_by_case_id(case_id)
            if case is None:
                case = await uow.recovery_cases.get_by_id(case_id)
            if case and payment is None:
                payment = await uow.payments.get_by_id(case.payment_id)
            if diagnosis is None:
                diag_list = await uow.diagnoses.find_by_case_id(case_id)
                diagnosis = diag_list[0] if diag_list else None
            if decisions is None:
                decisions = await uow.decisions.find_by_case_id(case_id)
            if policy_decisions is None:
                policy_decisions = await uow.policy_decisions.find_by_case_id(case_id)
            if executions is None:
                executions = await uow.executions.find_by_case_id(case_id)
            if outcomes is None:
                outcomes = await uow.outcomes.find_by_case_id(case_id)
        elif audit_events is not None:
            events = [ev for ev in audit_events if ev.case_id == case_id]

        if not events and case is None:
            raise AuditNotFoundError(f"No audit records found for case_id={case_id}")

        # Deterministic sorting: timestamp then audit_event_id
        sorted_events = sorted(events, key=lambda e: (e.timestamp, e.audit_event_id))

        # Integrity Validation
        is_integrity_valid, integrity_issues = (
            AuditIntegrityChecker.validate_events_integrity(
                case_id=case_id,
                events=sorted_events,
            )
        )

        dec_list = decisions or []
        pol_list = policy_decisions or []
        exec_list = executions or []
        out_list = outcomes or []

        # Determine number of cycles
        max_event_cycle = max(
            [
                ev.payload.get("cycle_number", 1)
                for ev in sorted_events
                if isinstance(ev.payload.get("cycle_number"), int)
            ]
            or [1]
        )
        cycle_count = max(
            len(dec_list),
            len(pol_list),
            len(exec_list),
            len(out_list),
            max_event_cycle,
            1,
        )

        cycles: list[CycleTraceRecord] = []
        for i in range(1, cycle_count + 1):
            cycle_events = [
                ev
                for ev in sorted_events
                if ev.payload.get("cycle_number") == i
                or (i == 1 and ev.payload.get("cycle_number") is None)
            ]

            dec_candidates = None
            for ev in cycle_events:
                if ev.event_type in (
                    AuditEventType.DECISION_CREATED,
                    "DECISION_CREATED",
                ):
                    dec_candidates = ev.payload.get("candidate_actions")
                    break

            dec_rec: DecisionTraceRecord | None = None
            if i - 1 < len(dec_list):
                dec_rec = build_decision_trace(
                    dec_list[i - 1],
                    cycle_number=i,
                    candidate_actions=dec_candidates,
                )
            else:
                for ev in cycle_events:
                    if ev.event_type in (
                        AuditEventType.DECISION_CREATED,
                        "DECISION_CREATED",
                    ):
                        p = dict(ev.payload)
                        p.setdefault("created_at", ev.timestamp)
                        p.setdefault("case_id", ev.case_id)
                        dec_rec = build_decision_trace(
                            p, cycle_number=i, candidate_actions=dec_candidates
                        )
                        break

            pol_rec: PolicyTraceRecord | None = None
            if i - 1 < len(pol_list):
                pol_rec = build_policy_trace(pol_list[i - 1])
            else:
                for ev in cycle_events:
                    if ev.event_type in (
                        AuditEventType.POLICY_DECISION_CREATED,
                        "POLICY_DECISION_CREATED",
                    ):
                        p = dict(ev.payload)
                        p.setdefault("created_at", ev.timestamp)
                        p.setdefault("case_id", ev.case_id)
                        pol_rec = build_policy_trace(p)
                        break

            exec_rec: ExecutionTraceRecord | None = None
            if i - 1 < len(exec_list):
                exec_rec = build_execution_trace(exec_list[i - 1])
            else:
                for ev in cycle_events:
                    if ev.event_type in (
                        AuditEventType.EXECUTION_COMPLETED,
                        "EXECUTION_COMPLETED",
                        AuditEventType.EXECUTION_STARTED,
                        "EXECUTION_STARTED",
                    ):
                        p = dict(ev.payload)
                        mode_str = p.get("execution_mode", "SIMULATION")
                        mode_obj = (
                            ExecutionMode(mode_str)
                            if mode_str in [e.value for e in ExecutionMode]
                            else ExecutionMode.SIMULATION
                        )
                        status_str = p.get("status", "SUCCEEDED")
                        status_obj = (
                            ExecutionStatus(status_str)
                            if status_str in [e.value for e in ExecutionStatus]
                            else ExecutionStatus.SUCCEEDED
                        )
                        exec_obj = Execution(
                            execution_id=p.get("execution_id", ev.audit_event_id),
                            action_id=p.get("action_id", f"act_{ev.case_id[:8]}_{i}"),
                            case_id=ev.case_id,
                            execution_type=p.get("execution_type", "UNKNOWN"),
                            execution_mode=mode_obj,
                            status=status_obj,
                            provider_reference=p.get("provider_reference"),
                            started_at=ev.timestamp,
                            completed_at=ev.timestamp
                            if "COMPLETED" in str(ev.event_type)
                            else None,
                            error_code=p.get("error_code"),
                            error_message=p.get("error_message"),
                        )
                        exec_rec = build_execution_trace(exec_obj)
                        break

            out_rec: OutcomeTraceRecord | None = None
            if i - 1 < len(out_list):
                out_rec = build_outcome_trace(out_list[i - 1])
            else:
                for ev in cycle_events:
                    if ev.event_type in (
                        AuditEventType.OUTCOME_PROCESSED,
                        "OUTCOME_PROCESSED",
                    ):
                        p = dict(ev.payload)
                        out_type_str = p.get("outcome_type", p.get("type", "FAILED"))
                        out_type_obj = (
                            OutcomeType(out_type_str)
                            if out_type_str in [e.value for e in OutcomeType]
                            else OutcomeType.FAILED
                        )
                        out_obj = Outcome(
                            outcome_id=p.get("outcome_id", ev.audit_event_id),
                            case_id=ev.case_id,
                            execution_id=p.get("execution_id", ""),
                            type=out_type_obj,
                            amount_recovered=int(p.get("amount_recovered", 0) or 0),
                            evidence_reference=p.get("evidence_reference", ""),
                            observed_at=ev.timestamp,
                        )
                        out_rec = build_outcome_trace(out_obj)
                        break

            cycles.append(
                CycleTraceRecord(
                    cycle_number=i,
                    re_evaluation_id=f"reeval_{i}" if i > 1 else None,
                    decision=dec_rec,
                    policy=pol_rec,
                    execution=exec_rec,
                    outcome=out_rec,
                    events=cycle_events,
                )
            )

        final_status = "UNKNOWN"
        if case is not None:
            final_status = str(
                case.status.value if hasattr(case.status, "value") else case.status
            )

        final_outcome_type: str | None = None
        total_recovered = 0
        if out_list:
            last_out = out_list[-1]
            final_outcome_type = str(
                last_out.type.value
                if hasattr(last_out.type, "value")
                else last_out.type
            )
            total_recovered = sum(o.amount_recovered for o in out_list)
        else:
            cycle_outcomes = [c.outcome for c in cycles if c.outcome is not None]
            if cycle_outcomes:
                last_c_out = cycle_outcomes[-1]
                final_outcome_type = str(last_c_out.outcome_type)
                total_recovered = sum(
                    c.outcome.amount_recovered
                    for c in cycles
                    if c.outcome and c.outcome.amount_recovered
                )

        # Completeness Evaluation
        if sorted_events:
            has_case_artifact = case is not None and any(
                ev.event_type
                in (
                    AuditEventType.CASE_CREATED,
                    "RECOVERY_CASE_CREATED",
                    "CASE_CREATED",
                )
                for ev in sorted_events
            )
            has_diag_artifact = diagnosis is not None and any(
                ev.event_type in (AuditEventType.DIAGNOSIS_CREATED, "DIAGNOSIS_CREATED")
                for ev in sorted_events
            )
            has_dec_artifact = len(dec_list) > 0 and any(
                ev.event_type in (AuditEventType.DECISION_CREATED, "DECISION_CREATED")
                for ev in sorted_events
            )
            has_pol_artifact = len(pol_list) > 0 and any(
                ev.event_type
                in (
                    AuditEventType.POLICY_DECISION_CREATED,
                    "POLICY_DECISION_CREATED",
                )
                for ev in sorted_events
            )
            has_exec_artifact = len(exec_list) > 0 and any(
                ev.event_type
                in (
                    AuditEventType.EXECUTION_STARTED,
                    AuditEventType.EXECUTION_COMPLETED,
                    "EXECUTION_STARTED",
                    "EXECUTION_COMPLETED",
                )
                for ev in sorted_events
            )
            has_out_artifact = len(out_list) > 0 and any(
                ev.event_type in (AuditEventType.OUTCOME_PROCESSED, "OUTCOME_PROCESSED")
                for ev in sorted_events
            )
        else:
            has_case_artifact = case is not None
            has_diag_artifact = diagnosis is not None
            has_dec_artifact = len(dec_list) > 0
            has_pol_artifact = len(pol_list) > 0
            has_exec_artifact = len(exec_list) > 0
            has_out_artifact = len(out_list) > 0
        is_terminal = final_status in ("RECOVERED", "STOPPED", "ESCALATED")

        completeness = AuditIntegrityChecker.evaluate_completeness(
            has_case=has_case_artifact,
            has_diagnosis=has_diag_artifact,
            has_decision=has_dec_artifact,
            has_policy=has_pol_artifact,
            has_execution=has_exec_artifact,
            has_outcome=has_out_artifact,
            is_terminal=is_terminal,
        )

        # Answer the 7 Authoritative Reviewer Questions
        diag_cat = None
        if diagnosis:
            raw_c = getattr(
                diagnosis,
                "category",
                getattr(diagnosis, "failure_category", None),
            )
            if raw_c is not None and hasattr(raw_c, "value"):
                diag_cat = str(raw_c.value)
            else:
                diag_cat = str(raw_c) if raw_c is not None else None

        reviewer_answers: dict[str, Any] = {
            "Q1_what_happened": {
                "case_id": case_id,
                "payment_id": case.payment_id if case else None,
                "amount": (
                    payment.amount
                    if payment
                    else (case.recovery_amount if case else None)
                ),
                "trigger": trigger_event.event_id if trigger_event else None,
                "initial_status": "NEW",
            },
            "Q2_why_interpreted": {
                "diagnosis_id": diagnosis.diagnosis_id if diagnosis else None,
                "category": diag_cat,
                "confidence": diagnosis.confidence if diagnosis else None,
                "model_version": diagnosis.model_version if diagnosis else None,
            },
            "Q3_what_considered": [
                c.decision.candidate_actions for c in cycles if c.decision
            ],
            "Q4_what_recommended": [
                {
                    "cycle": c.cycle_number,
                    "selected_action": c.decision.selected_action,
                    "model_version": c.decision.model_version,
                    "erv": c.decision.expected_recovery_value,
                }
                for c in cycles
                if c.decision
            ],
            "Q5_what_policy_allowed": [
                {
                    "cycle": c.cycle_number,
                    "policy_outcome": c.policy.policy_outcome,
                    "effective_action": c.policy.effective_action,
                    "rules_triggered": c.policy.rules_triggered,
                    "reason_code": c.policy.reason_code,
                    "policy_version": c.policy.policy_version,
                }
                for c in cycles
                if c.policy
            ],
            "Q6_what_executed": [
                {
                    "cycle": c.cycle_number,
                    "execution_id": c.execution.execution_id,
                    "execution_mode": c.execution.execution_mode,
                    "executor": c.execution.executor_name,
                    "status": c.execution.status,
                    "provider_reference": c.execution.provider_reference,
                }
                for c in cycles
                if c.execution
            ],
            "Q7_what_happened_afterward": {
                "total_cycles": len(cycles),
                "outcomes": [
                    {
                        "cycle": c.cycle_number,
                        "type": c.outcome.outcome_type,
                        "amount_recovered": c.outcome.amount_recovered,
                    }
                    for c in cycles
                    if c.outcome
                ],
                "final_case_status": final_status,
                "total_amount_recovered": total_recovered,
            },
        }

        trace_id = (
            sorted_events[0].correlation_id if sorted_events else f"trace_{case_id}"
        )

        return CaseAuditTrace(
            case_id=case_id,
            trace_id=trace_id,
            schema_version=AUDIT_SCHEMA_VERSION,
            initial_event=(
                TelemetrySanitizer.sanitize(trigger_event.model_dump())
                if trigger_event
                else None
            ),
            diagnosis=(
                TelemetrySanitizer.sanitize(diagnosis.model_dump())
                if diagnosis
                else None
            ),
            predictions=[],
            cycles=cycles,
            events=sorted_events,
            final_case_status=final_status,
            final_outcome_type=final_outcome_type,
            total_amount_recovered=total_recovered,
            completeness=completeness,
            integrity_valid=is_integrity_valid,
            integrity_issues=integrity_issues,
            reviewer_answers=reviewer_answers,
        )
