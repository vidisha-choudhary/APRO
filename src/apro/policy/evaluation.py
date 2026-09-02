"""Governed benchmark policy evaluation, constraint violation metrics,
segment analysis, distribution shift comparison, and evaluator-side error analysis.
"""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.models import GovernedDataset
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import (
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)
from apro.decision.models import RecoveryDecision
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig
from apro.policy.engine import PolicyEngine
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import (
    ActionExecutionHistory,
    EventTrustState,
    PolicyDecision,
)
from apro.policy.traces import PolicyEvaluationTrace
from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.models import OutcomePrediction


class PolicySafetyMetrics(BaseModel):
    """Aggregate safety and governance metrics across an evaluation dataset."""

    model_config = ConfigDict(frozen=True)

    total_evaluations: int
    allow_count: int
    block_count: int
    require_human_approval_count: int
    allow_rate: float
    block_rate: float
    require_human_approval_rate: float
    constraint_violation_count: int = Field(
        default=0
    )  # Must be 0 in valid policy evaluation
    ineligible_selection_count: int = Field(default=0)
    ineligible_selection_rate: float = Field(default=0.0)
    captured_payment_block_count: int = Field(default=0)
    invalid_model_output_block_count: int = Field(default=0)
    duplicate_event_block_count: int = Field(default=0)
    retry_limit_block_count: int = Field(default=0)
    cooldown_block_count: int = Field(default=0)
    same_action_block_count: int = Field(default=0)
    total_intervention_limit_block_count: int = Field(default=0)
    high_value_approval_count: int = Field(default=0)
    low_confidence_approval_count: int = Field(default=0)
    reconciliation_required_count: int = Field(default=0)
    idempotency_conflict_count: int = Field(default=0)
    negative_erv_block_count: int = Field(default=0)
    reason_code_counts: dict[str, int] = Field(default_factory=dict)
    action_counts_before_policy: dict[str, int] = Field(default_factory=dict)
    action_counts_after_policy: dict[str, int] = Field(default_factory=dict)


