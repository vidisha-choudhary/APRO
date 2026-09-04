"""Trace provenance builders for decisions, policies, executions, and outcomes."""

from datetime import UTC, datetime
from typing import Any

from apro.audit.models import (
    DecisionTraceRecord,
    ExecutionTraceRecord,
    OutcomeTraceRecord,
    PolicyTraceRecord,
)
from apro.audit.sanitization import TelemetrySanitizer
from apro.domain.models import Execution, Outcome


def build_decision_trace(
    decision: Any,
    cycle_number: int = 1,
    candidate_actions: list[dict[str, Any]] | None = None,
    diagnosis_ref: dict[str, Any] | None = None,
    prediction_refs: list[dict[str, Any]] | None = None,
) -> DecisionTraceRecord:
    """Build a DecisionTraceRecord from an authoritative Decision model
    or event payload.
    """
    if isinstance(decision, dict):
        candidates = candidate_actions or decision.get("candidate_actions", [])
        selected_raw = decision.get("selected_action") or decision.get(
            "recommended_action"
        )
        if selected_raw is not None and hasattr(selected_raw, "value"):
            selected_str = str(selected_raw.value)
        else:
            selected_str = str(selected_raw or "UNKNOWN")
        raw_created = decision.get("created_at") or decision.get("decided_at")
        created: datetime = (
            raw_created if isinstance(raw_created, datetime) else datetime.now(UTC)
        )
        raw_ver = decision.get("model_version") or decision.get(
            "decision_model_version", "1.0.0"
        )
        model_ver = str(raw_ver or "1.0.0")
        return DecisionTraceRecord(
            decision_id=str(decision.get("decision_id", "")),
            case_id=str(decision.get("case_id", decision.get("recovery_case_id", ""))),
            cycle_number=int(decision.get("cycle_number", cycle_number)),
            model_name=str(decision.get("model_name", "decision_engine")),
            model_version=model_ver,
            dataset_version=str(decision.get("dataset_version", "dataset-v1")),
            feature_schema_version=str(decision.get("feature_schema_version", "1.0")),
            input_features_summary=TelemetrySanitizer.sanitize(
                decision.get("input_features_summary", {})
            ),
            diagnosis_ref=TelemetrySanitizer.sanitize(
                diagnosis_ref or decision.get("diagnosis_ref")
            ),
            prediction_refs=TelemetrySanitizer.sanitize(
                prediction_refs or decision.get("prediction_refs", [])
            ),
            candidate_actions=TelemetrySanitizer.sanitize(candidates),
            selected_action=selected_str,
            expected_recovery_value=decision.get("expected_recovery_value"),
            created_at=created,
        )

    meta = getattr(decision, "metadata", {}) or {}
    candidates = candidate_actions or meta.get("candidate_actions", [])
    diag = diagnosis_ref or meta.get("diagnosis_ref")
    preds = prediction_refs or meta.get("prediction_refs", [])

    selected = getattr(decision, "selected_action", None) or getattr(
        decision, "recommended_action", None
    )
    if selected is not None and hasattr(selected, "value"):
        selected_str = str(selected.value)
    else:
        selected_str = str(selected or "UNKNOWN")

    erv = getattr(decision, "expected_recovery_value", None)
    model_name = getattr(decision, "model_name", "decision_engine")
    model_ver = getattr(
        decision, "model_version", getattr(decision, "decision_model_version", "1.0.0")
    )
    dataset_ver = getattr(decision, "dataset_version", "dataset-v1")
    feature_schema_ver = getattr(decision, "feature_schema_version", "1.0")
    raw_created = getattr(decision, "created_at", None) or getattr(
        decision, "decided_at", None
    )
    created = raw_created if isinstance(raw_created, datetime) else datetime.now(UTC)

    return DecisionTraceRecord(
        decision_id=str(getattr(decision, "decision_id", "")),
        case_id=str(
            getattr(decision, "case_id", getattr(decision, "recovery_case_id", ""))
        ),
        cycle_number=cycle_number,
        model_name=model_name,
        model_version=model_ver,
        dataset_version=dataset_ver,
        feature_schema_version=feature_schema_ver,
        input_features_summary=TelemetrySanitizer.sanitize(
            meta.get("input_features_summary", {})
        ),
        diagnosis_ref=TelemetrySanitizer.sanitize(diag),
        prediction_refs=TelemetrySanitizer.sanitize(preds),
        candidate_actions=TelemetrySanitizer.sanitize(candidates),
        selected_action=selected_str,
        expected_recovery_value=erv,
        created_at=created,
    )


