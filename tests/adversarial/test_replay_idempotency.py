"""Tests for Scenario 3: Duplicate and Replay Storm Idempotency."""

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select

from apro.adversarial.assertions import assert_exactly_once_advancement
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_replay_storm_cases
from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    Customer,
    Execution,
    Payment,
    RecoveryAction,
    RecoveryCase,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.persistence.models import OutcomeModel
from apro.persistence.unit_of_work import UnitOfWork
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_loop.enums import EvidenceProvenance, EvidenceType
from apro.recovery_loop.models import OutcomeEvidence
from apro.recovery_loop.outcomes import OutcomeProcessor
from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction


@pytest.mark.asyncio
async def test_scenario_3_replay_storm_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 3: Sequential replay storm cases are safely handled by idempotency layer."""
    cases = generate_replay_storm_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.CONTAINED


@pytest.mark.asyncio
async def test_scenario_3_concurrent_50_replay_storm(
    attack_db_session_factory: Any,
) -> None:
    """Scenario 3 (Amendment 5): 50+ concurrent replays produce exactly 1 provider execution and 1 persisted semantic outcome."""
    import uuid

    now = datetime.now(UTC)
    idem_key = "storm_concurrent_key_50"

    cust_id = str(uuid.uuid4())
    pay_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    action_id = str(uuid.uuid4())
    policy_dec_id = str(uuid.uuid4())
    decision_id = str(uuid.uuid4())

    policy_dec = PolicyDecision(
        policy_decision_id=policy_dec_id,
        case_id=case_id,
        payment_id=pay_id,
        decision_id=decision_id,
        requested_action=PredictRecoveryAction.RETRY,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictRecoveryAction.RETRY,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Concurrent replay storm test",
        idempotency_key=idem_key,
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )

    recovery_action = RecoveryAction(
        action_id=action_id,
        case_id=case_id,
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    recovery_case = RecoveryCase(
        case_id=case_id,
        payment_id=pay_id,
        customer_id=cust_id,
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )

    payment = Payment(
        payment_id=pay_id,
        customer_id=cust_id,
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    from apro.execution.executors.retry import SimulationRetryExecutor
    from apro.execution.models import ApprovedExecutionRequest, ExecutionResult
    from apro.execution.registry import ExecutorRegistry

    class CountingSimulationRetryExecutor(SimulationRetryExecutor):
        def __init__(self) -> None:
            super().__init__()
            self.dispatch_count = 0

        async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
            self.dispatch_count += 1
            return await super().execute(request)

    counting_executor = CountingSimulationRetryExecutor()
    reg = ExecutorRegistry()
    reg.register(counting_executor)
    orchestrator = ExecutionOrchestrator(registry=reg)

    # Launch 50 concurrent executions with identical idempotency key
    async def run_one() -> Any:
        return await orchestrator.execute(
            policy_decision=policy_dec,
            recovery_action=recovery_action,
            recovery_case=recovery_case,
            payment=payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
        )

    results = await asyncio.gather(*[run_one() for _ in range(50)])

    exec_id = results[0].execution_id
    customer = Customer(
        customer_id=recovery_case.customer_id,
        email="test_storm@example.com",
        phone="+919876543210",
        name="Storm Customer",
        created_at=now,
        updated_at=now,
    )
    execution = Execution(
        execution_id=exec_id,
        action_id=recovery_action.action_id,
        case_id=recovery_case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )

    # Persist baseline entities (case in OBSERVING status post-execution)
    async with UnitOfWork(attack_db_session_factory) as uow:
        await uow.customers.save(customer)
        await uow.payments.save(payment)
        await uow.recovery_cases.save(
            recovery_case.model_copy(update={"status": RecoveryCaseStatus.OBSERVING})
        )
        await uow.recovery_actions.save(recovery_action)
        await uow.executions.save(execution)
        await uow.commit()

    outcome_processor = OutcomeProcessor()
    for r in results:
        async with UnitOfWork(attack_db_session_factory) as uow:
            loaded_case = await uow.recovery_cases.get_by_id(recovery_case.case_id)
            loaded_payment = await uow.payments.get_by_id(payment.payment_id)
            ev = OutcomeEvidence(
                evidence_id=f"ev_{r.execution_id}",
                case_id=recovery_case.case_id,
                execution_id=r.execution_id,
                evidence_type=EvidenceType.EXECUTION_RESULT,
                payment_status=payment.status,
                observed_at=now,
                provenance=EvidenceProvenance.SIMULATOR,
                raw_details={"status": "failed"},
            )
            if loaded_case and loaded_payment:
                await outcome_processor.process_outcome(
                    evidence=ev,
                    case=loaded_case,
                    payment=loaded_payment,
                    execution=execution,
                    uow=uow,
                )
                await uow.commit()

    # Query PostgreSQL attack database for actual persisted outcomes
    async with UnitOfWork(attack_db_session_factory) as uow:
        stmt = select(OutcomeModel).where(OutcomeModel.case_id == recovery_case.case_id)
        db_res = await uow.session.execute(stmt)
        persisted_outcomes = list(db_res.scalars())

    # Measured counters from real concurrent execution path & PostgreSQL persistence
    replay_attempt_count = len(results)
    authoritative_execution_count = len({r.execution_id for r in results})
    provider_simulator_side_effect_count = counting_executor.dispatch_count
    persisted_semantic_outcome_count = len(persisted_outcomes)
    duplicate_persisted_advancement_count = max(0, persisted_semantic_outcome_count - 1)

    assert replay_attempt_count == 50
    assert authoritative_execution_count == 1
    assert provider_simulator_side_effect_count == 1
    assert persisted_semantic_outcome_count == 1
    assert duplicate_persisted_advancement_count == 0

    # Invariant helper check with measured counters
    assert_exactly_once_advancement(
        replay_attempt_count=replay_attempt_count,
        authoritative_execution_count=authoritative_execution_count,
        provider_simulator_side_effect_count=provider_simulator_side_effect_count,
        persisted_semantic_outcome_count=persisted_semantic_outcome_count,
        duplicate_persisted_advancement_count=duplicate_persisted_advancement_count,
    )
