"""Domain <-> ORM model mapping functions for APRO persistence."""

from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
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
    RecoveryActionModel,
    RecoveryCaseModel,
)


def customer_to_orm(domain: Customer) -> CustomerModel:
    return CustomerModel(
        customer_id=domain.customer_id,
        external_reference=domain.external_reference,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        historical_payment_count=domain.historical_payment_count,
        historical_success_count=domain.historical_success_count,
        historical_failure_count=domain.historical_failure_count,
        historical_recovery_count=domain.historical_recovery_count,
    )


def customer_to_domain(orm: CustomerModel) -> Customer:
    return Customer(
        customer_id=orm.customer_id,
        external_reference=orm.external_reference,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        historical_payment_count=orm.historical_payment_count,
        historical_success_count=orm.historical_success_count,
        historical_failure_count=orm.historical_failure_count,
        historical_recovery_count=orm.historical_recovery_count,
    )


def payment_to_orm(domain: Payment) -> PaymentModel:
    return PaymentModel(
        payment_id=domain.payment_id,
        customer_id=domain.customer_id,
        order_id=domain.order_id,
        provider=domain.provider,
        amount=domain.amount,
        currency=domain.currency,
        method=domain.method,
        status=domain.status.value
        if isinstance(domain.status, PaymentStatus)
        else str(domain.status),
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        captured_at=domain.captured_at,
        failed_at=domain.failed_at,
    )


def payment_to_domain(orm: PaymentModel) -> Payment:
    return Payment(
        payment_id=orm.payment_id,
        customer_id=orm.customer_id,
        order_id=orm.order_id,
        provider=orm.provider,
        amount=orm.amount,
        currency=orm.currency,
        method=orm.method,
        status=PaymentStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        captured_at=orm.captured_at,
        failed_at=orm.failed_at,
    )


def payment_event_to_orm(domain: PaymentEvent) -> PaymentEventModel:
    return PaymentEventModel(
        event_id=domain.event_id,
        provider=domain.provider,
        event_type=domain.event_type,
        payment_id=domain.payment_id,
        order_id=domain.order_id,
        amount=domain.amount,
        currency=domain.currency,
        method=domain.method,
        status=domain.status.value
        if isinstance(domain.status, PaymentStatus)
        else str(domain.status),
        failure_code=domain.failure_code,
        failure_source=domain.failure_source,
        failure_step=domain.failure_step,
        failure_reason=domain.failure_reason,
        failure_description=domain.failure_description,
        event_timestamp=domain.event_timestamp,
        received_at=domain.received_at,
        raw_payload_reference=domain.raw_payload_reference,
    )


def payment_event_to_domain(orm: PaymentEventModel) -> PaymentEvent:
    return PaymentEvent(
        event_id=orm.event_id,
        provider=orm.provider,
        event_type=orm.event_type,
        payment_id=orm.payment_id,
        order_id=orm.order_id,
        amount=orm.amount,
        currency=orm.currency,
        method=orm.method,
        status=PaymentStatus(orm.status),
        failure_code=orm.failure_code,
        failure_source=orm.failure_source,
        failure_step=orm.failure_step,
        failure_reason=orm.failure_reason,
        failure_description=orm.failure_description,
        event_timestamp=orm.event_timestamp,
        received_at=orm.received_at,
        raw_payload_reference=orm.raw_payload_reference,
    )


def recovery_case_to_orm(domain: RecoveryCase) -> RecoveryCaseModel:
    return RecoveryCaseModel(
        case_id=domain.case_id,
        payment_id=domain.payment_id,
        customer_id=domain.customer_id,
        status=domain.status.value
        if isinstance(domain.status, RecoveryCaseStatus)
        else str(domain.status),
        opened_at=domain.opened_at,
        updated_at=domain.updated_at,
        closed_at=domain.closed_at,
        recovery_amount=domain.recovery_amount,
        current_attempt_count=domain.current_attempt_count,
        stop_reason=domain.stop_reason,
        escalation_reason=domain.escalation_reason,
    )