class ErrorAnalysisCase(BaseModel):
    """Evaluator-side error analysis case context."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    scenario_id: str
    category: str
    description: str
    proposed_action: str | None
    effective_action: str | None
    policy_outcome: str
    reason_code: str
    confidence: float
    payment_amount: int


class PolicyErrorAnalysisReport(BaseModel):
    """Evaluator-side error analysis output across all required categories."""

    model_config = ConfigDict(frozen=True)

    total_cases_analyzed: int
    wrong_policy_outcomes: list[ErrorAnalysisCase] = Field(default_factory=list)
    high_confidence_policy_mistakes: list[ErrorAnalysisCase] = Field(
        default_factory=list
    )
    negative_utility_incorrectly_permitted: list[ErrorAnalysisCase] = Field(
        default_factory=list
    )
    near_threshold_decisions: list[ErrorAnalysisCase] = Field(default_factory=list)
    policy_filtered_selections: list[ErrorAnalysisCase] = Field(default_factory=list)
    stale_state_protections: list[ErrorAnalysisCase] = Field(default_factory=list)
    model_failure_protections: list[ErrorAnalysisCase] = Field(default_factory=list)
    shift_sensitive_cases: list[ErrorAnalysisCase] = Field(default_factory=list)


def evaluate_policy_on_dataset(
    dataset: GovernedDataset,
    engine: PolicyEngine | None = None,
    config: PolicyConfig | None = None,
    decisions: list[RecoveryDecision] | None = None,
    decision_engine: EconomicDecisionEngine | None = None,
    diagnosis_model: BaseDiagnosisModel | None = None,
    outcome_model: BaseRecoveryOutcomeModel | None = None,
) -> tuple[PolicySafetyMetrics, list[PolicyDecision], list[PolicyEvaluationTrace]]:
    """Evaluate PolicyEngine across benchmark scenarios."""
    active_engine = engine or PolicyEngine()
    active_config = config or DEFAULT_POLICY_CONFIG
    now = datetime.now(UTC)

    # 1. Compute or obtain upstream Phase 9 decisions
    if decisions is None:
        dec_engine = decision_engine or EconomicDecisionEngine()
        computed_decisions: list[RecoveryDecision] = []

        for rec in dataset.records:
            model_in = rec.model_input
            diag_res = diagnosis_model.predict(model_in) if diagnosis_model else None
            preds: dict[RecoveryAction, OutcomePrediction] = {}
            if outcome_model:
                for act in RECOVERY_ACTION_ORDER:
                    preds[act] = outcome_model.predict(
                        model_in, act, diagnosis_result=diag_res
                    )

            dec = dec_engine.decide(
                model_input=model_in,
                diagnosis_result=diag_res,
                outcome_predictions=preds,
            )
            computed_decisions.append(dec)
        eval_decisions = computed_decisions
    else:
        eval_decisions = decisions

    policy_decisions: list[PolicyDecision] = []
    traces: list[PolicyEvaluationTrace] = []

    reason_counts: Counter[str] = Counter()
    action_before_counts: Counter[str] = Counter()
    action_after_counts: Counter[str] = Counter()

    captured_payment_blocks = 0
    invalid_model_output_blocks = 0
    duplicate_event_blocks = 0
    retry_limit_blocks = 0
    cooldown_blocks = 0
    same_action_blocks = 0
    total_intervention_blocks = 0
    high_value_approvals = 0
    low_confidence_approvals = 0
    reconciliation_blocks = 0
    idempotency_conflicts = 0
    negative_erv_blocks = 0
    constraint_violations = 0
    ineligible_selection_count = 0

    allow_count = 0
    block_count = 0
    approval_count = 0

    # 2. Evaluate PolicyEngine for each scenario
    for rec, dec in zip(dataset.records, eval_decisions, strict=False):
        features = rec.model_input.features

        # Check for ineligible selection from Phase 9
        if dec.selected_action:
            elig = dec.eligibility_by_action.get(dec.selected_action)
            if elig is not None and not elig.is_eligible:
                ineligible_selection_count += 1

        # Synthesize domain Payment entity from observable state
        payment = Payment(
            payment_id=f"pay_{rec.model_input.scenario_id}",
            customer_id=features.customer_id,
            provider="razorpay",
            amount=features.payment_amount,
            currency=features.currency,
            method=features.payment_method.value,
            status=PaymentStatus.FAILED,
            created_at=now,
            updated_at=now,
        )

        case_id_val = dec.recovery_case_id or f"case_{rec.model_input.scenario_id}"
        case = RecoveryCase(
            case_id=case_id_val,
            payment_id=payment.payment_id,
            customer_id=features.customer_id,
            status=RecoveryCaseStatus.NEW,
            opened_at=now,
            updated_at=now,
            current_attempt_count=features.attempt_count,
        )

        history = ActionExecutionHistory(
            retry_count=features.attempt_count,
            total_interventions=features.attempt_count,
            same_action_count=features.attempt_count,
        )

        # Count proposed action before policy
        prop_action_str = dec.selected_action.value if dec.selected_action else "NONE"
        action_before_counts[prop_action_str] += 1

        pol_dec, trace = active_engine.evaluate(
            decision=dec,
            payment=payment,
            case=case,
            current_time=now,
            config=active_config,
            history=history,
            event_trust=EventTrustState.TRUSTED,
        )

        policy_decisions.append(pol_dec)
        traces.append(trace)

        # Count outcomes & reasons
        reason_counts[pol_dec.reason_code.value] += 1

        if pol_dec.policy_outcome == PolicyOutcome.ALLOW:
            allow_count += 1
            effective_str = (
                pol_dec.effective_action.value if pol_dec.effective_action else "NONE"
            )
            action_after_counts[effective_str] += 1
        elif pol_dec.policy_outcome == PolicyOutcome.BLOCK:
            block_count += 1
            action_after_counts["BLOCKED"] += 1
        elif pol_dec.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL:
            approval_count += 1
            action_after_counts["REQUIRES_APPROVAL"] += 1

        # Track specific reason categories
        rc = pol_dec.reason_code
        if rc == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED:
            captured_payment_blocks += 1
        elif rc == PolicyReasonCode.INVALID_MODEL_OUTPUT:
            invalid_model_output_blocks += 1
        elif rc == PolicyReasonCode.DUPLICATE_EVENT:
            duplicate_event_blocks += 1
        elif rc == PolicyReasonCode.MAX_RETRIES_REACHED:
            retry_limit_blocks += 1
        elif rc == PolicyReasonCode.RETRY_COOLDOWN_ACTIVE:
            cooldown_blocks += 1
        elif rc == PolicyReasonCode.MAX_SAME_ACTION_REPETITIONS_REACHED:
            same_action_blocks += 1
        elif rc == PolicyReasonCode.MAX_TOTAL_INTERVENTIONS_REACHED:
            total_intervention_blocks += 1
        elif rc == PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL:
            high_value_approvals += 1
        elif rc == PolicyReasonCode.LOW_CONFIDENCE_REQUIRES_APPROVAL:
            low_confidence_approvals += 1
        elif rc == PolicyReasonCode.RECONCILIATION_REQUIRED:
            reconciliation_blocks += 1
        elif rc == PolicyReasonCode.IDEMPOTENCY_CONFLICT:
            idempotency_conflicts += 1
        elif rc in (
            PolicyReasonCode.NEGATIVE_EXPECTED_VALUE,
            PolicyReasonCode.INSUFFICIENT_EXPECTED_VALUE,
        ):
            negative_erv_blocks += 1

        # Verify that policy didn't violate any hard constraint
        # High value active interventions require approval
        if (
            payment.amount >= active_config.high_value_threshold
            and pol_dec.policy_outcome == PolicyOutcome.ALLOW
            and pol_dec.effective_action
            in (
                RecoveryAction.RETRY,
                RecoveryAction.PAYMENT_LINK,
                RecoveryAction.OUTREACH,
            )
            and not pol_dec.approval_reference
        ):
            constraint_violations += 1

        # Retry limit violation
        if (
            history.retry_count >= active_config.max_retries
            and pol_dec.effective_action == RecoveryAction.RETRY
        ):
            constraint_violations += 1

    total = len(dataset.records)
    metrics = PolicySafetyMetrics(
        total_evaluations=total,
        allow_count=allow_count,
        block_count=block_count,
        require_human_approval_count=approval_count,
        allow_rate=allow_count / total if total > 0 else 0.0,
        block_rate=block_count / total if total > 0 else 0.0,
        require_human_approval_rate=approval_count / total if total > 0 else 0.0,
        constraint_violation_count=constraint_violations,
        ineligible_selection_count=ineligible_selection_count,
        ineligible_selection_rate=(
            ineligible_selection_count / total if total > 0 else 0.0
        ),
        captured_payment_block_count=captured_payment_blocks,
        invalid_model_output_block_count=invalid_model_output_blocks,
        duplicate_event_block_count=duplicate_event_blocks,
        retry_limit_block_count=retry_limit_blocks,
        cooldown_block_count=cooldown_blocks,
        same_action_block_count=same_action_blocks,
        total_intervention_limit_block_count=total_intervention_blocks,
        high_value_approval_count=high_value_approvals,
        low_confidence_approval_count=low_confidence_approvals,
        reconciliation_required_count=reconciliation_blocks,
        idempotency_conflict_count=idempotency_conflicts,
        negative_erv_block_count=negative_erv_blocks,
        reason_code_counts=dict(reason_counts),
        action_counts_before_policy=dict(action_before_counts),
        action_counts_after_policy=dict(action_after_counts),
    )

    return metrics, policy_decisions, traces


def evaluate_policy_segments(
    dataset: GovernedDataset,
    policy_decisions: list[PolicyDecision],
    decisions: list[RecoveryDecision] | None = None,
) -> dict[str, dict[str, Any]]:
    """Segment policy outcomes across all 10 required evaluation dimensions:
    scenario_family, payment_method, payment_value_tier, scenario_difficulty,
    failure_diagnosis, diagnosis_confidence_tier, selected_action,
    policy_outcome, policy_reason, and seed.
    """
    segments: dict[str, dict[str, Any]] = {}

    def _record(key: str, outcome: PolicyOutcome) -> None:
        if key not in segments:
            segments[key] = {
                "count": 0,
                "allow": 0,
                "block": 0,
                "require_approval": 0,
            }
        segments[key]["count"] += 1
        if outcome == PolicyOutcome.ALLOW:
            segments[key]["allow"] += 1
        elif outcome == PolicyOutcome.BLOCK:
            segments[key]["block"] += 1
        elif outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL:
            segments[key]["require_approval"] += 1

    for idx, (rec, pol_dec) in enumerate(
        zip(dataset.records, policy_decisions, strict=False)
    ):
        features = rec.model_input.features
        truth = rec.evaluation_truth
        phase9_dec = decisions[idx] if decisions and idx < len(decisions) else None

        # 1. scenario_family
        _record(f"family_{truth.scenario_family.value}", pol_dec.policy_outcome)

        # 2. payment_method
        _record(f"method_{features.payment_method.value}", pol_dec.policy_outcome)

        # 3. payment_value_tier
        amount = features.payment_amount
        tier_name = "low" if amount < 25000 else "medium" if amount < 100000 else "high"
        _record(f"value_tier_{tier_name}", pol_dec.policy_outcome)

        # 4. scenario_difficulty
        _record(
            f"difficulty_{truth.scenario_difficulty.value}",
            pol_dec.policy_outcome,
        )

        # 5. failure_diagnosis
        _record(f"diagnosis_{features.failure_code}", pol_dec.policy_outcome)

        # 6. diagnosis_confidence_tier
        conf = (
            phase9_dec.decision_confidence
            if phase9_dec
            else pol_dec.provenance.get("decision_confidence", 0.75)
        )
        conf_tier = "low" if conf < 0.50 else "medium" if conf < 0.80 else "high"
        _record(f"confidence_tier_{conf_tier}", pol_dec.policy_outcome)

        # 7. selected_action
        req_act = pol_dec.requested_action.value if pol_dec.requested_action else "NONE"
        _record(f"action_{req_act}", pol_dec.policy_outcome)

        # 8. policy_outcome
        _record(f"outcome_{pol_dec.policy_outcome.value}", pol_dec.policy_outcome)

        # 9. policy_reason
        _record(f"reason_{pol_dec.reason_code.value}", pol_dec.policy_outcome)

        # 10. seed
        _record(f"seed_{rec.model_input.generation_seed}", pol_dec.policy_outcome)

    return segments


def compare_distribution_shift(
    in_dist_metrics: PolicySafetyMetrics,
    shift_metrics: PolicySafetyMetrics,
) -> dict[str, Any]:
    """Compare in-distribution vs distribution-shifted policy metrics
    across all required dimensions.
    """
    in_total = in_dist_metrics.total_evaluations
    shift_total = shift_metrics.total_evaluations

    in_reconcile_rate = (
        in_dist_metrics.reconciliation_required_count / in_total
        if in_total > 0
        else 0.0
    )
    shift_reconcile_rate = (
        shift_metrics.reconciliation_required_count / shift_total
        if shift_total > 0
        else 0.0
    )

    in_safety_counters = {
        "captured_payment_blocks": in_dist_metrics.captured_payment_block_count,
        "invalid_model_output_blocks": (
            in_dist_metrics.invalid_model_output_block_count
        ),
        "duplicate_event_blocks": in_dist_metrics.duplicate_event_block_count,
        "retry_limit_blocks": in_dist_metrics.retry_limit_block_count,
        "cooldown_blocks": in_dist_metrics.cooldown_block_count,
        "same_action_blocks": in_dist_metrics.same_action_block_count,
        "total_intervention_blocks": (
            in_dist_metrics.total_intervention_limit_block_count
        ),
        "high_value_approvals": in_dist_metrics.high_value_approval_count,
        "low_confidence_approvals": in_dist_metrics.low_confidence_approval_count,
        "reconciliation_blocks": in_dist_metrics.reconciliation_required_count,
        "idempotency_conflicts": in_dist_metrics.idempotency_conflict_count,
        "negative_erv_blocks": in_dist_metrics.negative_erv_block_count,
    }

    shift_safety_counters = {
        "captured_payment_blocks": shift_metrics.captured_payment_block_count,
        "invalid_model_output_blocks": (shift_metrics.invalid_model_output_block_count),
        "duplicate_event_blocks": shift_metrics.duplicate_event_block_count,
        "retry_limit_blocks": shift_metrics.retry_limit_block_count,
        "cooldown_blocks": shift_metrics.cooldown_block_count,
        "same_action_blocks": shift_metrics.same_action_block_count,
        "total_intervention_blocks": (
            shift_metrics.total_intervention_limit_block_count
        ),
        "high_value_approvals": shift_metrics.high_value_approval_count,
        "low_confidence_approvals": shift_metrics.low_confidence_approval_count,
        "reconciliation_blocks": shift_metrics.reconciliation_required_count,
        "idempotency_conflicts": shift_metrics.idempotency_conflict_count,
        "negative_erv_blocks": shift_metrics.negative_erv_block_count,
    }

    return {
        "in_distribution": {
            "total": in_total,
            "allow_rate": in_dist_metrics.allow_rate,
            "block_rate": in_dist_metrics.block_rate,
            "require_human_approval_rate": (
                in_dist_metrics.require_human_approval_rate
            ),
            "constraint_violations": in_dist_metrics.constraint_violation_count,
            "captured_payment_blocks": (in_dist_metrics.captured_payment_block_count),
            "invalid_output_blocks": (in_dist_metrics.invalid_model_output_block_count),
            "reconciliation_rate": in_reconcile_rate,
            "ineligible_selection_rate": (in_dist_metrics.ineligible_selection_rate),
            "action_distribution_after_policy": (
                in_dist_metrics.action_counts_after_policy
            ),
            "safety_counters": in_safety_counters,
        },
        "distribution_shift": {
            "total": shift_total,
            "allow_rate": shift_metrics.allow_rate,
            "block_rate": shift_metrics.block_rate,
            "require_human_approval_rate": (shift_metrics.require_human_approval_rate),
            "constraint_violations": shift_metrics.constraint_violation_count,
            "captured_payment_blocks": (shift_metrics.captured_payment_block_count),
            "invalid_output_blocks": (shift_metrics.invalid_model_output_block_count),
            "reconciliation_rate": shift_reconcile_rate,
            "ineligible_selection_rate": (shift_metrics.ineligible_selection_rate),
            "action_distribution_after_policy": (
                shift_metrics.action_counts_after_policy
            ),
            "safety_counters": shift_safety_counters,
        },
        "delta": {
            "allow_rate_delta": shift_metrics.allow_rate - in_dist_metrics.allow_rate,
            "block_rate_delta": shift_metrics.block_rate - in_dist_metrics.block_rate,
            "approval_rate_delta": (
                shift_metrics.require_human_approval_rate
                - in_dist_metrics.require_human_approval_rate
            ),
            "constraint_violations_delta": (
                shift_metrics.constraint_violation_count
                - in_dist_metrics.constraint_violation_count
            ),
            "captured_payment_blocks_delta": (
                shift_metrics.captured_payment_block_count
                - in_dist_metrics.captured_payment_block_count
            ),
            "invalid_output_blocks_delta": (
                shift_metrics.invalid_model_output_block_count
                - in_dist_metrics.invalid_model_output_block_count
            ),
            "reconciliation_rate_delta": shift_reconcile_rate - in_reconcile_rate,
        },
    }


def perform_policy_error_analysis(
    dataset: GovernedDataset,
    decisions: list[RecoveryDecision],
    policy_decisions: list[PolicyDecision],
    traces: list[PolicyEvaluationTrace],
    config: PolicyConfig | None = None,
) -> PolicyErrorAnalysisReport:
    """Identify and structure evaluator-side error analysis categories without
    leaking simulator truth into live engine outputs.
    """
    active_config = config or DEFAULT_POLICY_CONFIG
    wrong_outcomes: list[ErrorAnalysisCase] = []
    high_conf_mistakes: list[ErrorAnalysisCase] = []
    neg_utility_permitted: list[ErrorAnalysisCase] = []
    near_threshold: list[ErrorAnalysisCase] = []
    filtered_selections: list[ErrorAnalysisCase] = []
    stale_protections: list[ErrorAnalysisCase] = []
    model_failure_protections: list[ErrorAnalysisCase] = []
    shift_sensitive: list[ErrorAnalysisCase] = []

    for _idx, (rec, dec, pol_dec, _tr) in enumerate(
        zip(dataset.records, decisions, policy_decisions, traces, strict=False)
    ):
        model_in = rec.model_input
        features = model_in.features
        if hasattr(dec, "selected_action"):
            prop_act = dec.selected_action
            prop_str = dec.selected_action.value if dec.selected_action else None
        else:
            prop_act = pol_dec.requested_action
            prop_str = (
                pol_dec.requested_action.value if pol_dec.requested_action else None
            )

        eff_str = pol_dec.effective_action.value if pol_dec.effective_action else None
        conf = getattr(
            dec,
            "decision_confidence",
            getattr(pol_dec, "decision_confidence", 0.75),
        )
        erv = getattr(dec, "expected_recovery_value", None)

        base_case = ErrorAnalysisCase(
            record_id=model_in.record_id,
            scenario_id=model_in.scenario_id,
            category="general",
            description="",
            proposed_action=prop_str,
            effective_action=eff_str,
            policy_outcome=pol_dec.policy_outcome.value,
            reason_code=pol_dec.reason_code.value,
            confidence=conf,
            payment_amount=features.payment_amount,
        )

        # 1. Wrong policy outcome vs safety expectation
        if (
            features.payment_amount >= active_config.high_value_threshold
            and pol_dec.policy_outcome == PolicyOutcome.ALLOW
            and pol_dec.effective_action
            in (
                RecoveryAction.RETRY,
                RecoveryAction.PAYMENT_LINK,
                RecoveryAction.OUTREACH,
            )
            and not pol_dec.approval_reference
        ):
            wrong_outcomes.append(
                base_case.model_copy(
                    update={
                        "category": "wrong_policy_outcome",
                        "description": (
                            "High value transaction permitted without required approval"
                        ),
                    }
                )
            )

        # 2. High confidence policy mistakes
        if conf >= 0.80 and pol_dec.policy_outcome != PolicyOutcome.ALLOW:
            high_conf_mistakes.append(
                base_case.model_copy(
                    update={
                        "category": "high_confidence_policy_mistake",
                        "description": (
                            f"Model confidence {conf:.2f} "
                            f"but policy outcome is {pol_dec.policy_outcome.value}"
                        ),
                    }
                )
            )

        # 3. Negative utility attempts incorrectly permitted
        if (
            erv is not None
            and erv <= 0
            and pol_dec.policy_outcome == PolicyOutcome.ALLOW
            and pol_dec.effective_action
            not in (RecoveryAction.STOP, RecoveryAction.ESCALATE)
        ):
            neg_utility_permitted.append(
                base_case.model_copy(
                    update={
                        "category": "negative_utility_permitted",
                        "description": f"Negative ERV {erv} permitted as {eff_str}",
                    }
                )
            )

        # 4. Near-threshold decisions
        is_near_conf = abs(conf - active_config.min_decision_confidence) <= 0.05
        is_near_hv = (
            abs(features.payment_amount - active_config.high_value_threshold)
            <= 0.10 * active_config.high_value_threshold
        )
        if is_near_conf or is_near_hv:
            near_threshold.append(
                base_case.model_copy(
                    update={
                        "category": "near_threshold_decision",
                        "description": (
                            f"Near threshold: conf={conf:.2f}, "
                            f"amount={features.payment_amount}"
                        ),
                    }
                )
            )

        # 5. Policy-filtered selections
        if (
            prop_act
            in (
                RecoveryAction.RETRY,
                RecoveryAction.PAYMENT_LINK,
                RecoveryAction.OUTREACH,
            )
            and pol_dec.policy_outcome != PolicyOutcome.ALLOW
        ):
            filtered_selections.append(
                base_case.model_copy(
                    update={
                        "category": "policy_filtered_selection",
                        "description": (
                            f"Phase 9 proposed {prop_str} filtered to "
                            f"{pol_dec.policy_outcome.value} "
                            f"({pol_dec.reason_code.value})"
                        ),
                    }
                )
            )

        # 6. Stale-state protections
        if pol_dec.reason_code == PolicyReasonCode.STALE_OR_INCONSISTENT_EVENT:
            stale_protections.append(
                base_case.model_copy(
                    update={
                        "category": "stale_state_protection",
                        "description": "Event blocked by stale state protection (S5)",
                    }
                )
            )

        # 7. Model-failure protections
        if pol_dec.reason_code in (
            PolicyReasonCode.INVALID_MODEL_OUTPUT,
            PolicyReasonCode.MODEL_A_FAILURE,
            PolicyReasonCode.MODEL_B_FAILURE,
        ):
            model_failure_protections.append(
                base_case.model_copy(
                    update={
                        "category": "model_failure_protection",
                        "description": (
                            "Model failure fail-safe protection triggered: "
                            f"{pol_dec.reason_code.value}"
                        ),
                    }
                )
            )

        # 8. Shift-sensitive cases
        if (
            pol_dec.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
            and conf < active_config.min_decision_confidence
        ):
            shift_sensitive.append(
                base_case.model_copy(
                    update={
                        "category": "shift_sensitive",
                        "description": (
                            "Low confidence triggered approval requirement "
                            "under evaluation"
                        ),
                    }
                )
            )

    return PolicyErrorAnalysisReport(
        total_cases_analyzed=len(dataset.records),
        wrong_policy_outcomes=wrong_outcomes,
        high_confidence_policy_mistakes=high_conf_mistakes,
        negative_utility_incorrectly_permitted=neg_utility_permitted,
        near_threshold_decisions=near_threshold,
        policy_filtered_selections=filtered_selections,
        stale_state_protections=stale_protections,
        model_failure_protections=model_failure_protections,
        shift_sensitive_cases=shift_sensitive,
    )


__all__ = [
    "ErrorAnalysisCase",
    "PolicyErrorAnalysisReport",
    "PolicySafetyMetrics",
    "compare_distribution_shift",
    "evaluate_policy_on_dataset",
    "evaluate_policy_segments",
    "perform_policy_error_analysis",
]