def build_policy_trace(policy_decision: Any) -> PolicyTraceRecord:
    """Build a PolicyTraceRecord from an authoritative PolicyDecision model
    or event payload.
    """
    if isinstance(policy_decision, dict):
        raw_rules = policy_decision.get(
            "rules_triggered", policy_decision.get("triggered_rules", [])
        )
        rules = [str(r.value if hasattr(r, "value") else r) for r in (raw_rules or [])]
        raw_outcome = policy_decision.get(
            "policy_outcome", policy_decision.get("result", "UNKNOWN")
        )
        if raw_outcome is not None and hasattr(raw_outcome, "value"):
            outcome_str = str(raw_outcome.value)
        else:
            outcome_str = str(raw_outcome or "UNKNOWN")
        raw_eff = policy_decision.get("effective_action")
        if raw_eff is not None and hasattr(raw_eff, "value"):
            effective_str = str(raw_eff.value)
        else:
            effective_str = str(raw_eff or "UNKNOWN")
        raw_reason = policy_decision.get(
            "reason_code", policy_decision.get("reason", "REASON_UNSPECIFIED")
        )
        if raw_reason is not None and hasattr(raw_reason, "value"):
            reason_str = str(raw_reason.value)
        else:
            reason_str = str(raw_reason or "REASON_UNSPECIFIED")
        raw_created = policy_decision.get("created_at") or policy_decision.get(
            "decided_at"
        )
        created: datetime = (
            raw_created if isinstance(raw_created, datetime) else datetime.now(UTC)
        )
        ruleset_ver = str(
            policy_decision.get(
                "rule_set_version",
                policy_decision.get("ruleset_version", "policy-rules-v1"),
            )
            or "policy-rules-v1"
        )
        approval_req = bool(
            policy_decision.get(
                "approval_required",
                policy_decision.get("requires_human_approval", False),
            )
        )
        return PolicyTraceRecord(
            policy_decision_id=str(policy_decision.get("policy_decision_id", "")),
            case_id=str(policy_decision.get("case_id", "")),
            decision_id=str(policy_decision.get("decision_id", "")),
            policy_version=str(policy_decision.get("policy_version", "1.0.0")),
            ruleset_version=ruleset_ver,
            policy_outcome=outcome_str,
            effective_action=effective_str,
            reason_code=reason_str,
            reason_detail=TelemetrySanitizer.sanitize_string(
                policy_decision.get("reason_detail", policy_decision.get("reason", ""))
                or ""
            ),
            rules_triggered=rules,
            human_approval_required=approval_req,
            approval_id=policy_decision.get(
                "approval_reference", policy_decision.get("human_approval_id")
            ),
            created_at=created,
        )

    raw_rules = getattr(
        policy_decision,
        "rules_triggered",
        getattr(policy_decision, "triggered_rules", []),
    )
    rules = [str(r.value if hasattr(r, "value") else r) for r in (raw_rules or [])]

    raw_outcome = getattr(
        policy_decision, "policy_outcome", getattr(policy_decision, "result", "UNKNOWN")
    )
    if raw_outcome is not None and hasattr(raw_outcome, "value"):
        outcome_str = str(raw_outcome.value)
    else:
        outcome_str = str(raw_outcome or "UNKNOWN")

    raw_eff = getattr(policy_decision, "effective_action", None)
    if raw_eff is not None and hasattr(raw_eff, "value"):
        effective_str = str(raw_eff.value)
    else:
        effective_str = str(raw_eff or "UNKNOWN")

    raw_reason_code = getattr(
        policy_decision,
        "reason_code",
        getattr(policy_decision, "reason", "REASON_UNSPECIFIED"),
    )
    if raw_reason_code is not None and hasattr(raw_reason_code, "value"):
        reason_code_str = str(raw_reason_code.value)
    else:
        reason_code_str = str(raw_reason_code or "REASON_UNSPECIFIED")

    reason_detail = getattr(
        policy_decision,
        "reason_detail",
        getattr(policy_decision, "reason", None),
    )

    ruleset_ver = getattr(
        policy_decision,
        "rule_set_version",
        getattr(policy_decision, "ruleset_version", "policy-rules-v1"),
    )
    approval_req = getattr(
        policy_decision,
        "approval_required",
        getattr(policy_decision, "requires_human_approval", False),
    )
    approval_id = getattr(
        policy_decision,
        "approval_reference",
        getattr(policy_decision, "human_approval_id", None),
    )

    raw_created = getattr(
        policy_decision,
        "created_at",
        getattr(policy_decision, "decided_at", None),
    )
    created = raw_created if isinstance(raw_created, datetime) else datetime.now(UTC)

    return PolicyTraceRecord(
        policy_decision_id=str(getattr(policy_decision, "policy_decision_id", "")),
        case_id=str(getattr(policy_decision, "case_id", "")),
        decision_id=str(getattr(policy_decision, "decision_id", "")),
        policy_version=str(getattr(policy_decision, "policy_version", "1.0.0")),
        ruleset_version=ruleset_ver,
        policy_outcome=outcome_str,
        effective_action=effective_str,
        reason_code=reason_code_str,
        reason_detail=TelemetrySanitizer.sanitize_string(reason_detail or ""),
        rules_triggered=rules,
        human_approval_required=approval_req,
        approval_id=approval_id,
        created_at=created,
    )


