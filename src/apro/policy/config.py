"""Immutable, validated configuration contract for Phase 10 Policy Engine."""

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.policy.enums import (
    POLICY_SCHEMA_VERSION,
    POLICY_VERSION,
    RULE_SET_VERSION,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_SCHEMA_VERSION,
)


class PolicyConfig(BaseModel):
    """Immutable policy configuration defining thresholds, limits, and rules."""

    model_config = ConfigDict(frozen=True)

    policy_version: str = Field(default=POLICY_VERSION)
    policy_schema_version: str = Field(default=POLICY_SCHEMA_VERSION)
    rule_set_version: str = Field(default=RULE_SET_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)

    # Operational Limits & Thresholds (monetary values in minor units / paise)
    max_retries: int = Field(default=3, ge=0)
    retry_cooldown_seconds: int = Field(default=300, ge=0)
    max_same_action_repetitions: int = Field(default=2, ge=1)
    max_total_interventions: int = Field(default=4, ge=1)
    high_value_threshold: int = Field(default=100000, ge=0)  # 100,000 paise = 1,000 INR
    min_diagnosis_confidence: float = Field(default=0.50, ge=0.0, le=1.0)
    min_outcome_confidence: float = Field(default=0.50, ge=0.0, le=1.0)
    min_decision_confidence: float = Field(default=0.50, ge=0.0, le=1.0)
    min_expected_recovery_value: int = Field(default=100, ge=0)  # 100 paise = 1 INR
    max_payment_link_creations: int = Field(default=2, ge=1)
    approval_expiry_seconds: int = Field(default=86400, ge=0)  # 24 hours

    # Behavior Policies
    stale_event_policy: str = "BLOCK"
    unknown_state_policy: str = "RECONCILIATION_REQUIRED"
    model_failure_policy: str = "STOP"
    unsupported_action_policy: str = "BLOCK"
    negative_erv_policy: str = "BLOCK"
    precedence_configuration: tuple[str, ...] = (
        "HARD_SAFETY",
        "STALE_STATE",
        "UNSUPPORTED_ACTION",
        "LIMITS",
        "INVALID_MODEL",
        "ECONOMIC_GUARDRAILS",
        "HUMAN_APPROVAL",
        "ALLOW",
    )
    effective_at: datetime | None = None

    def compute_deterministic_identity(self) -> str:
        """Compute stable SHA-256 hash identity of canonical configuration."""
        canonical_data: dict[str, Any] = {
            "policy_version": self.policy_version,
            "policy_schema_version": self.policy_schema_version,
            "rule_set_version": self.rule_set_version,
            "action_schema_version": self.action_schema_version,
            "max_retries": self.max_retries,
            "retry_cooldown_seconds": self.retry_cooldown_seconds,
            "max_same_action_repetitions": self.max_same_action_repetitions,
            "max_total_interventions": self.max_total_interventions,
            "high_value_threshold": self.high_value_threshold,
            "min_diagnosis_confidence": self.min_diagnosis_confidence,
            "min_outcome_confidence": self.min_outcome_confidence,
            "min_decision_confidence": self.min_decision_confidence,
            "min_expected_recovery_value": self.min_expected_recovery_value,
            "max_payment_link_creations": self.max_payment_link_creations,
            "approval_expiry_seconds": self.approval_expiry_seconds,
            "stale_event_policy": self.stale_event_policy,
            "unknown_state_policy": self.unknown_state_policy,
            "model_failure_policy": self.model_failure_policy,
            "unsupported_action_policy": self.unsupported_action_policy,
            "negative_erv_policy": self.negative_erv_policy,
            "precedence_configuration": list(self.precedence_configuration),
        }
        serialized = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary."""
        data = self.model_dump()
        if self.effective_at:
            data["effective_at"] = self.effective_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyConfig":
        """Deserialize configuration from dictionary with type coercion."""
        cleaned = dict(data)
        if "effective_at" in cleaned and isinstance(cleaned["effective_at"], str):
            cleaned["effective_at"] = datetime.fromisoformat(cleaned["effective_at"])
        if "precedence_configuration" in cleaned and isinstance(
            cleaned["precedence_configuration"], list
        ):
            cleaned["precedence_configuration"] = tuple(
                cleaned["precedence_configuration"]
            )
        return cls(**cleaned)


DEFAULT_POLICY_CONFIG = PolicyConfig()

__all__ = ["DEFAULT_POLICY_CONFIG", "PolicyConfig"]