def recovery_case_to_domain(orm: RecoveryCaseModel) -> RecoveryCase:
    return RecoveryCase(
        case_id=orm.case_id,
        payment_id=orm.payment_id,
        customer_id=orm.customer_id,
        status=RecoveryCaseStatus(orm.status),
        opened_at=orm.opened_at,
        updated_at=orm.updated_at,
        closed_at=orm.closed_at,
        recovery_amount=orm.recovery_amount,
        current_attempt_count=orm.current_attempt_count,
        stop_reason=orm.stop_reason,
        escalation_reason=orm.escalation_reason,
    )


def recovery_action_to_orm(domain: RecoveryAction) -> RecoveryActionModel:
    mode_val = (
        domain.execution_mode.value
        if isinstance(domain.execution_mode, ExecutionMode)
        else domain.execution_mode
    )
    return RecoveryActionModel(
        action_id=domain.action_id,
        case_id=domain.case_id,
        action_type=domain.action_type.value
        if isinstance(domain.action_type, RecoveryActionType)
        else str(domain.action_type),
        status=domain.status.value
        if isinstance(domain.status, RecoveryActionStatus)
        else str(domain.status),
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        provider_reference=domain.provider_reference,
        execution_mode=mode_val,
        parameters=domain.parameters,
    )


def recovery_action_to_domain(orm: RecoveryActionModel) -> RecoveryAction:
    mode_obj = ExecutionMode(orm.execution_mode) if orm.execution_mode else None
    return RecoveryAction(
        action_id=orm.action_id,
        case_id=orm.case_id,
        action_type=RecoveryActionType(orm.action_type),
        status=RecoveryActionStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        provider_reference=orm.provider_reference,
        execution_mode=mode_obj,
        parameters=orm.parameters,
    )


def diagnosis_to_orm(domain: Diagnosis) -> DiagnosisModel:
    return DiagnosisModel(
        diagnosis_id=domain.diagnosis_id,
        case_id=domain.case_id,
        category=domain.category.value
        if isinstance(domain.category, FailureCategory)
        else str(domain.category),
        confidence=domain.confidence,
        evidence=list(domain.evidence),
        model_name=domain.model_name,
        model_version=domain.model_version,
        created_at=domain.created_at,
    )


def diagnosis_to_domain(orm: DiagnosisModel) -> Diagnosis:
    return Diagnosis(
        diagnosis_id=orm.diagnosis_id,
        case_id=orm.case_id,
        category=FailureCategory(orm.category),
        confidence=orm.confidence,
        evidence=tuple(orm.evidence),
        model_name=orm.model_name,
        model_version=orm.model_version,
        created_at=orm.created_at,
    )


def action_evaluation_to_orm(domain: ActionEvaluation) -> ActionEvaluationModel:
    return ActionEvaluationModel(
        evaluation_id=domain.evaluation_id,
        case_id=domain.case_id,
        action_type=domain.action_type.value
        if isinstance(domain.action_type, RecoveryActionType)
        else str(domain.action_type),
        success_probability=domain.success_probability,
        recoverable_amount=domain.recoverable_amount,
        action_cost=domain.action_cost,
        expected_recovery_value=domain.expected_recovery_value,
        model_name=domain.model_name,
        model_version=domain.model_version,
        created_at=domain.created_at,
    )


def action_evaluation_to_domain(orm: ActionEvaluationModel) -> ActionEvaluation:
    return ActionEvaluation(
        evaluation_id=orm.evaluation_id,
        case_id=orm.case_id,
        action_type=RecoveryActionType(orm.action_type),
        success_probability=orm.success_probability,
        recoverable_amount=orm.recoverable_amount,
        action_cost=orm.action_cost,
        expected_recovery_value=orm.expected_recovery_value,
        model_name=orm.model_name,
        model_version=orm.model_version,
        created_at=orm.created_at,
    )


def decision_to_orm(domain: Decision) -> DecisionModel:
    return DecisionModel(
        decision_id=domain.decision_id,
        case_id=domain.case_id,
        recommended_action=domain.recommended_action.value
        if isinstance(domain.recommended_action, RecoveryActionType)
        else str(domain.recommended_action),
        confidence=domain.confidence,
        expected_recovery_value=domain.expected_recovery_value,
        reason=domain.reason,
        model_name=domain.model_name,
        model_version=domain.model_version,
        created_at=domain.created_at,
    )


