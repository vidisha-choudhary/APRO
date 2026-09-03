"""Outcome processor evaluating evidence and advancing case state in Phase 13."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from apro.domain.enums import (
    ExecutionStatus,
    OutcomeType,
    PaymentStatus,
    RecoveryCaseStatus,
)
from apro.domain.models import Execution, Outcome, Payment, RecoveryCase
from apro.domain.state_machines import (
    transition_payment,
    transition_recovery_case,
)
from apro.persistence.unit_of_work import UnitOfWork
from apro.recovery_loop.dispositions import DispositionResolver
from apro.recovery_loop.enums import (
    EvidenceProvenance,
    EvidenceType,
    RecoveryLoopDisposition,
)
from apro.recovery_loop.exceptions import (
    EntityMismatchError,
    TerminalCaseReopenError,
)
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.history import ActionHistoryService
from apro.recovery_loop.models import (
    ActionHistoryRecord,
    OutcomeEvidence,
    OutcomeProcessingResult,
)

_TERMINAL_STATUSES = {
    RecoveryCaseStatus.RECOVERED,
    RecoveryCaseStatus.STOPPED,
    RecoveryCaseStatus.ESCALATED,
}


def compute_outcome_id(
    case_id: str,
    execution_id: str | None,
    evidence_id: str,
    evidence_type: str,
) -> str:
    """Generate a deterministic UUID identifier for an outcome record."""
    payload: dict[str, Any] = {
        "case_id": case_id,
        "execution_id": execution_id or "",
        "evidence_id": evidence_id,
        "evidence_type": str(evidence_type),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hex_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]
    return str(uuid.UUID(hex=hex_digest))


class OutcomeProcessor:
    """Consumes normalized outcome evidence, persists immutable Outcome,
    and advances RecoveryCase.
    """

    def __init__(
        self,
        disposition_resolver: DispositionResolver | None = None,
        history_service: ActionHistoryService | None = None,
        safety_guard: LoopSafetyGuard | None = None,
    ) -> None:
        self.safety_guard = safety_guard or LoopSafetyGuard()
        self.disposition_resolver = disposition_resolver or DispositionResolver(
            self.safety_guard
        )
        self.history_service = history_service or ActionHistoryService()
        self._in_memory_outcomes: dict[str, Outcome] = {}

    def _classify_outcome(
        self,
        evidence: OutcomeEvidence,
        execution: Execution | None,
        payment: Payment,
    ) -> tuple[OutcomeType, int]:
        """Deterministically map evidence into domain OutcomeType and
        recovered amount.

        Invariant: RECOVERED requires verified recovery proof (payment is
        captured or verified provider status). Positive amount alone without
        verification is not classified as RECOVERED.
        """
        # 1. Recovery confirmation (requires verified payment capture
        # or verified provider status)
        is_verified_captured = (
            payment.status == PaymentStatus.CAPTURED
            or evidence.payment_status == PaymentStatus.CAPTURED
        )
        raw_status = str(evidence.raw_details.get("status", "")).lower()
        is_verified_raw_recovery = raw_status in ("paid", "captured", "recovered")

        if is_verified_captured or is_verified_raw_recovery:
            amount = (
                evidence.amount_recovered
                if evidence.amount_recovered > 0
                else payment.amount
            )
            return OutcomeType.RECOVERED, amount

        # 2. Check explicit non-recovery provider status
        if raw_status in ("expired",):
            return OutcomeType.EXPIRED, 0
        if raw_status in ("cancelled", "failed", "rejected"):
            return OutcomeType.FAILED, 0
        if raw_status in ("escalated", "fraud_review", "disputed", "manual_review"):
            return OutcomeType.ESCALATED, 0

        # 3. Process Execution Result evidence
        if (
            evidence.evidence_type == EvidenceType.EXECUTION_RESULT
            and execution is not None
        ):
            if execution.status == ExecutionStatus.SUCCEEDED:
                # Invariant: Execution != Recovery. No capture proof = PENDING.
                return OutcomeType.PENDING, 0
            if execution.status == ExecutionStatus.UNKNOWN:
                # Invariant: UNKNOWN is indeterminate, not false FAILED.
                return OutcomeType.PENDING, 0
            if execution.status == ExecutionStatus.FAILED:
                return OutcomeType.FAILED, 0
            if execution.status == ExecutionStatus.CANCELLED:
                return OutcomeType.STOPPED, 0

        # 4. Payment Event evidence
        if evidence.evidence_type == EvidenceType.PAYMENT_EVENT:
            if evidence.payment_status == PaymentStatus.FAILED:
                return OutcomeType.FAILED, 0
            if evidence.payment_status == PaymentStatus.PENDING:
                return OutcomeType.PENDING, 0

        # Default conservative classification
        return OutcomeType.PENDING, 0

    async def process_outcome(
        self,
        evidence: OutcomeEvidence,
        case: RecoveryCase,
        payment: Payment,
        execution: Execution | None = None,
        history: tuple[ActionHistoryRecord, ...]
        | list[ActionHistoryRecord]
        | None = None,
        cycle_number: int = 1,
        now: datetime | None = None,
        uow: UnitOfWork | None = None,
    ) -> tuple[OutcomeProcessingResult, RecoveryCase, Payment]:
        """Process normalized outcome evidence and advance case state.

        Returns:
            (processing_result, updated_case, updated_payment)
        """
        current_time = now or datetime.now(UTC)

        # 1. Validate Entity Bindings
        if evidence.case_id != case.case_id:
            msg = (
                f"Evidence case_id '{evidence.case_id}' does not match "
                f"RecoveryCase '{case.case_id}'."
            )
            raise EntityMismatchError(msg)

        if payment.payment_id != case.payment_id:
            msg = (
                f"Payment payment_id '{payment.payment_id}' does not match "
                f"RecoveryCase payment_id '{case.payment_id}'."
            )
            raise EntityMismatchError(msg)

        if execution is not None and execution.case_id != case.case_id:
            msg = (
                f"Execution case_id '{execution.case_id}' does not match "
                f"RecoveryCase '{case.case_id}'."
            )
            raise EntityMismatchError(msg)

        # 2. Check Terminal State Invariant
        outcome_id = compute_outcome_id(
            case_id=case.case_id,
            execution_id=execution.execution_id if execution else evidence.execution_id,
            evidence_id=evidence.evidence_id,
            evidence_type=evidence.evidence_type.value,
        )

        # 3. Check Outcome Idempotency
        existing_outcome: Outcome | None = None
        if uow is not None:
            existing_outcome = await uow.outcomes.get_by_id(outcome_id)
        if existing_outcome is None:
            existing_outcome = self._in_memory_outcomes.get(outcome_id)

        provenance_val = (
            evidence.provenance
            if isinstance(evidence.provenance, EvidenceProvenance)
            else EvidenceProvenance(evidence.provenance)
        )

        if existing_outcome is not None:
            # Reconstruct idempotent result without duplicate state mutations
            active_history = history or (
                await self.history_service.get_case_history(case.case_id, uow)
                if uow
                else ()
            )
            disposition, termination_reason = self.disposition_resolver.resolve(
                outcome=existing_outcome,
                case=case,
                payment=payment,
                history=active_history,
                cycle_number=cycle_number,
            )
            result = OutcomeProcessingResult(
                outcome=existing_outcome,
                disposition=disposition,
                case_status=case.status,
                re_evaluation_id=None,
                termination_reason=termination_reason,
                cycle_number=cycle_number,
                provenance=provenance_val,
            )
            return result, case, payment

        # If not a duplicate and case is already terminal, cannot process
        if case.status in _TERMINAL_STATUSES:
            msg = (
                f"RecoveryCase '{case.case_id}' is in terminal state '{case.status}' "
                "and cannot process new outcomes."
            )
            raise TerminalCaseReopenError(msg)

        # 4. Classify Outcome
        outcome_type, amount_recovered = self._classify_outcome(
            evidence=evidence,
            execution=execution,
            payment=payment,
        )

        exec_id = (
            execution.execution_id
            if execution
            else (
                evidence.execution_id
                or str(
                    uuid.uuid5(
                        uuid.NAMESPACE_DNS, f"exec_virtual_{evidence.evidence_id}"
                    )
                )
            )
        )

        prov_str = (
            evidence.provenance.value
            if hasattr(evidence.provenance, "value")
            else str(evidence.provenance)
        )
        evidence_ref = (
            evidence.evidence_reference
            or f"provenance={prov_str}:{evidence.evidence_id}"
        )

        outcome = Outcome(
            outcome_id=outcome_id,
            case_id=case.case_id,
            execution_id=exec_id,
            type=outcome_type,
            amount_recovered=amount_recovered,
            evidence_reference=evidence_ref,
            observed_at=evidence.observed_at or current_time,
        )

        # 5. Build Updated History
        active_history = list(
            history
            or (
                await self.history_service.get_case_history(case.case_id, uow)
                if uow
                else []
            )
        )

        # 6. Resolve Explicit Disposition
        disposition, termination_reason = self.disposition_resolver.resolve(
            outcome=outcome,
            case=case,
            payment=payment,
            history=active_history,
            cycle_number=cycle_number,
        )

        # 7. Advance Domain State Machines
        updated_payment = payment
        if (
            outcome_type == OutcomeType.RECOVERED
            and payment.status != PaymentStatus.CAPTURED
        ):
            updated_payment = transition_payment(
                payment=payment,
                new_status=PaymentStatus.CAPTURED,
                now=current_time,
            )

        # Determine target case status based on outcome & disposition
        target_case_status = case.status
        if outcome_type == OutcomeType.RECOVERED:
            target_case_status = RecoveryCaseStatus.RECOVERED
        elif disposition == RecoveryLoopDisposition.RE_EVALUATE:
            target_case_status = RecoveryCaseStatus.EVALUATING
        elif disposition == RecoveryLoopDisposition.STOP:
            target_case_status = RecoveryCaseStatus.STOPPED
        elif disposition == RecoveryLoopDisposition.ESCALATE:
            target_case_status = RecoveryCaseStatus.ESCALATED
        elif disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME:
            # Case remains in OBSERVING or current non-terminal state
            target_case_status = (
                RecoveryCaseStatus.OBSERVING
                if case.status != RecoveryCaseStatus.OBSERVING
                else case.status
            )

        updated_case = case
        if target_case_status != case.status:
            # Handle intermediate transition if necessary
            if (
                case.status == RecoveryCaseStatus.EXECUTING
                and target_case_status != RecoveryCaseStatus.OBSERVING
            ):
                observing_case = transition_recovery_case(
                    case=case,
                    payment=updated_payment,
                    new_status=RecoveryCaseStatus.OBSERVING,
                    now=current_time,
                )
                updated_case = transition_recovery_case(
                    case=observing_case,
                    payment=updated_payment,
                    new_status=target_case_status,
                    now=current_time,
                )
            else:
                updated_case = transition_recovery_case(
                    case=case,
                    payment=updated_payment,
                    new_status=target_case_status,
                    now=current_time,
                )

        # Update case attempt count and closed_at if terminal
        case_updates: dict[str, Any] = {
            "current_attempt_count": max(case.current_attempt_count, cycle_number),
            "updated_at": current_time,
        }
        if target_case_status in _TERMINAL_STATUSES:
            case_updates["closed_at"] = current_time
            if target_case_status == RecoveryCaseStatus.STOPPED:
                case_updates["stop_reason"] = (
                    termination_reason.value if termination_reason else "STOPPED"
                )
            elif target_case_status == RecoveryCaseStatus.ESCALATED:
                case_updates["escalation_reason"] = (
                    termination_reason.value if termination_reason else "ESCALATED"
                )
            elif target_case_status == RecoveryCaseStatus.RECOVERED:
                case_updates["recovery_amount"] = amount_recovered

        updated_case = updated_case.model_copy(update=case_updates)

        # 8. Persist Outcome and Case (with idempotent concurrency handling)
        self._in_memory_outcomes[outcome_id] = outcome
        if uow is not None:
            try:
                await uow.outcomes.append(outcome)
                await uow.recovery_cases.save(updated_case)
                if updated_payment.status != payment.status:
                    await uow.payments.save(updated_payment)
            except Exception as e:
                # Handle unique constraint collision if another concurrent
                # transaction inserted first
                from sqlalchemy.exc import IntegrityError

                if (
                    isinstance(e, IntegrityError)
                    or "unique" in str(e).lower()
                    or "duplicate" in str(e).lower()
                    or "already exists" in str(e).lower()
                ):
                    await uow.rollback()
                    existing_outcome = await uow.outcomes.get_by_id(outcome_id)
                    if existing_outcome is not None:
                        current_case = (
                            await uow.recovery_cases.get_by_id(case.case_id)
                            or updated_case
                        )
                        current_payment = (
                            await uow.payments.get_by_id(payment.payment_id)
                            or updated_payment
                        )
                        disposition, termination_reason = (
                            self.disposition_resolver.resolve(
                                outcome=existing_outcome,
                                case=current_case,
                                payment=current_payment,
                                history=active_history,
                                cycle_number=cycle_number,
                            )
                        )
                        return (
                            OutcomeProcessingResult(
                                outcome=existing_outcome,
                                disposition=disposition,
                                case_status=current_case.status,
                                re_evaluation_id=None,
                                termination_reason=termination_reason,
                                cycle_number=cycle_number,
                                provenance=provenance_val,
                            ),
                            current_case,
                            current_payment,
                        )
                raise

        result = OutcomeProcessingResult(
            outcome=outcome,
            disposition=disposition,
            case_status=updated_case.status,
            re_evaluation_id=None,
            termination_reason=termination_reason,
            cycle_number=cycle_number,
            provenance=provenance_val,
        )

        return result, updated_case, updated_payment
