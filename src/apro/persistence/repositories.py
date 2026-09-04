"""Domain-oriented asynchronous repositories for APRO Phase 2 persistence."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apro.domain.enums import (
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryCaseStatus,
)
from apro.domain.exceptions import (
    InvalidStateTransitionError,
)
from apro.domain.models import (
    ActionEvaluation,
    AuditEvent,
    Customer,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PaymentEvent,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.persistence.mapper import (
    action_evaluation_to_domain,
    action_evaluation_to_orm,
    audit_event_to_domain,
    audit_event_to_orm,
    customer_to_domain,
    customer_to_orm,
    decision_to_domain,
    decision_to_orm,
    diagnosis_to_domain,
    diagnosis_to_orm,
    execution_to_domain,
    execution_to_orm,
    outcome_to_domain,
    outcome_to_orm,
    payment_event_to_domain,
    payment_event_to_orm,
    payment_to_domain,
    payment_to_orm,
    policy_decision_to_domain,
    policy_decision_to_orm,
    recovery_action_to_domain,
    recovery_action_to_orm,
    recovery_case_to_domain,
    recovery_case_to_orm,
)
from apro.persistence.models import (
    ActionEvaluationModel,
    AuditEventModel,
    CustomerModel,
    DecisionModel,
    DiagnosisModel,
    ExecutionModel,
    OutcomeModel,
    PaymentEventModel,
    PaymentModel,
    PolicyDecisionModel,
    RawEventModel,
    RecoveryActionModel,
    RecoveryCaseModel,
)


class CustomerRepository:
    """Repository for Customer persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, customer: Customer) -> Customer:
        orm = await self._session.get(CustomerModel, customer.customer_id)
        if orm is None:
            orm = customer_to_orm(customer)
            self._session.add(orm)
        else:
            orm.external_reference = customer.external_reference
            orm.updated_at = customer.updated_at
            orm.historical_payment_count = customer.historical_payment_count
            orm.historical_success_count = customer.historical_success_count
            orm.historical_failure_count = customer.historical_failure_count
            orm.historical_recovery_count = customer.historical_recovery_count
        await self._session.flush()
        return customer_to_domain(orm)

    async def get_by_id(self, customer_id: str) -> Customer | None:
        orm = await self._session.get(CustomerModel, customer_id)
        return customer_to_domain(orm) if orm else None


