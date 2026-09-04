"""Configuration schema for APRO Phase 15 evaluation."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.evaluation.enums import (
    BaselineType,
    CensoringPolicy,
    EvaluationConfigVersion,
    MetricSchemaVersion,
    MissingDataPolicy,
    MultipleComparisonPolicy,
)


class CostModelConfig(BaseModel):
    """Action cost configuration in integer minor units (paise)."""

    model_config = ConfigDict(frozen=True)

    retry_cost: int = Field(
        default=100, ge=0, description="Cost of RETRY action in paise (₹1.00)"
    )
    payment_link_cost: int = Field(
        default=200, ge=0, description="Cost of PAYMENT_LINK action in paise (₹2.00)"
    )
    outreach_cost: int = Field(
        default=500, ge=0, description="Cost of OUTREACH action in paise (₹5.00)"
    )
    escalation_cost: int = Field(
        default=1000, ge=0, description="Cost of ESCALATION action in paise (₹10.00)"
    )
    stop_cost: int = Field(
        default=0, ge=0, description="Cost of STOP action in paise (₹0.00)"
    )

    def get_action_cost(self, action_name: str) -> int:
        """Return unit cost for a given recovery action name."""
        clean = str(action_name).upper().replace(" ", "_")
        if "RETRY" in clean:
            return self.retry_cost
        if "LINK" in clean:
            return self.payment_link_cost
        if "OUTREACH" in clean:
            return self.outreach_cost
        if "ESCALAT" in clean:
            return self.escalation_cost
        if "STOP" in clean:
            return self.stop_cost
        return self.retry_cost


class BaselineConfig(BaseModel):
    """Configuration for an individual baseline strategy comparison."""

    model_config = ConfigDict(frozen=True)

    baseline_type: BaselineType
    name: str
    version: str = "1.0.0"
    description: str = ""
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)


def default_baselines() -> list[BaselineConfig]:
    """Default standard benchmark baselines."""
    return [
        BaselineConfig(
            baseline_type=BaselineType.NO_INTERVENTION,
            name="No Intervention",
            description="Always select STOP (no recovery action taken).",
        ),
        BaselineConfig(
            baseline_type=BaselineType.FIXED_RETRY,
            name="Fixed Retry",
            description="Always attempt a single retry where eligible.",
        ),
        BaselineConfig(
            baseline_type=BaselineType.PAYMENT_LINK,
            name="Payment Link",
            description="Always dispatch payment link where eligible.",
        ),
        BaselineConfig(
            baseline_type=BaselineType.FIXED_ESCALATION,
            name="Fixed Escalation",
            description="Always escalate to human operators.",
        ),
    ]


class EvaluationConfig(BaseModel):
    """Complete versioned evaluation configuration."""

    model_config = ConfigDict(frozen=True)

    metric_schema_version: str = Field(default=MetricSchemaVersion.V1_0.value)
    evaluation_config_version: str = Field(default=EvaluationConfigVersion.V1_0.value)
    benchmark_dataset_id: str = Field(default="apro-benchmark-v1")
    observation_window_seconds: int = Field(
        default=86400, ge=60, description="Observation window in seconds (24h default)"
    )
    recovery_definition: str = Field(
        default="authoritative_outcome_recovered",
        description="Definition used to count a case as recovered",
    )
    cost_model: CostModelConfig = Field(default_factory=CostModelConfig)
    baseline_definitions: list[BaselineConfig] = Field(
        default_factory=default_baselines
    )
    confidence_level: float = Field(default=0.95, gt=0.0, lt=1.0)
    bootstrap_iterations: int = Field(default=1000, ge=100)
    bootstrap_seed: int = Field(default=42)
    minimum_cohort_size: int = Field(default=5, ge=1)
    multiple_comparison_policy: MultipleComparisonPolicy = Field(
        default=MultipleComparisonPolicy.HOLM
    )
    censoring_policy: CensoringPolicy = Field(default=CensoringPolicy.RIGHT_CENSOR)
    missing_data_policy: MissingDataPolicy = Field(
        default=MissingDataPolicy.FLAG_INCOMPLETE
    )

    def compute_config_hash(self) -> str:
        """Compute deterministic SHA-256 hash of the configuration."""
        dumped = self.model_dump()
        canonical_json = json.dumps(dumped, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
