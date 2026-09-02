"""Deterministic rule definitions, trigger logic, and rule registry for Phase 10."""

from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from apro.decision.models import RecoveryDecision
from apro.domain.enums import PaymentStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.approvals import validate_human_approval
from apro.policy.config import PolicyConfig
from apro.policy.enums import (
    PolicyOutcome,
    PolicyReasonCode,
    RuleId,
    RulePrecedenceLevel,
)
from apro.policy.idempotency import is_idempotency_conflict
from apro.policy.models import (
    ActionExecutionHistory,
    ApprovalRecord,
    EventTrustState,
)
from apro.policy.state_guard import (
    is_payment_captured,
    is_stale_or_inconsistent_event,
)
from apro.policy.validation import (
    is_action_supported,
    validate_entity_binding,
    validate_event_trust,
    validate_recovery_decision_model_output,
)
from apro.recovery_prediction.enums import RecoveryAction


class PolicyRuleContext(BaseModel):
    """Execution context containing all inputs required for policy rule evaluation."""

    model_config = ConfigDict(frozen=True)

    decision: RecoveryDecision
    payment: Payment
    case: RecoveryCase
    config: PolicyConfig
    history: ActionExecutionHistory = Field(default_factory=ActionExecutionHistory)
    event_trust: EventTrustState | bool | str | None = EventTrustState.UNTRUSTED
    is_duplicate_event: bool = False
    event_timestamp: datetime | None = None
    approval: ApprovalRecord | None = None
    current_time: datetime
    idempotency_key: str | None = None
    model_a_failed: bool = False
    model_b_failed: bool = False
    entity_binding_valid: bool = True
    entity_binding_error: str | None = None


class RuleEvaluationResult(BaseModel):
    """Result produced by evaluating a single policy rule."""

    model_config = ConfigDict(frozen=True)

    rule_id: RuleId
    triggered: bool
    outcome: PolicyOutcome = PolicyOutcome.ALLOW
    precedence: RulePrecedenceLevel = RulePrecedenceLevel.ALLOW
    reason_code: PolicyReasonCode = PolicyReasonCode.POLICY_ALLOWED
    detail: str = ""


# ==============================================================================
# Hard Safety Rules (H1–H5)
# ==============================================================================


