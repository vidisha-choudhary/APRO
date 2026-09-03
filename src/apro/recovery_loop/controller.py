"""Recovery loop controller orchestrating adaptive feedback loops in Phase 13."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from apro.dataset.models import ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.models import RecoveryDecision
from apro.diagnosis.models import DiagnosisResult
from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Execution, Payment, RecoveryAction, RecoveryCase
from apro.domain.state_machines import transition_recovery_case
from apro.execution.models import ExecutionResult
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.persistence.unit_of_work import UnitOfWork
from apro.policy.engine import PolicyEngine
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import EventTrustState
from apro.recovery_loop.context import ReEvaluationContextBuilder
from apro.recovery_loop.dispositions import DispositionResolver
from apro.recovery_loop.enums import (
    LoopTerminationReason,
    RecoveryLoopDisposition,
)
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.history import ActionHistoryService
from apro.recovery_loop.models import (
    ActionHistoryRecord,
    AdaptiveCycleResult,
    OutcomeEvidence,
    OutcomeProcessingResult,
)
from apro.recovery_loop.outcomes import OutcomeProcessor
from apro.recovery_prediction.enums import RecoveryAction as PredictorAction
from apro.recovery_prediction.models import OutcomePrediction


class RecoveryLoopController:
    """Orchestrates post-execution outcome processing and adaptive re-evaluation cycles.

    Invariant: Phase 13 decides whether a new decision cycle should happen.
    Phase 13 does NOT select recovery actions or override Phase 9 / Phase 10 / Phase 11.
    """

    def __init__(
        self,
        outcome_processor: OutcomeProcessor | None = None,
        disposition_resolver: DispositionResolver | None = None,
        history_service: ActionHistoryService | None = None,
        context_builder: ReEvaluationContextBuilder | None = None,
        safety_guard: LoopSafetyGuard | None = None,
    ) -> None:
        self.safety_guard = safety_guard or LoopSafetyGuard()
        self.history_service = history_service or ActionHistoryService()
        self.disposition_resolver = disposition_resolver or DispositionResolver(
            self.safety_guard
        )
        self.outcome_processor = outcome_processor or OutcomeProcessor(
            disposition_resolver=self.disposition_resolver,
            history_service=self.history_service,
            safety_guard=self.safety_guard,
        )
        self.context_builder = context_builder or ReEvaluationContextBuilder()
        self._locks: dict[str, asyncio.Lock] = {}
        self._in_memory_history: dict[str, list[ActionHistoryRecord]] = {}

    def _get_lock(self, case_id: str) -> asyncio.Lock:
        if case_id not in self._locks:
            self._locks[case_id] = asyncio.Lock()
        return self._locks[case_id]

    async def handle_outcome_and_cycle(
        self,
        evidence: OutcomeEvidence,
        case: RecoveryCase,
        payment: Payment,
        base_model_input: ModelInputRecord,
        execution: Execution | None = None,
        diagnosis_provider: Callable[[ModelInputRecord], DiagnosisResult | None]
        | None = None,
        predictions_provider: Callable[
            [ModelInputRecord, DiagnosisResult | None],
            dict[PredictorAction, OutcomePrediction],
        ]
        | None = None,
        decision_engine: EconomicDecisionEngine | None = None,
        policy_engine: PolicyEngine | None = None,
        execution_orchestrator: ExecutionOrchestrator | None = None,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
        cycle_number: int = 1,
        now: datetime | None = None,
        uow: UnitOfWork | None = None,
        execution_parameters: dict[str, Any] | None = None,
    ) -> tuple[AdaptiveCycleResult, RecoveryCase, Payment]:
        """Process an outcome and, if disposition is RE_EVALUATE, coordinate
        the downstream decision chain.

        Returns:
            (cycle_result, updated_case, updated_payment)
        """
        lock = self._get_lock(case.case_id)
        async with lock:
            current_time = now or datetime.now(UTC)

            # Step 1: Process Outcome
            (
                outcome_res,
                updated_case,
                updated_payment,
            ) = await self.outcome_processor.process_outcome(
                evidence=evidence,
                case=case,
                payment=payment,
                execution=execution,
                cycle_number=cycle_number,
                now=current_time,
                uow=uow,
            )

            # Record prior action/outcome into in-memory history accumulator
            # if uow is None
            if uow is None and execution is not None:
                hist_list = self._in_memory_history.setdefault(updated_case.case_id, [])
                if not any(r.execution_id == execution.execution_id for r in hist_list):
                    act_type_str = str(execution.execution_type)
                    mapped_type = (
                        RecoveryActionType.ALTERNATE_RECOVERY
                        if act_type_str in ("PAYMENT_LINK", "ALTERNATE_RECOVERY")
                        else (
                            RecoveryActionType(act_type_str)
                            if act_type_str in [e.value for e in RecoveryActionType]
                            else RecoveryActionType.RETRY
                        )
                    )
                    record = ActionHistoryRecord(
                        action_id=execution.action_id,
                        action_type=mapped_type,
                        execution_id=execution.execution_id,
                        execution_status=execution.status,
                        outcome_type=outcome_res.outcome.type,
                        amount_recovered=outcome_res.outcome.amount_recovered,
                        observed_at=outcome_res.outcome.observed_at,
                        attempt_order=len(hist_list) + 1,
                        provider_reference=execution.provider_reference,
                    )
                    hist_list.append(record)

            # If disposition is not RE_EVALUATE, return without new action
            if outcome_res.disposition != RecoveryLoopDisposition.RE_EVALUATE:
                res = AdaptiveCycleResult(
                    cycle_number=cycle_number,
                    re_evaluation_id=None,
                    outcome_result=outcome_res,
                    decision=None,
                    policy_decision=None,
                    execution_result=None,
                )
                return res, updated_case, updated_payment

            # Step 2: Next cycle setup
            next_cycle = cycle_number + 1

            # Query authoritative history
            if uow is not None:
                history = await self.history_service.get_case_history(
                    updated_case.case_id, uow
                )
            else:
                history = tuple(self._in_memory_history.get(updated_case.case_id, []))

            # Build fresh observable context
            context = self.context_builder.build_context(
                case=updated_case,
                payment=updated_payment,
                cycle_number=next_cycle,
                history=history,
                latest_diagnosis=None,
                latest_outcome=outcome_res.outcome,
                base_model_input=base_model_input,
                now=current_time,
            )

            # If re-evaluation components are not supplied, return context info
            if (
                decision_engine is None
                or policy_engine is None
                or execution_orchestrator is None
                or predictions_provider is None
            ):
                updated_outcome_res = OutcomeProcessingResult(
                    outcome=outcome_res.outcome,
                    disposition=outcome_res.disposition,
                    case_status=updated_case.status,
                    re_evaluation_id=context.re_evaluation_id,
                    termination_reason=outcome_res.termination_reason,
                    cycle_number=cycle_number,
                    provenance=outcome_res.provenance,
                )
                res = AdaptiveCycleResult(
                    cycle_number=next_cycle,
                    re_evaluation_id=context.re_evaluation_id,
                    outcome_result=updated_outcome_res,
                    decision=None,
                    policy_decision=None,
                    execution_result=None,
                )
                return res, updated_case, updated_payment

            # Step 3: Diagnosis (Phase 7)
            diag_result: DiagnosisResult | None = None
            if diagnosis_provider is not None:
                diag_result = diagnosis_provider(context.model_input)

            # Step 4: Outcome Predictions (Phase 8)
            predictions = predictions_provider(context.model_input, diag_result)

            # Step 5: Economic Decision (Phase 9 - Sole Action Selection Authority)
            decision: RecoveryDecision = decision_engine.decide(
                model_input=context.model_input,
                diagnosis_result=diag_result,
                outcome_predictions=predictions,
                recovery_case_id=updated_case.case_id,
            )

            # Advance case through state machine for decision cycle
            if updated_case.status == RecoveryCaseStatus.EVALUATING:
                updated_case = transition_recovery_case(
                    case=updated_case,
                    payment=updated_payment,
                    new_status=RecoveryCaseStatus.DECISION_PENDING,
                    now=current_time,
                )
                updated_case = transition_recovery_case(
                    case=updated_case,
                    payment=updated_payment,
                    new_status=RecoveryCaseStatus.POLICY_CHECK,
                    now=current_time,
                )

            # Step 6: Policy & Safety Governance (Phase 10 - Authorization Authority)
            policy_history = self.history_service.build_policy_execution_history(
                history
            )
            policy_decision, _trace = policy_engine.evaluate(
                decision=decision,
                payment=updated_payment,
                case=updated_case,
                current_time=current_time,
                history=policy_history,
                event_trust=EventTrustState.TRUSTED,
            )

            # Step 7: Enforce No-Blind-Repetition & Loop Bounds Safety Guard
            domain_action_type: RecoveryActionType | None = None
            can_execute = False

            if policy_decision.policy_outcome == PolicyOutcome.BLOCK:
                if updated_case.status == RecoveryCaseStatus.POLICY_CHECK:
                    updated_case = transition_recovery_case(
                        case=updated_case,
                        payment=updated_payment,
                        new_status=RecoveryCaseStatus.STOPPED,
                        now=current_time,
                    )
                term_reason = LoopTerminationReason.POLICY_BLOCKED
                if (
                    policy_decision.reason_code
                    == PolicyReasonCode.MAX_SAME_ACTION_REPETITIONS_REACHED
                    or "SAME_ACTION" in str(policy_decision.reason_code)
                    or "RETRY" in str(policy_decision.reason_code)
                ):
                    term_reason = LoopTerminationReason.SAME_ACTION_LIMIT_EXCEEDED
                outcome_res = OutcomeProcessingResult(
                    outcome=outcome_res.outcome,
                    disposition=RecoveryLoopDisposition.STOP,
                    case_status=updated_case.status,
                    re_evaluation_id=context.re_evaluation_id,
                    termination_reason=term_reason,
                    cycle_number=cycle_number,
                    provenance=outcome_res.provenance,
                )
            elif policy_decision.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL:
                if updated_case.status == RecoveryCaseStatus.POLICY_CHECK:
                    updated_case = transition_recovery_case(
                        case=updated_case,
                        payment=updated_payment,
                        new_status=RecoveryCaseStatus.ESCALATED,
                        now=current_time,
                    )
                outcome_res = OutcomeProcessingResult(
                    outcome=outcome_res.outcome,
                    disposition=RecoveryLoopDisposition.ESCALATE,
                    case_status=updated_case.status,
                    re_evaluation_id=context.re_evaluation_id,
                    termination_reason=LoopTerminationReason.HUMAN_ESCALATION_REQUIRED,
                    cycle_number=cycle_number,
                    provenance=outcome_res.provenance,
                )
            elif (
                policy_decision.policy_outcome == PolicyOutcome.ALLOW
                and decision.selected_action is not None
            ):
                action_type_val = decision.selected_action.value
                domain_action_type = (
                    RecoveryActionType.ALTERNATE_RECOVERY
                    if action_type_val == "PAYMENT_LINK"
                    else (
                        RecoveryActionType(action_type_val)
                        if action_type_val in [e.value for e in RecoveryActionType]
                        else RecoveryActionType.RETRY
                    )
                )
                # Check consecutive same-action repetition limit
                can_repeat = self.safety_guard.check_same_action_repetition(
                    proposed_action=domain_action_type,
                    history=history,
                )
                if not can_repeat:
                    # Guardrail 3 & 11: Safety guard rejects immediate
                    # consecutive repetition
                    can_execute = False
                    if updated_case.status == RecoveryCaseStatus.POLICY_CHECK:
                        updated_case = transition_recovery_case(
                            case=updated_case,
                            payment=updated_payment,
                            new_status=RecoveryCaseStatus.STOPPED,
                            now=current_time,
                        )
                    outcome_res = OutcomeProcessingResult(
                        outcome=outcome_res.outcome,
                        disposition=RecoveryLoopDisposition.STOP,
                        case_status=updated_case.status,
                        re_evaluation_id=context.re_evaluation_id,
                        termination_reason=LoopTerminationReason.SAME_ACTION_LIMIT_EXCEEDED,
                        cycle_number=cycle_number,
                        provenance=outcome_res.provenance,
                    )
                else:
                    can_execute = True

            # If Policy ALLOWs and Safety Guard passes, advance case to ACTION_APPROVED
            # and execute through Phase 11
            exec_result: ExecutionResult | None = None
            if can_execute and domain_action_type is not None:
                if updated_case.status == RecoveryCaseStatus.POLICY_CHECK:
                    updated_case = transition_recovery_case(
                        case=updated_case,
                        payment=updated_payment,
                        new_status=RecoveryCaseStatus.ACTION_APPROVED,
                        now=current_time,
                    )

                recovery_action = RecoveryAction(
                    action_id=f"act_{updated_case.case_id[:8]}_{next_cycle}",
                    case_id=updated_case.case_id,
                    action_type=domain_action_type,
                    status=RecoveryActionStatus.APPROVED,
                    created_at=current_time,
                    updated_at=current_time,
                    execution_mode=execution_mode,
                    parameters=execution_parameters
                    or {"amount": updated_payment.amount},
                )
                if uow is not None:
                    await uow.recovery_actions.save(recovery_action)

                # Execute through Phase 11 Execution Orchestrator
                exec_result = await execution_orchestrator.execute(
                    policy_decision=policy_decision,
                    recovery_action=recovery_action,
                    recovery_case=updated_case,
                    payment=updated_payment,
                    execution_mode=execution_mode,
                    current_time=current_time,
                    parameters=execution_parameters
                    or {"amount": updated_payment.amount},
                    unit_of_work=uow,
                )
                if exec_result.status == ExecutionStatus.SUCCEEDED:
                    executing_case = transition_recovery_case(
                        case=updated_case,
                        payment=updated_payment,
                        new_status=RecoveryCaseStatus.EXECUTING,
                        now=current_time,
                    )
                    updated_case = transition_recovery_case(
                        case=executing_case,
                        payment=updated_payment,
                        new_status=RecoveryCaseStatus.OBSERVING,
                        now=current_time,
                    )

            # Update outcome processing result with re_evaluation_id
            updated_outcome_res = OutcomeProcessingResult(
                outcome=outcome_res.outcome,
                disposition=outcome_res.disposition,
                case_status=updated_case.status,
                re_evaluation_id=context.re_evaluation_id,
                termination_reason=outcome_res.termination_reason,
                cycle_number=cycle_number,
                provenance=outcome_res.provenance,
            )

            res = AdaptiveCycleResult(
                cycle_number=next_cycle,
                re_evaluation_id=context.re_evaluation_id,
                outcome_result=updated_outcome_res,
                decision=decision,
                policy_decision=policy_decision,
                execution_result=exec_result,
            )

            return res, updated_case, updated_payment
