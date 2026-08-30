"""Recovery Case Orchestration Service for APRO Phase 4."""

import logging
import uuid
from datetime import UTC, datetime

from apro.domain.enums import AuditActor, PaymentStatus, RecoveryCaseStatus
from apro.domain.exceptions import CapturedPaymentRecoveryError
from apro.domain.models import AuditEvent, Payment, PaymentEvent, RecoveryCase
from apro.domain.state_machines import transition_recovery_case
from apro.persistence.unit_of_work import UnitOfWork

logger = logging.getLogger("apro.recovery.orchestrator")


class RecoveryCaseOrchestrator:
    """Orchestrates RecoveryCase lifecycle in response to canonical PaymentEvents."""

    async def handle_payment_event(
        self, uow: UnitOfWork, event: PaymentEvent, payment: Payment
    ) -> RecoveryCase | None:
        """Evaluate case eligibility and route canonical PaymentEvent."""
        if payment.status == PaymentStatus.CAPTURED:
            return await self.handle_payment_captured(uow, payment, event)
        if event.event_type == "payment.failed":
            return await self.handle_payment_failed(uow, payment, event)

        # Non-failed event for active payment: return existing active case if present
        return await uow.recovery_cases.find_active_by_payment_id(
            payment.payment_id, for_update=False
        )

    async def handle_payment_failed(
        self, uow: UnitOfWork, payment: Payment, event: PaymentEvent
    ) -> RecoveryCase:
        """Handle payment.failed event: create new RecoveryCase or reuse active case."""
        if payment.status == PaymentStatus.CAPTURED:
            msg = (
                f"Cannot open recovery case for CAPTURED payment {payment.payment_id}."
            )
            raise CapturedPaymentRecoveryError(msg)

        now = event.received_at or datetime.now(UTC)

        # Active case lookup with pessimistic row lock
        active_case = await uow.recovery_cases.find_active_by_payment_id(
            payment.payment_id, for_update=True
        )

        if active_case is not None:
            logger.info(
                "Reusing active RecoveryCase %s for payment %s",
                active_case.case_id,
                payment.payment_id,
            )
            audit = AuditEvent(
                audit_event_id=str(uuid.uuid4()),
                case_id=active_case.case_id,
                event_type="RECOVERY_CASE_REUSED",
                actor=AuditActor.SYSTEM,
                timestamp=now,
                payload={
                    "trigger_event_id": event.event_id,
                    "payment_id": payment.payment_id,
                    "status": (
                        active_case.status.value
                        if isinstance(active_case.status, RecoveryCaseStatus)
                        else str(active_case.status)
                    ),
                    "reason": "Active recovery case reused",
                },
                correlation_id=event.event_id,
            )
            await uow.audit_events.append(audit)
            return active_case

        # Create new RecoveryCase
        new_case = RecoveryCase(
            case_id=str(uuid.uuid4()),
            payment_id=payment.payment_id,
            customer_id=payment.customer_id,
            status=RecoveryCaseStatus.NEW,
            opened_at=now,
            updated_at=now,
            closed_at=None,
            recovery_amount=payment.amount,
            current_attempt_count=0,
            stop_reason=None,
            escalation_reason=None,
        )
        saved_case = await uow.recovery_cases.save(new_case)
        logger.info(
            "Created new RecoveryCase %s (status=NEW) for payment %s",
            saved_case.case_id,
            payment.payment_id,
        )

        audit = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=saved_case.case_id,
            event_type="RECOVERY_CASE_CREATED",
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={
                "trigger_event_id": event.event_id,
                "payment_id": payment.payment_id,
                "initial_status": "NEW",
                "recovery_amount": payment.amount,
            },
            correlation_id=event.event_id,
        )
        await uow.audit_events.append(audit)
        return saved_case

    async def handle_payment_captured(
        self, uow: UnitOfWork, payment: Payment, event: PaymentEvent
    ) -> RecoveryCase | None:
        """Handle payment capture: safely terminate any active RecoveryCase."""
        now = event.received_at or datetime.now(UTC)

        active_case = await uow.recovery_cases.find_active_by_payment_id(
            payment.payment_id, for_update=True
        )
        if active_case is None:
            return None

        previous_status = active_case.status
        if active_case.status == RecoveryCaseStatus.OBSERVING:
            target_status = RecoveryCaseStatus.RECOVERED
            audit_type = "RECOVERY_CASE_RECOVERED"
            reason = "Payment captured while case in OBSERVING"
        else:
            target_status = RecoveryCaseStatus.STOPPED
            audit_type = "RECOVERY_CASE_STOPPED"
            reason = "Payment captured; active recovery terminated"

        updated_case = transition_recovery_case(
            active_case, payment, target_status, now=now
        )
        if target_status == RecoveryCaseStatus.STOPPED:
            updated_case = updated_case.model_copy(update={"stop_reason": reason})

        saved_case = await uow.recovery_cases.save(updated_case)
        logger.info(
            "Terminated active RecoveryCase %s (%s -> %s) due to capture",
            saved_case.case_id,
            previous_status,
            target_status,
        )

        audit = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=saved_case.case_id,
            event_type=audit_type,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={
                "trigger_event_id": event.event_id,
                "payment_id": payment.payment_id,
                "previous_status": (
                    previous_status.value
                    if isinstance(previous_status, RecoveryCaseStatus)
                    else str(previous_status)
                ),
                "new_status": target_status.value,
                "reason": reason,
            },
            correlation_id=event.event_id,
        )
        await uow.audit_events.append(audit)
        return saved_case

    async def transition_case(
        self,
        uow: UnitOfWork,
        case_id: str,
        new_status: RecoveryCaseStatus,
        reason: str | None = None,
        now: datetime | None = None,
    ) -> RecoveryCase:
        """Perform a controlled domain state transition on a RecoveryCase."""
        timestamp = now or datetime.now(UTC)

        case = await uow.recovery_cases.get_by_id(case_id)
        if case is None:
            msg = f"RecoveryCase {case_id} not found."
            raise ValueError(msg)

        payment = await uow.payments.get_by_id(case.payment_id)
        if payment is None:
            msg = f"Payment {case.payment_id} for case {case_id} not found."
            raise ValueError(msg)

        previous_status = case.status
        updated_case = transition_recovery_case(
            case, payment, new_status, now=timestamp
        )

        if new_status == RecoveryCaseStatus.STOPPED and reason:
            updated_case = updated_case.model_copy(update={"stop_reason": reason})
        elif new_status == RecoveryCaseStatus.ESCALATED and reason:
            updated_case = updated_case.model_copy(update={"escalation_reason": reason})

        saved_case = await uow.recovery_cases.save(updated_case)

        if new_status == RecoveryCaseStatus.STOPPED:
            audit_type = "RECOVERY_CASE_STOPPED"
        elif new_status == RecoveryCaseStatus.RECOVERED:
            audit_type = "RECOVERY_CASE_RECOVERED"
        elif new_status == RecoveryCaseStatus.ESCALATED:
            audit_type = "RECOVERY_CASE_ESCALATED"
        else:
            audit_type = "RECOVERY_CASE_TRANSITIONED"

        audit = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=saved_case.case_id,
            event_type=audit_type,
            actor=AuditActor.SYSTEM,
            timestamp=timestamp,
            payload={
                "payment_id": payment.payment_id,
                "previous_status": (
                    previous_status.value
                    if isinstance(previous_status, RecoveryCaseStatus)
                    else str(previous_status)
                ),
                "new_status": new_status.value,
                "reason": reason or f"Transitioned to {new_status.value}",
            },
        )
        await uow.audit_events.append(audit)
        return saved_case