def eval_h1_payment_captured(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """H1: If payment is already captured, hard block recovery."""
    if is_payment_captured(ctx.payment):
        return RuleEvaluationResult(
            rule_id=RuleId.H1_PAYMENT_CAPTURED,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.HARD_SAFETY_BLOCK,
            reason_code=PolicyReasonCode.PAYMENT_ALREADY_RECOVERED,
            detail=(
                f"Payment {ctx.payment.payment_id} is already CAPTURED. "
                "Automated recovery is prohibited."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.H1_PAYMENT_CAPTURED, triggered=False)


def eval_h2_invalid_event(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """H2: If webhook signature is invalid/untrusted, reject and block."""
    if not validate_event_trust(ctx.event_trust):
        return RuleEvaluationResult(
            rule_id=RuleId.H2_INVALID_EVENT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.HARD_SAFETY_BLOCK,
            reason_code=PolicyReasonCode.INVALID_EVENT,
            detail=(
                "Triggering event signature is invalid or untrusted. "
                "Recovery pipeline rejected."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.H2_INVALID_EVENT, triggered=False)


def eval_h3_duplicate_event(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """H3: If event ID was already processed, block duplicate authorization."""
    if ctx.is_duplicate_event:
        return RuleEvaluationResult(
            rule_id=RuleId.H3_DUPLICATE_EVENT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.HARD_SAFETY_BLOCK,
            reason_code=PolicyReasonCode.DUPLICATE_EVENT,
            detail=(
                "Duplicate event delivery detected. Additional external action blocked."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.H3_DUPLICATE_EVENT, triggered=False)


def eval_h4_unsupported_action(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """H4: If requested action is not supported by executor taxonomy, block."""
    action = ctx.decision.selected_action
    if not is_action_supported(action):
        return RuleEvaluationResult(
            rule_id=RuleId.H4_UNSUPPORTED_ACTION,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.UNSUPPORTED_ACTION,
            reason_code=PolicyReasonCode.UNSUPPORTED_ACTION,
            detail=(
                f"Requested action '{action}' is not in the "
                "supported 5-action taxonomy."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.H4_UNSUPPORTED_ACTION, triggered=False)


def eval_h5_invalid_model_output(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """H5: If model output fails mathematical sanity constraints, block."""
    # Check entity binding first
    if not ctx.entity_binding_valid:
        return RuleEvaluationResult(
            rule_id=RuleId.H5_INVALID_MODEL_OUTPUT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.INVALID_MODEL_OUTPUT,
            reason_code=PolicyReasonCode.INVALID_MODEL_OUTPUT,
            detail=f"Entity binding validation failed: {ctx.entity_binding_error}",
        )
    valid_bind, err_bind = validate_entity_binding(ctx.payment, ctx.case, ctx.decision)
    if not valid_bind:
        return RuleEvaluationResult(
            rule_id=RuleId.H5_INVALID_MODEL_OUTPUT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.INVALID_MODEL_OUTPUT,
            reason_code=PolicyReasonCode.INVALID_MODEL_OUTPUT,
            detail=f"Entity binding mismatch: {err_bind}",
        )
    valid, err_msg = validate_recovery_decision_model_output(ctx.decision, ctx.payment)
    if not valid:
        return RuleEvaluationResult(
            rule_id=RuleId.H5_INVALID_MODEL_OUTPUT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.INVALID_MODEL_OUTPUT,
            reason_code=PolicyReasonCode.INVALID_MODEL_OUTPUT,
            detail=f"Model output validation failed: {err_msg}",
        )
    return RuleEvaluationResult(rule_id=RuleId.H5_INVALID_MODEL_OUTPUT, triggered=False)


# ==============================================================================
# Model Failures (M1–M2)
# ==============================================================================


def eval_m1_model_a_failure(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """M1: If Diagnosis Model A fails, fail closed."""
    if ctx.model_a_failed:
        return RuleEvaluationResult(
            rule_id=RuleId.M1_MODEL_A_FAILURE,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.INVALID_MODEL_OUTPUT,
            reason_code=PolicyReasonCode.MODEL_A_FAILURE,
            detail="Diagnosis Model A execution failed. Fallback fail-closed block.",
        )
    return RuleEvaluationResult(rule_id=RuleId.M1_MODEL_A_FAILURE, triggered=False)


def eval_m2_model_b_failure(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """M2: If Recovery Outcome Model B fails, fail closed."""
    if ctx.model_b_failed:
        return RuleEvaluationResult(
            rule_id=RuleId.M2_MODEL_B_FAILURE,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.INVALID_MODEL_OUTPUT,
            reason_code=PolicyReasonCode.MODEL_B_FAILURE,
            detail="Outcome Model B execution failed. Fallback fail-closed block.",
        )
    return RuleEvaluationResult(rule_id=RuleId.M2_MODEL_B_FAILURE, triggered=False)


# ==============================================================================
# Retry & Attempt Limits (R1–R4)
# ==============================================================================


def eval_r1_retry_limit(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """R1: If retry count >= max_retries, block further RETRY attempts."""
    if (
        ctx.decision.selected_action == RecoveryAction.RETRY
        and ctx.history.retry_count >= ctx.config.max_retries
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.R1_RETRY_LIMIT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT,
            reason_code=PolicyReasonCode.MAX_RETRIES_REACHED,
            detail=(
                f"Retry attempt limit reached "
                f"({ctx.history.retry_count} >= {ctx.config.max_retries})."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.R1_RETRY_LIMIT, triggered=False)


def eval_r2_retry_cooldown(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """R2: If current time is within retry cooldown window, block/defer retry."""
    if (
        ctx.decision.selected_action == RecoveryAction.RETRY
        and ctx.history.last_retry_at
    ):
        elapsed = (ctx.current_time - ctx.history.last_retry_at).total_seconds()
        if elapsed < ctx.config.retry_cooldown_seconds:
            remaining = int(ctx.config.retry_cooldown_seconds - elapsed)
            return RuleEvaluationResult(
                rule_id=RuleId.R2_RETRY_COOLDOWN,
                triggered=True,
                outcome=PolicyOutcome.BLOCK,
                precedence=RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT,
                reason_code=PolicyReasonCode.RETRY_COOLDOWN_ACTIVE,
                detail=(
                    f"Retry cooldown active ({remaining}s remaining "
                    f"of {ctx.config.retry_cooldown_seconds}s window)."
                ),
            )
    return RuleEvaluationResult(rule_id=RuleId.R2_RETRY_COOLDOWN, triggered=False)


def eval_r3_same_action_limit(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """R3: If the same action is repeated >= max repetitions, block."""
    action = ctx.decision.selected_action
    if (
        action is not None
        and action not in (RecoveryAction.STOP, RecoveryAction.ESCALATE)
        and ctx.history.last_action == action
        and ctx.history.same_action_count >= ctx.config.max_same_action_repetitions
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.R3_SAME_ACTION_LIMIT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT,
            reason_code=PolicyReasonCode.MAX_SAME_ACTION_REPETITIONS_REACHED,
            detail=(
                f"Same action '{action.value}' repeated "
                f"{ctx.history.same_action_count} times "
                f"(max allowed: {ctx.config.max_same_action_repetitions})."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.R3_SAME_ACTION_LIMIT, triggered=False)


def eval_r4_total_intervention_limit(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """R4: If total case interventions >= max limit, block further interventions."""
    action = ctx.decision.selected_action
    if (
        action not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None)
        and ctx.history.total_interventions >= ctx.config.max_total_interventions
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.R4_TOTAL_INTERVENTION_LIMIT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT,
            reason_code=PolicyReasonCode.MAX_TOTAL_INTERVENTIONS_REACHED,
            detail=(
                f"Total intervention limit reached "
                f"({ctx.history.total_interventions} >= "
                f"{ctx.config.max_total_interventions})."
            ),
        )
    return RuleEvaluationResult(
        rule_id=RuleId.R4_TOTAL_INTERVENTION_LIMIT, triggered=False
    )


# ==============================================================================
# Safety Guardrails, Value, & State Rules (S1–S8)
# ==============================================================================


def eval_s1_high_value(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S1: If transaction amount >= high_value_threshold, require approval."""
    if ctx.payment.amount >= ctx.config.high_value_threshold:
        action = ctx.decision.selected_action
        if action not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None):
            return RuleEvaluationResult(
                rule_id=RuleId.S1_HIGH_VALUE,
                triggered=True,
                outcome=PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
                precedence=RulePrecedenceLevel.HUMAN_APPROVAL_REQUIREMENT,
                reason_code=PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL,
                detail=(
                    f"Transaction amount ({ctx.payment.amount} paise) exceeds "
                    f"high-value threshold ({ctx.config.high_value_threshold} paise)."
                ),
            )
    return RuleEvaluationResult(rule_id=RuleId.S1_HIGH_VALUE, triggered=False)


def eval_s2_low_confidence(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S2: If model confidence < min_decision_confidence, require approval."""
    if ctx.decision.decision_confidence < ctx.config.min_decision_confidence:
        action = ctx.decision.selected_action
        if action not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None):
            return RuleEvaluationResult(
                rule_id=RuleId.S2_LOW_CONFIDENCE,
                triggered=True,
                outcome=PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
                precedence=RulePrecedenceLevel.CONFIDENCE_ECONOMIC_GUARDRAIL,
                reason_code=PolicyReasonCode.LOW_CONFIDENCE_REQUIRES_APPROVAL,
                detail=(
                    f"Decision confidence ({ctx.decision.decision_confidence:.2f}) "
                    f"is below minimum ({ctx.config.min_decision_confidence:.2f})."
                ),
            )
    return RuleEvaluationResult(rule_id=RuleId.S2_LOW_CONFIDENCE, triggered=False)


def eval_s4_negative_erv(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S4: If expected recovery value <= 0, block active recovery."""
    erv = ctx.decision.expected_recovery_value
    action = ctx.decision.selected_action
    if (
        action not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None)
        and erv is not None
        and erv <= 0
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.S4_NEGATIVE_ERV,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.CONFIDENCE_ECONOMIC_GUARDRAIL,
            reason_code=PolicyReasonCode.NEGATIVE_EXPECTED_VALUE,
            detail=(
                f"Expected recovery value ({erv} paise) is non-positive. "
                "Active intervention prohibited."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.S4_NEGATIVE_ERV, triggered=False)


def eval_s3_min_erv(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S3: If expected recovery value is positive but < min ERV, block/stop."""
    erv = ctx.decision.expected_recovery_value
    action = ctx.decision.selected_action
    if (
        action not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None)
        and erv is not None
        and 0 < erv < ctx.config.min_expected_recovery_value
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.S3_MIN_ERV,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.CONFIDENCE_ECONOMIC_GUARDRAIL,
            reason_code=PolicyReasonCode.INSUFFICIENT_EXPECTED_VALUE,
            detail=(
                f"Expected recovery value ({erv} paise) is positive but below "
                f"minimum threshold ({ctx.config.min_expected_recovery_value} paise)."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.S3_MIN_ERV, triggered=False)


def eval_s5_stale_state(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S5: If event is stale/inconsistent with payment state, block."""
    if ctx.event_timestamp and is_stale_or_inconsistent_event(
        ctx.event_timestamp, ctx.payment
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.S5_STALE_STATE,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.STALE_UNKNOWN_STATE,
            reason_code=PolicyReasonCode.STALE_OR_INCONSISTENT_EVENT,
            detail=(
                f"Event timestamp ({ctx.event_timestamp.isoformat()}) is older "
                f"than current payment state ({ctx.payment.updated_at.isoformat()}). "
                "Stale state update rejected."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.S5_STALE_STATE, triggered=False)


def eval_s6_reconciliation(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S6: If payment state is ambiguous or non-recoverable, require reconciliation."""
    if ctx.payment.status not in (
        PaymentStatus.FAILED,
        PaymentStatus.PENDING,
        PaymentStatus.CAPTURED,
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.S6_RECONCILIATION,
            triggered=True,
            outcome=PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
            precedence=RulePrecedenceLevel.STALE_UNKNOWN_STATE,
            reason_code=PolicyReasonCode.RECONCILIATION_REQUIRED,
            detail=(
                f"Payment status '{ctx.payment.status}' is ambiguous or "
                "requires external provider reconciliation."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.S6_RECONCILIATION, triggered=False)


def eval_s7_payment_link_capacity(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S7: If Payment Link capacity is exhausted, block further Link creation."""
    if (
        ctx.decision.selected_action == RecoveryAction.PAYMENT_LINK
        and ctx.history.payment_link_count >= ctx.config.max_payment_link_creations
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.S7_PAYMENT_LINK_CAPACITY,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT,
            reason_code=PolicyReasonCode.PAYMENT_LINK_CAPACITY_REACHED,
            detail=(
                f"Payment Link capacity reached "
                f"({ctx.history.payment_link_count} >= "
                f"{ctx.config.max_payment_link_creations})."
            ),
        )
    return RuleEvaluationResult(
        rule_id=RuleId.S7_PAYMENT_LINK_CAPACITY, triggered=False
    )


def eval_s8_idempotency_conflict(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """S8: If generated idempotency key was already executed, block."""
    if ctx.idempotency_key and is_idempotency_conflict(
        ctx.idempotency_key, ctx.history.executed_idempotency_keys
    ):
        return RuleEvaluationResult(
            rule_id=RuleId.S8_IDEMPOTENCY_CONFLICT,
            triggered=True,
            outcome=PolicyOutcome.BLOCK,
            precedence=RulePrecedenceLevel.HARD_SAFETY_BLOCK,
            reason_code=PolicyReasonCode.IDEMPOTENCY_CONFLICT,
            detail=(
                f"Idempotency key '{ctx.idempotency_key}' has already "
                "been authorized or executed."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.S8_IDEMPOTENCY_CONFLICT, triggered=False)


# ==============================================================================
# Human Approval Rules (A1–A3)
# ==============================================================================


def eval_a1_approval_required(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """A1: When human approval is required but absent, require approval."""
    # Check if high value or low confidence applies
    is_hv = (
        ctx.payment.amount >= ctx.config.high_value_threshold
        and ctx.decision.selected_action
        not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None)
    )
    is_lc = (
        ctx.decision.decision_confidence < ctx.config.min_decision_confidence
        and ctx.decision.selected_action
        not in (RecoveryAction.STOP, RecoveryAction.ESCALATE, None)
    )
    if (is_hv or is_lc) and ctx.approval is None:
        return RuleEvaluationResult(
            rule_id=RuleId.A1_APPROVAL_REQUIRED,
            triggered=True,
            outcome=PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
            precedence=RulePrecedenceLevel.HUMAN_APPROVAL_REQUIREMENT,
            reason_code=PolicyReasonCode.APPROVAL_REQUIRED,
            detail=(
                "Human approval is required for this action but "
                "no approval token was provided."
            ),
        )
    return RuleEvaluationResult(rule_id=RuleId.A1_APPROVAL_REQUIRED, triggered=False)


def eval_a2_approval_mismatch(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """A2: If approval token is provided but mismatched or replayed, hard block."""
    if ctx.approval is not None:
        valid, reason, detail = validate_human_approval(
            approval=ctx.approval,
            case_id=ctx.case.case_id,
            decision_id=ctx.decision.decision_id,
            requested_action=ctx.decision.selected_action,
            current_time=ctx.current_time,
            expected_policy_version=ctx.config.policy_version,
            executed_approval_ids=ctx.history.executed_approval_ids,
        )
        if not valid and reason == PolicyReasonCode.APPROVAL_MISMATCH:
            return RuleEvaluationResult(
                rule_id=RuleId.A2_APPROVAL_MISMATCH,
                triggered=True,
                outcome=PolicyOutcome.BLOCK,
                precedence=RulePrecedenceLevel.HARD_SAFETY_BLOCK,
                reason_code=PolicyReasonCode.APPROVAL_MISMATCH,
                detail=detail or "Approval mismatch detected.",
            )
    return RuleEvaluationResult(rule_id=RuleId.A2_APPROVAL_MISMATCH, triggered=False)


def eval_a3_approval_expired(ctx: PolicyRuleContext) -> RuleEvaluationResult:
    """A3: If approval token is expired, hard block."""
    if ctx.approval is not None:
        valid, reason, detail = validate_human_approval(
            approval=ctx.approval,
            case_id=ctx.case.case_id,
            decision_id=ctx.decision.decision_id,
            requested_action=ctx.decision.selected_action,
            current_time=ctx.current_time,
            expected_policy_version=ctx.config.policy_version,
            executed_approval_ids=ctx.history.executed_approval_ids,
        )
        if not valid and reason == PolicyReasonCode.APPROVAL_EXPIRED:
            return RuleEvaluationResult(
                rule_id=RuleId.A3_APPROVAL_EXPIRED,
                triggered=True,
                outcome=PolicyOutcome.BLOCK,
                precedence=RulePrecedenceLevel.HARD_SAFETY_BLOCK,
                reason_code=PolicyReasonCode.APPROVAL_EXPIRED,
                detail=detail or "Approval token is expired.",
            )
    return RuleEvaluationResult(rule_id=RuleId.A3_APPROVAL_EXPIRED, triggered=False)


# ==============================================================================
# Rule Registry
# ==============================================================================

ALL_RULES: tuple[Callable[[PolicyRuleContext], RuleEvaluationResult], ...] = (
    eval_h1_payment_captured,
    eval_h2_invalid_event,
    eval_h3_duplicate_event,
    eval_h4_unsupported_action,
    eval_h5_invalid_model_output,
    eval_m1_model_a_failure,
    eval_m2_model_b_failure,
    eval_r1_retry_limit,
    eval_r2_retry_cooldown,
    eval_r3_same_action_limit,
    eval_r4_total_intervention_limit,
    eval_s1_high_value,
    eval_s2_low_confidence,
    eval_s4_negative_erv,
    eval_s3_min_erv,
    eval_s5_stale_state,
    eval_s6_reconciliation,
    eval_s7_payment_link_capacity,
    eval_s8_idempotency_conflict,
    eval_a1_approval_required,
    eval_a2_approval_mismatch,
    eval_a3_approval_expired,
)


class PolicyRuleRegistry:
    """Deterministic registry managing evaluation and ordering of policy rules."""

    def __init__(
        self,
        rules: tuple[
            Callable[[PolicyRuleContext], RuleEvaluationResult], ...
        ] = ALL_RULES,
    ) -> None:
        self._rules = rules

    def evaluate_all(self, ctx: PolicyRuleContext) -> tuple[RuleEvaluationResult, ...]:
        """Evaluate all registered rules against the given policy context."""
        return tuple(rule_func(ctx) for rule_func in self._rules)


DEFAULT_RULE_REGISTRY = PolicyRuleRegistry()

__all__ = [
    "ALL_RULES",
    "DEFAULT_RULE_REGISTRY",
    "PolicyRuleContext",
    "PolicyRuleRegistry",
    "RuleEvaluationResult",
    "eval_a1_approval_required",
    "eval_a2_approval_mismatch",
    "eval_a3_approval_expired",
    "eval_h1_payment_captured",
    "eval_h2_invalid_event",
    "eval_h3_duplicate_event",
    "eval_h4_unsupported_action",
    "eval_h5_invalid_model_output",
    "eval_m1_model_a_failure",
    "eval_m2_model_b_failure",
    "eval_r1_retry_limit",
    "eval_r2_retry_cooldown",
    "eval_r3_same_action_limit",
    "eval_r4_total_intervention_limit",
    "eval_s1_high_value",
    "eval_s2_low_confidence",
    "eval_s3_min_erv",
    "eval_s4_negative_erv",
    "eval_s5_stale_state",
    "eval_s6_reconciliation",
    "eval_s7_payment_link_capacity",
    "eval_s8_idempotency_conflict",
]
