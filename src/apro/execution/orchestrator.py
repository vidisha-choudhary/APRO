"""Execution Orchestrator coordinating authorization, gates, and dispatch."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionStatus,
    RecoveryCaseStatus,
)
from apro.domain.models import Execution, Payment, RecoveryAction, RecoveryCase
from apro.domain.state_machines import (
    transition_execution,
    transition_recovery_action,
    transition_recovery_case,
)
from apro.execution.exceptions import (
    ExecutionStateError,
    IdempotencyConflictError,
)
from apro.execution.interfaces import BaseExecutor
from apro.execution.models import (
    ExecutionResult,
)
from apro.execution.registry import DEFAULT_EXECUTOR_REGISTRY, ExecutorRegistry
from apro.execution.validation import (
    build_approved_execution_request,
    validate_execution_preconditions,
    validate_policy_authorization,
)
from apro.persistence.models import ExecutionModel
from apro.persistence.unit_of_work import UnitOfWork
from apro.policy.models import PolicyDecision
from apro.policy.state_guard import StateGuard


class ExecutionOrchestrator:
    """Orchestrates bounded, authorized recovery action execution.

    Durable multi-worker idempotency requires passing a PostgreSQL-backed
    `UnitOfWork`. When `unit_of_work=None` is used (in-process / unit tests),
    in-memory locking guarantees at-most-one dispatch for concurrent coroutines.
    """

    def __init__(
        self,
        registry: ExecutorRegistry | None = None,
        audit_service: Any | None = None,
    ) -> None:
        self.registry = registry or DEFAULT_EXECUTOR_REGISTRY
        self.audit_service = audit_service
        self._in_memory_idempotency: dict[str, ExecutionResult] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pre_gate_hook: Callable[[], Any] | None = None

    def _get_lock(self, idempotency_key: str) -> asyncio.Lock:
        if idempotency_key not in self._locks:
            self._locks[idempotency_key] = asyncio.Lock()
        return self._locks[idempotency_key]

    @staticmethod
    def _reconstruct_result(
        existing_orm: Execution | ExecutionModel, executor: BaseExecutor
    ) -> ExecutionResult:
        status = (
            ExecutionStatus(existing_orm.status)
            if hasattr(existing_orm.status, "value")
            or isinstance(existing_orm.status, str)
            else existing_orm.status
        )
        mode = (
            ExecutionMode(existing_orm.execution_mode)
            if hasattr(existing_orm.execution_mode, "value")
            or isinstance(existing_orm.execution_mode, str)
            else existing_orm.execution_mode
        )
        return ExecutionResult(
            execution_id=existing_orm.execution_id,
            action_id=existing_orm.action_id,
            case_id=existing_orm.case_id,
            status=status,
            execution_mode=mode,
            provider_reference=existing_orm.provider_reference,
            error_code=existing_orm.error_code,
            error_message=existing_orm.error_message,
            started_at=existing_orm.started_at,
            completed_at=existing_orm.completed_at,
            executor_name=type(executor).__name__,
            metadata={"reused_existing_execution": True},
        )

    async def execute(
        self,
        policy_decision: PolicyDecision,
        recovery_action: RecoveryAction,
        recovery_case: RecoveryCase,
        payment: Payment,
        execution_mode: ExecutionMode,
        current_time: datetime | None = None,
        parameters: dict[str, Any] | None = None,
        unit_of_work: UnitOfWork | None = None,
    ) -> ExecutionResult:
        """Validate, guard, and execute an authorized recovery action."""
        now = current_time or datetime.now(UTC)

        # 1. Authoritative Phase 10 Policy Authorization Gate
        validate_policy_authorization(
            policy_decision=policy_decision,
            action=recovery_action,
            case=recovery_case,
            payment=payment,
        )

        # 2. Precondition Validation (Parameters, States, Secrets)
        validate_execution_preconditions(
            action=recovery_action,
            case=recovery_case,
            payment=payment,
            execution_mode=execution_mode,
            parameters=parameters,
        )

        # 3. Resolve Executor from Registry (Fails closed if missing/unsupported)
        executor = self.registry.get(recovery_action.action_type, execution_mode)

        # 4. Construct Immutable Execution Request
        request = build_approved_execution_request(
            policy_decision=policy_decision,
            action=recovery_action,
            case=recovery_case,
            execution_mode=execution_mode,
            current_time=now,
            parameters=parameters,
        )

        # 5. Pre-Dispatch Validation (Must run before claim/transition)
        executor.validate(request)

        # 6. Branch between Durable PostgreSQL and In-Process Execution
        if unit_of_work is not None:
            return await self._execute_durable_uow(
                request=request,
                policy_decision=policy_decision,
                recovery_action=recovery_action,
                recovery_case=recovery_case,
                payment=payment,
                executor=executor,
                unit_of_work=unit_of_work,
                now=now,
            )

        # In-process: Hold lock across lifecycle for at-most-one dispatch
        async with self._get_lock(request.idempotency_key):
            if request.idempotency_key in self._in_memory_idempotency:
                return self._in_memory_idempotency[request.idempotency_key]

            result = await self._execute_in_memory(
                request=request,
                policy_decision=policy_decision,
                recovery_action=recovery_action,
                recovery_case=recovery_case,
                payment=payment,
                executor=executor,
                now=now,
            )
            self._in_memory_idempotency[request.idempotency_key] = result
            return result

    async def _execute_durable_uow(
        self,
        request: Any,
        policy_decision: PolicyDecision,
        recovery_action: RecoveryAction,
        recovery_case: RecoveryCase,
        payment: Payment,
        executor: BaseExecutor,
        unit_of_work: UnitOfWork,
        now: datetime,
    ) -> ExecutionResult:
        """Execute with durable PostgreSQL concurrency and idempotency guarantees."""
        domain_execution = Execution(
            execution_id=request.execution_id,
            action_id=request.action_id,
            case_id=request.case_id,
            execution_type=request.action_type.value,
            execution_mode=request.execution_mode,
            status=ExecutionStatus.PENDING,
            started_at=now,
        )

        # Idempotency claim attempt
        existing = await unit_of_work.executions.find_by_idempotency_key(
            request.idempotency_key
        )
        if existing is not None:
            if (
                existing.case_id != request.case_id
                or existing.action_id != request.action_id
            ):
                msg = (
                    f"Idempotency conflict: key '{request.idempotency_key}' "
                    f"already associated with case '{existing.case_id}' "
                    f"and action '{existing.action_id}'."
                )
                raise IdempotencyConflictError(msg)
            return self._reconstruct_result(existing, executor)

        try:
            await unit_of_work.executions.save(
                domain_execution, idempotency_key=request.idempotency_key
            )
            await unit_of_work.flush()
        except Exception:
            await unit_of_work.rollback()
            existing_after = await unit_of_work.executions.find_by_idempotency_key(
                request.idempotency_key
            )
            if existing_after is not None:
                return self._reconstruct_result(existing_after, executor)
            raise

        # Pre-gate hook for dynamic testing
        if self._pre_gate_hook is not None:
            if asyncio.iscoroutinefunction(self._pre_gate_hook):
                await self._pre_gate_hook()
            else:
                self._pre_gate_hook()

        # Final Pre-Execution State Recheck Gate
        assert policy_decision.effective_action is not None
        allowed, reason_code, reason_detail = StateGuard.recheck_current_state(
            payment, policy_decision.effective_action
        )
        if not allowed:
            r_val = reason_code.value if reason_code else "RECHECK_FAILED"
            msg = f"Final state recheck rejected dispatch: {reason_detail} ({r_val})"
            cancelled_exec = transition_execution(
                domain_execution, ExecutionStatus.CANCELLED, now=now
            )
            await unit_of_work.executions.save(
                cancelled_exec, idempotency_key=request.idempotency_key
            )
            await unit_of_work.commit()
            raise ExecutionStateError(msg)

        # Lifecycle Transitions -> EXECUTING / RUNNING
        current_action = transition_recovery_action(
            recovery_action, RecoveryActionStatus.EXECUTING, now=now
        )
        current_execution = transition_execution(
            domain_execution, ExecutionStatus.RUNNING, now=now
        )
        current_case = self._transition_case_to_executing(recovery_case, payment, now)

        await unit_of_work.recovery_actions.save(current_action)
        await unit_of_work.recovery_cases.save(current_case)
        await unit_of_work.executions.save(
            current_execution, idempotency_key=request.idempotency_key
        )
        if self.audit_service is not None:
            await self.audit_service.record_execution_started(
                current_execution, uow=unit_of_work
            )
        await unit_of_work.flush()

        # Dispatch
        result = await executor.execute(request)

        # Post-Execution Transitions & Commit
        current_action, current_execution, current_case = (
            self._apply_post_execution_transitions(
                result=result,
                request=request,
                current_action=current_action,
                current_execution=current_execution,
                current_case=current_case,
                payment=payment,
                now=now,
            )
        )

        await unit_of_work.recovery_actions.save(current_action)
        await unit_of_work.recovery_cases.save(current_case)
        await unit_of_work.executions.save(
            current_execution, idempotency_key=request.idempotency_key
        )
        if self.audit_service is not None:
            await self.audit_service.record_execution_completed(
                current_execution, uow=unit_of_work
            )
        await unit_of_work.commit()

        return result

    async def _execute_in_memory(
        self,
        request: Any,
        policy_decision: PolicyDecision,
        recovery_action: RecoveryAction,
        recovery_case: RecoveryCase,
        payment: Payment,
        executor: BaseExecutor,
        now: datetime,
    ) -> ExecutionResult:
        """Execute in-process with per-key locked lifecycle guarantees."""
        domain_execution = Execution(
            execution_id=request.execution_id,
            action_id=request.action_id,
            case_id=request.case_id,
            execution_type=request.action_type.value,
            execution_mode=request.execution_mode,
            status=ExecutionStatus.PENDING,
            started_at=now,
        )

        # Pre-gate hook
        if self._pre_gate_hook is not None:
            if asyncio.iscoroutinefunction(self._pre_gate_hook):
                await self._pre_gate_hook()
            else:
                self._pre_gate_hook()

        # Final Pre-Execution State Recheck Gate
        assert policy_decision.effective_action is not None
        allowed, reason_code, reason_detail = StateGuard.recheck_current_state(
            payment, policy_decision.effective_action
        )
        if not allowed:
            r_val = reason_code.value if reason_code else "RECHECK_FAILED"
            msg = f"Final state recheck rejected dispatch: {reason_detail} ({r_val})"
            raise ExecutionStateError(msg)

        # Lifecycle Transitions -> EXECUTING / RUNNING
        current_action = transition_recovery_action(
            recovery_action, RecoveryActionStatus.EXECUTING, now=now
        )
        current_execution = transition_execution(
            domain_execution, ExecutionStatus.RUNNING, now=now
        )
        current_case = self._transition_case_to_executing(recovery_case, payment, now)

        # Dispatch
        result = await executor.execute(request)

        # Post-Execution Transitions
        self._apply_post_execution_transitions(
            result=result,
            request=request,
            current_action=current_action,
            current_execution=current_execution,
            current_case=current_case,
            payment=payment,
            now=now,
        )

        return result

    @staticmethod
    def _transition_case_to_executing(
        case: RecoveryCase, payment: Payment, now: datetime
    ) -> RecoveryCase:
        if case.status == RecoveryCaseStatus.POLICY_CHECK:
            case = transition_recovery_case(
                case, payment, RecoveryCaseStatus.ACTION_APPROVED, now=now
            )
            return transition_recovery_case(
                case, payment, RecoveryCaseStatus.EXECUTING, now=now
            )
        if case.status == RecoveryCaseStatus.ACTION_APPROVED:
            return transition_recovery_case(
                case, payment, RecoveryCaseStatus.EXECUTING, now=now
            )
        return case

    @staticmethod
    def _apply_post_execution_transitions(
        result: ExecutionResult,
        request: Any,
        current_action: RecoveryAction,
        current_execution: Execution,
        current_case: RecoveryCase,
        payment: Payment,
        now: datetime,
    ) -> tuple[RecoveryAction, Execution, RecoveryCase]:
        if result.status == ExecutionStatus.SUCCEEDED:
            current_action = transition_recovery_action(
                current_action, RecoveryActionStatus.COMPLETED, now=now
            )
            current_execution = transition_execution(
                current_execution, ExecutionStatus.SUCCEEDED, now=now
            )
            if request.action_type == request.action_type.STOP:
                current_case = transition_recovery_case(
                    current_case, payment, RecoveryCaseStatus.STOPPED, now=now
                )
            elif request.action_type == request.action_type.ESCALATE:
                current_case = transition_recovery_case(
                    current_case,
                    payment,
                    RecoveryCaseStatus.ESCALATED,
                    now=now,
                )
            else:
                current_case = transition_recovery_case(
                    current_case,
                    payment,
                    RecoveryCaseStatus.OBSERVING,
                    now=now,
                )
        elif result.status == ExecutionStatus.FAILED:
            current_action = transition_recovery_action(
                current_action, RecoveryActionStatus.FAILED, now=now
            )
            current_execution = transition_execution(
                current_execution, ExecutionStatus.FAILED, now=now
            )
        elif result.status == ExecutionStatus.UNKNOWN:
            current_execution = transition_execution(
                current_execution, ExecutionStatus.UNKNOWN, now=now
            )
        elif result.status == ExecutionStatus.CANCELLED:
            current_action = transition_recovery_action(
                current_action, RecoveryActionStatus.CANCELLED, now=now
            )
            current_execution = transition_execution(
                current_execution, ExecutionStatus.CANCELLED, now=now
            )

        current_execution = current_execution.model_copy(
            update={
                "provider_reference": result.provider_reference,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "completed_at": result.completed_at or now,
            }
        )
        return current_action, current_execution, current_case

    async def cancel_execution(
        self,
        recovery_action: RecoveryAction,
        execution: Execution,
        current_time: datetime | None = None,
        unit_of_work: UnitOfWork | None = None,
    ) -> tuple[RecoveryAction, Execution]:
        """Explicitly cancel an execution and its associated recovery action."""
        now = current_time or datetime.now(UTC)
        cancelled_action = transition_recovery_action(
            recovery_action, RecoveryActionStatus.CANCELLED, now=now
        )
        cancelled_execution = transition_execution(
            execution, ExecutionStatus.CANCELLED, now=now
        )

        if unit_of_work is not None:
            await unit_of_work.recovery_actions.save(cancelled_action)
            await unit_of_work.executions.save(cancelled_execution)
            await unit_of_work.commit()

        return cancelled_action, cancelled_execution


__all__ = ["ExecutionOrchestrator"]