class PaymentRepository:
    """Repository for Payment persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, payment: Payment) -> Payment:
        orm = await self._session.get(PaymentModel, payment.payment_id)
        if orm is None:
            orm = payment_to_orm(payment)
            self._session.add(orm)
        else:
            orm.provider_payment_id = payment.provider_payment_id
            orm.status = (
                payment.status.value
                if isinstance(payment.status, PaymentStatus)
                else str(payment.status)
            )
            orm.updated_at = payment.updated_at
            orm.captured_at = payment.captured_at
            orm.failed_at = payment.failed_at
        await self._session.flush()
        return payment_to_domain(orm)

    async def get_by_id(self, payment_id: str) -> Payment | None:
        orm = await self._session.get(PaymentModel, payment_id)
        return payment_to_domain(orm) if orm else None

    async def find_by_provider_payment_id(
        self, provider: str, provider_payment_id: str, for_update: bool = False
    ) -> Payment | None:
        stmt = select(PaymentModel).where(
            PaymentModel.provider == provider,
            PaymentModel.provider_payment_id == provider_payment_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return payment_to_domain(orm) if orm else None

    async def update_status_conditional(
        self, payment: Payment, expected_status: PaymentStatus
    ) -> Payment:
        """Update Payment status conditionally matching expected_status."""
        stmt = (
            select(PaymentModel)
            .where(
                PaymentModel.payment_id == payment.payment_id,
                PaymentModel.status == expected_status.value,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            msg = f"Payment {payment.payment_id} modified or not in {expected_status}."
            raise InvalidStateTransitionError(msg)
        orm.provider_payment_id = payment.provider_payment_id
        orm.status = (
            payment.status.value
            if isinstance(payment.status, PaymentStatus)
            else str(payment.status)
        )
        orm.updated_at = payment.updated_at
        orm.captured_at = payment.captured_at
        orm.failed_at = payment.failed_at
        await self._session.flush()
        return payment_to_domain(orm)


class RawEventRepository:
    """Repository for Raw provider event storage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        raw_event_id: str,
        provider: str,
        provider_event_id: str,
        event_type: str | None,
        received_at: datetime,
        raw_payload: dict[str, Any],
        verification_status: str = "VERIFIED",
    ) -> RawEventModel:
        orm = RawEventModel(
            raw_event_id=raw_event_id,
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            received_at=received_at,
            raw_payload=raw_payload,
            verification_status=verification_status,
        )
        self._session.add(orm)
        await self._session.flush()
        return orm

    async def find_by_provider_event_id(
        self, provider: str, provider_event_id: str
    ) -> RawEventModel | None:
        stmt = select(RawEventModel).where(
            RawEventModel.provider == provider,
            RawEventModel.provider_event_id == provider_event_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class PaymentEventRepository:
    """Repository for canonical PaymentEvent persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: PaymentEvent) -> PaymentEvent:
        orm = payment_event_to_orm(event)
        self._session.add(orm)
        await self._session.flush()
        return payment_event_to_domain(orm)

    async def get_by_id(self, event_id: str) -> PaymentEvent | None:
        orm = await self._session.get(PaymentEventModel, event_id)
        return payment_event_to_domain(orm) if orm else None

    async def find_by_payment_id(self, payment_id: str) -> list[PaymentEvent]:
        stmt = select(PaymentEventModel).where(
            PaymentEventModel.payment_id == payment_id
        )
        result = await self._session.execute(stmt)
        return [payment_event_to_domain(row) for row in result.scalars()]

    async def find_latest_by_payment_id(self, payment_id: str) -> PaymentEvent | None:
        """Find the latest canonical PaymentEvent for a payment by event_timestamp."""
        stmt = (
            select(PaymentEventModel)
            .where(PaymentEventModel.payment_id == payment_id)
            .order_by(
                PaymentEventModel.event_timestamp.desc(),
                PaymentEventModel.received_at.desc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return payment_event_to_domain(orm) if orm else None


class RecoveryCaseRepository:
    """Repository for RecoveryCase persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, case: RecoveryCase) -> RecoveryCase:
        orm = await self._session.get(RecoveryCaseModel, case.case_id)
        if orm is None:
            orm = recovery_case_to_orm(case)
            self._session.add(orm)
        else:
            orm.status = (
                case.status.value
                if isinstance(case.status, RecoveryCaseStatus)
                else str(case.status)
            )
            orm.updated_at = case.updated_at
            orm.closed_at = case.closed_at
            orm.recovery_amount = case.recovery_amount
            orm.current_attempt_count = case.current_attempt_count
            orm.stop_reason = case.stop_reason
            orm.escalation_reason = case.escalation_reason
        await self._session.flush()
        return recovery_case_to_domain(orm)

    async def get_by_id(self, case_id: str) -> RecoveryCase | None:
        orm = await self._session.get(RecoveryCaseModel, case_id)
        return recovery_case_to_domain(orm) if orm else None

    async def find_by_payment_id(self, payment_id: str) -> list[RecoveryCase]:
        stmt = select(RecoveryCaseModel).where(
            RecoveryCaseModel.payment_id == payment_id
        )
        result = await self._session.execute(stmt)
        return [recovery_case_to_domain(row) for row in result.scalars()]

    async def list_by_payment_id(self, payment_id: str) -> list[RecoveryCase]:
        """Alias for find_by_payment_id."""
        return await self.find_by_payment_id(payment_id)

    async def find_active_by_payment_id(
        self, payment_id: str, for_update: bool = False
    ) -> RecoveryCase | None:
        """Find non-terminal active RecoveryCase for a payment."""
        terminal_statuses = [
            RecoveryCaseStatus.RECOVERED.value,
            RecoveryCaseStatus.STOPPED.value,
            RecoveryCaseStatus.ESCALATED.value,
        ]
        stmt = select(RecoveryCaseModel).where(
            RecoveryCaseModel.payment_id == payment_id,
            RecoveryCaseModel.status.notin_(terminal_statuses),
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return recovery_case_to_domain(orm) if orm else None

    async def update_status_conditional(
        self, case: RecoveryCase, expected_status: RecoveryCaseStatus
    ) -> RecoveryCase:
        stmt = (
            select(RecoveryCaseModel)
            .where(
                RecoveryCaseModel.case_id == case.case_id,
                RecoveryCaseModel.status == expected_status.value,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            msg = f"Case {case.case_id} modified or not in state {expected_status}."
            raise InvalidStateTransitionError(msg)
        orm.status = (
            case.status.value
            if isinstance(case.status, RecoveryCaseStatus)
            else str(case.status)
        )
        orm.updated_at = case.updated_at
        orm.closed_at = case.closed_at
        orm.recovery_amount = case.recovery_amount
        orm.current_attempt_count = case.current_attempt_count
        orm.stop_reason = case.stop_reason
        orm.escalation_reason = case.escalation_reason
        await self._session.flush()
        return recovery_case_to_domain(orm)


class RecoveryActionRepository:
    """Repository for RecoveryAction persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, action: RecoveryAction) -> RecoveryAction:
        orm = await self._session.get(RecoveryActionModel, action.action_id)
        if orm is None:
            orm = recovery_action_to_orm(action)
            self._session.add(orm)
        else:
            orm.status = (
                action.status.value
                if isinstance(action.status, RecoveryActionStatus)
                else str(action.status)
            )
            orm.updated_at = action.updated_at
            orm.provider_reference = action.provider_reference
            orm.parameters = action.parameters
        await self._session.flush()
        return recovery_action_to_domain(orm)

    async def get_by_id(self, action_id: str) -> RecoveryAction | None:
        orm = await self._session.get(RecoveryActionModel, action_id)
        return recovery_action_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[RecoveryAction]:
        stmt = select(RecoveryActionModel).where(RecoveryActionModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [recovery_action_to_domain(row) for row in result.scalars()]


class DiagnosisRepository:
    """Repository for Diagnosis persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, diagnosis: Diagnosis) -> Diagnosis:
        orm = diagnosis_to_orm(diagnosis)
        self._session.add(orm)
        await self._session.flush()
        return diagnosis_to_domain(orm)

    async def get_by_id(self, diagnosis_id: str) -> Diagnosis | None:
        orm = await self._session.get(DiagnosisModel, diagnosis_id)
        return diagnosis_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[Diagnosis]:
        stmt = select(DiagnosisModel).where(DiagnosisModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [diagnosis_to_domain(row) for row in result.scalars()]


class ActionEvaluationRepository:
    """Repository for ActionEvaluation persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, evaluation: ActionEvaluation) -> ActionEvaluation:
        orm = action_evaluation_to_orm(evaluation)
        self._session.add(orm)
        await self._session.flush()
        return action_evaluation_to_domain(orm)

    async def get_by_id(self, evaluation_id: str) -> ActionEvaluation | None:
        orm = await self._session.get(ActionEvaluationModel, evaluation_id)
        return action_evaluation_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[ActionEvaluation]:
        stmt = select(ActionEvaluationModel).where(
            ActionEvaluationModel.case_id == case_id
        )
        result = await self._session.execute(stmt)
        return [action_evaluation_to_domain(row) for row in result.scalars()]


class DecisionRepository:
    """Repository for Decision persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, decision: Decision) -> Decision:
        orm = decision_to_orm(decision)
        self._session.add(orm)
        await self._session.flush()
        return decision_to_domain(orm)

    async def get_by_id(self, decision_id: str) -> Decision | None:
        orm = await self._session.get(DecisionModel, decision_id)
        return decision_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[Decision]:
        stmt = select(DecisionModel).where(DecisionModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [decision_to_domain(row) for row in result.scalars()]


class PolicyDecisionRepository:
    """Repository for PolicyDecision persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, policy_decision: PolicyDecision) -> PolicyDecision:
        orm = policy_decision_to_orm(policy_decision)
        self._session.add(orm)
        await self._session.flush()
        return policy_decision_to_domain(orm)

    async def get_by_id(self, policy_decision_id: str) -> PolicyDecision | None:
        orm = await self._session.get(PolicyDecisionModel, policy_decision_id)
        return policy_decision_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[PolicyDecision]:
        stmt = select(PolicyDecisionModel).where(PolicyDecisionModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [policy_decision_to_domain(row) for row in result.scalars()]


class ExecutionRepository:
    """Repository for Execution persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self, execution: Execution, idempotency_key: str | None = None
    ) -> Execution:
        orm = await self._session.get(ExecutionModel, execution.execution_id)
        if orm is None:
            orm = execution_to_orm(execution, idempotency_key=idempotency_key)
            self._session.add(orm)
        else:
            orm.status = (
                execution.status.value
                if hasattr(execution.status, "value")
                else str(execution.status)
            )
            orm.completed_at = execution.completed_at
            orm.error_code = execution.error_code
            orm.error_message = execution.error_message
        await self._session.flush()
        return execution_to_domain(orm)

    async def get_by_id(self, execution_id: str) -> Execution | None:
        orm = await self._session.get(ExecutionModel, execution_id)
        return execution_to_domain(orm) if orm else None

    async def find_by_idempotency_key(self, idempotency_key: str) -> Execution | None:
        stmt = select(ExecutionModel).where(
            ExecutionModel.idempotency_key == idempotency_key
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return execution_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[Execution]:
        stmt = select(ExecutionModel).where(ExecutionModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [execution_to_domain(row) for row in result.scalars()]


class OutcomeRepository:
    """Repository for Outcome persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, outcome: Outcome) -> Outcome:
        orm = outcome_to_orm(outcome)
        self._session.add(orm)
        await self._session.flush()
        return outcome_to_domain(orm)

    async def get_by_id(self, outcome_id: str) -> Outcome | None:
        orm = await self._session.get(OutcomeModel, outcome_id)
        return outcome_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[Outcome]:
        stmt = select(OutcomeModel).where(OutcomeModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [outcome_to_domain(row) for row in result.scalars()]


class AuditEventRepository:
    """Repository for AuditEvent persistence (Append-Only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, audit: AuditEvent) -> AuditEvent:
        orm = audit_event_to_orm(audit)
        self._session.add(orm)
        await self._session.flush()
        return audit_event_to_domain(orm)

    async def get_by_id(self, audit_event_id: str) -> AuditEvent | None:
        orm = await self._session.get(AuditEventModel, audit_event_id)
        return audit_event_to_domain(orm) if orm else None

    async def find_by_case_id(self, case_id: str) -> list[AuditEvent]:
        stmt = select(AuditEventModel).where(AuditEventModel.case_id == case_id)
        result = await self._session.execute(stmt)
        return [audit_event_to_domain(row) for row in result.scalars()]

    async def find_by_correlation_id(self, correlation_id: str) -> list[AuditEvent]:
        stmt = select(AuditEventModel).where(
            AuditEventModel.correlation_id == correlation_id
        )
        result = await self._session.execute(stmt)
        return [audit_event_to_domain(row) for row in result.scalars()]

    async def find_by_trace_id(self, trace_id: str) -> list[AuditEvent]:
        return await self.find_by_correlation_id(trace_id)
