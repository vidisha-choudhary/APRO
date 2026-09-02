"""APRO Phase 10 — Policy & Safety Engine."""

from apro.policy.approvals import validate_human_approval
from apro.policy.artifacts import (
    PolicyArtifact,
    build_policy_artifact,
    load_policy_artifact,
    save_policy_artifact,
)
from apro.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig
from apro.policy.engine import PolicyEngine, compute_policy_decision_id
from apro.policy.enums import (
    POLICY_ARTIFACT_SCHEMA_VERSION,
    POLICY_DECISION_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    POLICY_TRACE_SCHEMA_VERSION,
    POLICY_VERSION,
    RULE_SET_VERSION,
    PolicyOutcome,
    PolicyReasonCode,
    RuleId,
    RulePrecedenceLevel,
)
from apro.policy.evaluation import (
    ErrorAnalysisCase,
    PolicyErrorAnalysisReport,
    PolicySafetyMetrics,
    compare_distribution_shift,
    evaluate_policy_on_dataset,
    evaluate_policy_segments,
    perform_policy_error_analysis,
)
from apro.policy.idempotency import (
    build_idempotency_identity,
    generate_idempotency_key,
    is_idempotency_conflict,
)
from apro.policy.models import (
    ActionExecutionHistory,
    ApprovalRecord,
    EventTrustState,
    IdempotencyIdentity,
    PolicyDecision,
)
from apro.policy.reports import (
    export_policy_metrics_json,
    format_policy_markdown_report,
)
from apro.policy.rules import (
    ALL_RULES,
    DEFAULT_RULE_REGISTRY,
    PolicyRuleContext,
    PolicyRuleRegistry,
    RuleEvaluationResult,
)
from apro.policy.state_guard import (
    StateGuard,
    check_pre_execution_state_gate,
    is_payment_captured,
    is_payment_recoverable,
    is_stale_or_inconsistent_event,
)
from apro.policy.traces import PolicyEvaluationTrace
from apro.policy.validation import (
    is_action_supported,
    is_valid_currency_amount,
    is_valid_probability,
    validate_event_trust,
    validate_recovery_decision_model_output,
)

__all__ = [
    "ALL_RULES",
    "DEFAULT_POLICY_CONFIG",
    "DEFAULT_RULE_REGISTRY",
    "ErrorAnalysisCase",
    "POLICY_ARTIFACT_SCHEMA_VERSION",
    "POLICY_DECISION_SCHEMA_VERSION",
    "POLICY_SCHEMA_VERSION",
    "POLICY_TRACE_SCHEMA_VERSION",
    "POLICY_VERSION",
    "RULE_SET_VERSION",
    "ActionExecutionHistory",
    "ApprovalRecord",
    "EventTrustState",
    "IdempotencyIdentity",
    "PolicyArtifact",
    "PolicyConfig",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyErrorAnalysisReport",
    "PolicyEvaluationTrace",
    "PolicyOutcome",
    "PolicyReasonCode",
    "PolicyRuleContext",
    "PolicyRuleRegistry",
    "PolicySafetyMetrics",
    "RuleEvaluationResult",
    "RuleId",
    "RulePrecedenceLevel",
    "StateGuard",
    "build_idempotency_identity",
    "build_policy_artifact",
    "check_pre_execution_state_gate",
    "compare_distribution_shift",
    "compute_policy_decision_id",
    "evaluate_policy_on_dataset",
    "evaluate_policy_segments",
    "export_policy_metrics_json",
    "format_policy_markdown_report",
    "generate_idempotency_key",
    "is_action_supported",
    "is_idempotency_conflict",
    "is_payment_captured",
    "is_payment_recoverable",
    "is_stale_or_inconsistent_event",
    "is_valid_currency_amount",
    "is_valid_probability",
    "load_policy_artifact",
    "perform_policy_error_analysis",
    "save_policy_artifact",
    "validate_event_trust",
    "validate_human_approval",
    "validate_recovery_decision_model_output",
]