def build_execution_trace(execution: Execution) -> ExecutionTraceRecord:
    """Build an ExecutionTraceRecord from an authoritative Execution domain model."""
    duration_ms: float | None = None
    if execution.completed_at and execution.started_at:
        duration_ms = (
            execution.completed_at - execution.started_at
        ).total_seconds() * 1000.0

    return ExecutionTraceRecord(
        execution_id=execution.execution_id,
        case_id=execution.case_id,
        action_id=execution.action_id,
        execution_mode=str(
            execution.execution_mode.value
            if hasattr(execution.execution_mode, "value")
            else execution.execution_mode
        ),
        executor_name=getattr(
            execution, "execution_type", getattr(execution, "executor_name", "UNKNOWN")
        ),
        status=str(
            execution.status.value
            if hasattr(execution.status, "value")
            else execution.status
        ),
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration_ms=duration_ms,
        error_code=execution.error_code,
        provider_reference=TelemetrySanitizer.sanitize_string(
            execution.provider_reference or ""
        ),
    )


def build_outcome_trace(outcome: Outcome) -> OutcomeTraceRecord:
    """Build an OutcomeTraceRecord from an authoritative Outcome domain model."""
    return OutcomeTraceRecord(
        outcome_id=outcome.outcome_id,
        case_id=outcome.case_id,
        execution_id=outcome.execution_id,
        outcome_type=str(
            outcome.type.value if hasattr(outcome.type, "value") else outcome.type
        ),
        amount_recovered=outcome.amount_recovered,
        evidence_reference=TelemetrySanitizer.sanitize_string(
            outcome.evidence_reference or ""
        ),
        provenance="SIMULATOR"
        if "SIMULATOR" in str(outcome.evidence_reference)
        else "RAZORPAY",
        observed_at=outcome.observed_at,
    )
