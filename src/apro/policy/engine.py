"""Deterministic Policy & Safety Engine evaluating governance rules
according to strict precedence.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any

from apro.decision.models import RecoveryDecision
from apro.domain.models import Payment, RecoveryCase
from apro.policy.approvals import validate_human_approval
from apro.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig
from apro.policy.enums import (
    POLICY_DECISION_SCHEMA_VERSION,
    POLICY_TRACE_SCHEMA_VERSION,
    PolicyOutcome,
    PolicyReasonCode,
    RulePrecedenceLevel,
)
from apro.policy.idempotency import generate_idempotency_key
from apro.policy.models import (
    ActionExecutionHistory,
    ApprovalRecord,
    EventTrustState,
    PolicyDecision,
)
from apro.policy.rules import (
    DEFAULT_RULE_REGISTRY,
    PolicyRuleContext,
    PolicyRuleRegistry,
    RuleEvaluationResult,
)
from apro.policy.traces import PolicyEvaluationTrace
from apro.policy.validation import validate_entity_binding
from apro.recovery_prediction.enums import RecoveryAction


def compute_policy_decision_id(
    case_id: str,
    payment_id: str,
    decision_id: str | None,
    requested_action: RecoveryAction | None,
    outcome: PolicyOutcome,
    effective_action: RecoveryAction | None,
    reason_code: PolicyReasonCode,
    policy_version: str,
    rule_set_version: str,
    action_schema_version: str,
    policy_config_identity: str | None,
    idempotency_key: str | None,
    approval_reference: str | None,
    dataset_version: str | None,
) -> str:
    """Generate a deterministic, reproducible SHA-256 identifier for a decision."""
    canonical_payload: dict[str, Any] = {
        "case_id": case_id,
        "payment_id": payment_id,
        "decision_id": decision_id or "",
        "requested_action": requested_action.value if requested_action else "",
        "outcome": outcome.value,
        "effective_action": effective_action.value if effective_action else "",
        "reason_code": reason_code.value,
        "policy_version": policy_version,
        "rule_set_version": rule_set_version,
        "action_schema_version": action_schema_version,
        "policy_config_identity": policy_config_identity or "",
        "idempotency_key": idempotency_key or "",
        "approval_reference": approval_reference or "",
        "dataset_version": dataset_version or "",
    }
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]


class PolicyEngine:
    """Deterministic governance and safety engine enforcing policy limits."""

    def __init__(
        self,
        registry: PolicyRuleRegistry = DEFAULT_RULE_REGISTRY,
        default_config: PolicyConfig = DEFAULT_POLICY_CONFIG,
    ) -> None:
        self._registry = registry
        self._default_config = default_config

    def evaluate(
        self,
        decision: RecoveryDecision,
        payment: Payment,
        case: RecoveryCase,
        current_time: datetime,
        config: PolicyConfig | None = None,
        history: ActionExecutionHistory | None = None,
        event_trust: EventTrustState | bool | str | None = None,
        is_duplicate_event: bool = False,
        event_timestamp: datetime | None = None,
        approval: ApprovalRecord | None = None,
        model_a_failed: bool = False,
        model_b_failed: bool = False,
    ) -> tuple[PolicyDecision, PolicyEvaluationTrace]:
        """Evaluate candidate decision against all policy and safety rules."""
        if current_time is None:
            msg = (
                "Explicit current_time must be provided for "
                "deterministic policy evaluation."
            )
            raise ValueError(msg)
        start_ns = time.perf_counter_ns()
        active_config = config or self._default_config
        active_history = history or ActionExecutionHistory()
        eval_time = current_time

        # Entity binding pre-check
        valid_binding, binding_error = validate_entity_binding(payment, case, decision)

        requested_action = decision.selected_action

        # Generate canonical idempotency key
        idempotency_key: str | None = None
        if requested_action is not None:
            attempt_num = case.current_attempt_count + 1
            idempotency_key = generate_idempotency_key(
                case.case_id, requested_action, attempt_num
            )

        # Build context
        ctx = PolicyRuleContext(
            decision=decision,
            payment=payment,
            case=case,
            config=active_config,
            history=active_history,
            event_trust=event_trust,
            is_duplicate_event=is_duplicate_event,
            event_timestamp=event_timestamp,
            approval=approval,
            current_time=eval_time,
            idempotency_key=idempotency_key,
            model_a_failed=model_a_failed,
            model_b_failed=model_b_failed,
            entity_binding_valid=valid_binding,
            entity_binding_error=binding_error,
        )

        # Evaluate all registered rules
        rule_results: tuple[RuleEvaluationResult, ...] = self._registry.evaluate_all(
            ctx
        )
        rules_evaluated = tuple(r.rule_id.value for r in rule_results)
        triggered_results = tuple(r for r in rule_results if r.triggered)
        rules_triggered = tuple(r.rule_id.value for r in triggered_results)

        # Precedence resolution
        if not triggered_results:
            # No rule triggered -> ALLOW
            final_outcome = PolicyOutcome.ALLOW
            final_reason_code = PolicyReasonCode.POLICY_ALLOWED
            reason_detail = "All policy, safety, and operational constraints satisfied."
            approval_required = False
            approval_ref = None
            reconciliation_required = False
            effective_action = requested_action
        else:
            # Sort triggered rules by precedence (lower = higher priority)
            sorted_triggered = sorted(
                triggered_results, key=lambda r: r.precedence.value
            )
            top_rule = sorted_triggered[0]

            if top_rule.precedence == RulePrecedenceLevel.HUMAN_APPROVAL_REQUIREMENT:
                # Human approval requirement triggered: verify token
                appr_valid, appr_reason, appr_detail = validate_human_approval(
                    approval=approval,
                    case_id=case.case_id,
                    decision_id=decision.decision_id,
                    requested_action=requested_action,
                    current_time=eval_time,
                    expected_policy_version=active_config.policy_version,
                    executed_approval_ids=active_history.executed_approval_ids,
                )
                if appr_valid and approval is not None:
                    # Valid approval supplied -> authorized
                    final_outcome = PolicyOutcome.ALLOW
                    final_reason_code = PolicyReasonCode.POLICY_ALLOWED
                    appr_ts = approval.approved_at.isoformat()
                    reason_detail = (
                        f"Human approval verified (approved by "
                        f"{approval.approver_reference} at {appr_ts}). "
                        f"{top_rule.detail}"
                    )
                    approval_required = True
                    approval_ref = approval.approval_id
                    reconciliation_required = False
                    effective_action = requested_action
                elif appr_reason in (
                    PolicyReasonCode.APPROVAL_MISMATCH,
                    PolicyReasonCode.APPROVAL_EXPIRED,
                ):
                    # Invalid, expired, or replayed approval -> hard BLOCK
                    final_outcome = PolicyOutcome.BLOCK
                    final_reason_code = appr_reason
                    reason_detail = (
                        appr_detail
                        or f"Approval verification failed: {appr_reason.value}"
                    )
                    approval_required = True
                    approval_ref = approval.approval_id if approval else None
                    reconciliation_required = False
                    effective_action = None
                else:
                    # No approval provided -> REQUIRE_HUMAN_APPROVAL
                    final_outcome = PolicyOutcome.REQUIRE_HUMAN_APPROVAL
                    final_reason_code = top_rule.reason_code
                    reason_detail = top_rule.detail
                    approval_required = True
                    approval_ref = None
                    reconciliation_required = False
                    effective_action = None
            elif top_rule.outcome == PolicyOutcome.BLOCK:
                final_outcome = PolicyOutcome.BLOCK
                final_reason_code = top_rule.reason_code
                reason_detail = top_rule.detail
                approval_required = False
                approval_ref = None
                reconciliation_required = (
                    top_rule.reason_code == PolicyReasonCode.RECONCILIATION_REQUIRED
                )
                effective_action = None
            else:
                final_outcome = top_rule.outcome
                final_reason_code = top_rule.reason_code
                reason_detail = top_rule.detail
                approval_required = (
                    final_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
                )
                approval_ref = approval.approval_id if approval else None
                reconciliation_required = (
                    top_rule.reason_code == PolicyReasonCode.RECONCILIATION_REQUIRED
                )
                effective_action = (
                    requested_action if final_outcome == PolicyOutcome.ALLOW else None
                )

        latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

        pol_config_ident = active_config.compute_deterministic_identity()
        policy_decision_id = compute_policy_decision_id(
            case_id=case.case_id,
            payment_id=payment.payment_id,
            decision_id=decision.decision_id,
            requested_action=requested_action,
            outcome=final_outcome,
            effective_action=effective_action,
            reason_code=final_reason_code,
            policy_version=active_config.policy_version,
            rule_set_version=active_config.rule_set_version,
            action_schema_version=active_config.action_schema_version,
            policy_config_identity=pol_config_ident,
            idempotency_key=idempotency_key,
            approval_reference=approval_ref,
            dataset_version=decision.dataset_version,
        )

        event_trust_val = (
            EventTrustState.TRUSTED.value
            if event_trust in (True, EventTrustState.TRUSTED, "TRUSTED")
            else EventTrustState.UNTRUSTED.value
        )

        pol_dec = PolicyDecision(
            policy_decision_id=policy_decision_id,
            case_id=case.case_id,
            payment_id=payment.payment_id,
            event_id=None,
            decision_id=decision.decision_id,
            requested_action=requested_action,
            policy_outcome=final_outcome,
            effective_action=effective_action,
            reason_code=final_reason_code,
            reason_detail=reason_detail,
            approval_required=approval_required,
            approval_reference=approval_ref,
            reconciliation_required=reconciliation_required,
            defer_until=None,
            idempotency_key=idempotency_key,
            rules_evaluated=rules_evaluated,
            rules_triggered=rules_triggered,
            payment_state_observed=payment.status,
            event_trust_state=event_trust_val,
            model_output_valid=(
                valid_binding
                and "H5_INVALID_MODEL_OUTPUT" not in rules_triggered
                and "M1_MODEL_A_FAILURE" not in rules_triggered
                and "M2_MODEL_B_FAILURE" not in rules_triggered
            ),
            policy_version=active_config.policy_version,
            rule_set_version=active_config.rule_set_version,
            action_schema_version=active_config.action_schema_version,
            decision_schema_version=POLICY_DECISION_SCHEMA_VERSION,
            decision_model_version=decision.diagnosis_model_version,
            diagnosis_model_version=decision.diagnosis_model_version,
            outcome_model_version=decision.outcome_model_version,
            dataset_version=decision.dataset_version,
            evaluation_run_id=None,
            provenance={
                "rules_evaluated_count": len(rules_evaluated),
                "rules_triggered_count": len(rules_triggered),
                "top_precedence_level": sorted_triggered[0].precedence.value
                if triggered_results
                else RulePrecedenceLevel.ALLOW.value,
                "policy_config_identity": pol_config_ident,
            },
            created_at=eval_time,
        )

        trace = PolicyEvaluationTrace(
            policy_decision_id=policy_decision_id,
            case_id=case.case_id,
            payment_id=payment.payment_id,
            event_id=None,
            decision_id=decision.decision_id,
            requested_action=requested_action,
            policy_outcome=final_outcome,
            effective_action=effective_action,
            payment_state=payment.status.value,
            event_trust_state=event_trust_val,
            model_output_valid=pol_dec.model_output_valid,
            rules_evaluated=rules_evaluated,
            rules_triggered=rules_triggered,
            final_reason_code=final_reason_code,
            reason_detail=reason_detail,
            approval_required=approval_required,
            approval_reference=approval_ref,
            reconciliation_required=reconciliation_required,
            idempotency_key=idempotency_key,
            policy_version=active_config.policy_version,
            rule_set_version=active_config.rule_set_version,
            action_schema_version=active_config.action_schema_version,
            decision_schema_version=POLICY_DECISION_SCHEMA_VERSION,
            trace_schema_version=POLICY_TRACE_SCHEMA_VERSION,
            decision_model_version=decision.diagnosis_model_version,
            diagnosis_model_version=decision.diagnosis_model_version,
            outcome_model_version=decision.outcome_model_version,
            dataset_version=decision.dataset_version,
            evaluation_run_id=None,
            evaluated_at=eval_time,
            evaluation_latency_ms=latency_ms,
        )

        return pol_dec, trace


__all__ = [
    "PolicyEngine",
    "compute_policy_decision_id",
]