def decision_to_domain(orm: DecisionModel) -> Decision:
    return Decision(
        decision_id=orm.decision_id,
        case_id=orm.case_id,
        recommended_action=RecoveryActionType(orm.recommended_action),
        confidence=orm.confidence,
        expected_recovery_value=orm.expected_recovery_value,
        reason=orm.reason,
        model_name=orm.model_name,
        model_version=orm.model_version,
        created_at=orm.created_at,
    )


def policy_decision_to_orm(domain: PolicyDecision) -> PolicyDecisionModel:
    return PolicyDecisionModel(
        policy_decision_id=domain.policy_decision_id,
        decision_id=domain.decision_id,
        case_id=domain.case_id,
        result=domain.result.value
        if isinstance(domain.result, PolicyDecisionResult)
        else str(domain.result),
        reason=domain.reason,
        policy_version=domain.policy_version,
        created_at=domain.created_at,
    )


def policy_decision_to_domain(orm: PolicyDecisionModel) -> PolicyDecision:
    return PolicyDecision(
        policy_decision_id=orm.policy_decision_id,
        decision_id=orm.decision_id,
        case_id=orm.case_id,
        result=PolicyDecisionResult(orm.result),
        reason=orm.reason,
        policy_version=orm.policy_version,
        created_at=orm.created_at,
    )


def execution_to_orm(
    domain: Execution, idempotency_key: str | None = None
) -> ExecutionModel:
    mode_val = (
        domain.execution_mode.value
        if isinstance(domain.execution_mode, ExecutionMode)
        else domain.execution_mode
    )
    status_val = (
        domain.status.value
        if isinstance(domain.status, ExecutionStatus)
        else str(domain.status)
    )
    return ExecutionModel(
        execution_id=domain.execution_id,
        action_id=domain.action_id,
        case_id=domain.case_id,
        execution_type=domain.execution_type,
        execution_mode=mode_val,
        status=status_val,
        provider_reference=domain.provider_reference,
        idempotency_key=idempotency_key,
        started_at=domain.started_at,
        completed_at=domain.completed_at,
        error_code=domain.error_code,
        error_message=domain.error_message,
    )


def execution_to_domain(orm: ExecutionModel) -> Execution:
    return Execution(
        execution_id=orm.execution_id,
        action_id=orm.action_id,
        case_id=orm.case_id,
        execution_type=orm.execution_type,
        execution_mode=ExecutionMode(orm.execution_mode),
        status=ExecutionStatus(orm.status),
        provider_reference=orm.provider_reference,
        started_at=orm.started_at,
        completed_at=orm.completed_at,
        error_code=orm.error_code,
        error_message=orm.error_message,
    )


def outcome_to_orm(domain: Outcome) -> OutcomeModel:
    type_val = (
        domain.type.value if isinstance(domain.type, OutcomeType) else str(domain.type)
    )
    return OutcomeModel(
        outcome_id=domain.outcome_id,
        case_id=domain.case_id,
        execution_id=domain.execution_id,
        type=type_val,
        amount_recovered=domain.amount_recovered,
        evidence_reference=domain.evidence_reference,
        observed_at=domain.observed_at,
    )


def outcome_to_domain(orm: OutcomeModel) -> Outcome:
    return Outcome(
        outcome_id=orm.outcome_id,
        case_id=orm.case_id,
        execution_id=orm.execution_id,
        type=OutcomeType(orm.type),
        amount_recovered=orm.amount_recovered,
        evidence_reference=orm.evidence_reference,
        observed_at=orm.observed_at,
    )


def audit_event_to_orm(domain: AuditEvent) -> AuditEventModel:
    actor_val = (
        domain.actor.value
        if isinstance(domain.actor, AuditActor)
        else str(domain.actor)
    )
    return AuditEventModel(
        audit_event_id=domain.audit_event_id,
        case_id=domain.case_id,
        event_type=domain.event_type,
        actor=actor_val,
        timestamp=domain.timestamp,
        payload=domain.payload,
        correlation_id=domain.correlation_id,
    )


def audit_event_to_domain(orm: AuditEventModel) -> AuditEvent:
    return AuditEvent(
        audit_event_id=orm.audit_event_id,
        case_id=orm.case_id,
        event_type=orm.event_type,
        actor=AuditActor(orm.actor),
        timestamp=orm.timestamp,
        payload=orm.payload,
        correlation_id=orm.correlation_id,
    )
