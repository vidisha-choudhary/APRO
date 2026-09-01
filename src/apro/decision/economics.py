"""Economic configuration, cost modeling, and ERV calculations for APRO Phase 9."""

from pydantic import BaseModel, ConfigDict, Field

from apro.decision.enums import (
    DEFAULT_TIE_BREAK_ORDER,
    ECONOMIC_CONFIG_SCHEMA_VERSION,
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)
from apro.decision.models import ActionCostConfig


def get_default_action_costs() -> dict[RecoveryAction, ActionCostConfig]:
    """Provide standard action cost parameters in minor units (paise)."""
    return {
        RecoveryAction.RETRY: ActionCostConfig(
            action_cost=500,  # Rs 5.00
            operational_cost=200,  # Rs 2.00
            customer_friction_cost=300,  # Rs 3.00
            risk_penalty=200,  # Rs 2.00
        ),
        RecoveryAction.PAYMENT_LINK: ActionCostConfig(
            action_cost=1000,  # Rs 10.00
            operational_cost=500,  # Rs 5.00
            customer_friction_cost=1500,  # Rs 15.00
            risk_penalty=500,  # Rs 5.00
        ),
        RecoveryAction.OUTREACH: ActionCostConfig(
            action_cost=3000,  # Rs 30.00
            operational_cost=2000,  # Rs 20.00
            customer_friction_cost=5000,  # Rs 50.00
            risk_penalty=1000,  # Rs 10.00
        ),
        RecoveryAction.STOP: ActionCostConfig(
            action_cost=0,
            operational_cost=0,
            customer_friction_cost=0,
            risk_penalty=0,
        ),
        RecoveryAction.ESCALATE: ActionCostConfig(
            action_cost=5000,  # Rs 50.00
            operational_cost=3000,  # Rs 30.00
            customer_friction_cost=0,
            risk_penalty=0,
        ),
    }


class EconomicConfiguration(BaseModel):
    """Declarative versioned economic configuration for recovery evaluation."""

    model_config = ConfigDict(frozen=True)

    config_version: str = Field(default=ECONOMIC_CONFIG_SCHEMA_VERSION)
    costs_by_action: dict[RecoveryAction, ActionCostConfig] = Field(
        default_factory=get_default_action_costs
    )
    minimum_expected_recovery_value: int = Field(default=0)
    utility_tolerance: int = Field(default=0, ge=0)
    tie_break_order: list[RecoveryAction] = Field(
        default_factory=lambda: list(DEFAULT_TIE_BREAK_ORDER)
    )

    def get_cost_config(self, action: RecoveryAction) -> ActionCostConfig:
        """Retrieve cost configuration for a given action."""
        if action in self.costs_by_action:
            return self.costs_by_action[action]
        return ActionCostConfig()

    def compute_gross_recovery(
        self,
        predicted_success_probability: float,
        predicted_recovered_amount: int,
    ) -> int:
        """Compute expected gross recovery in paise."""
        if predicted_success_probability <= 0.0 or predicted_recovered_amount <= 0:
            return 0
        gross = predicted_success_probability * predicted_recovered_amount
        return int(round(gross))

    def compute_erv(
        self,
        action: RecoveryAction,
        predicted_success_probability: float,
        predicted_recovered_amount: int,
    ) -> tuple[int, int, ActionCostConfig]:
        """Compute expected gross recovery, ERV, and cost decomposition."""
        cost_cfg = self.get_cost_config(action)
        gross = self.compute_gross_recovery(
            predicted_success_probability,
            predicted_recovered_amount,
        )
        erv = gross - cost_cfg.total_cost
        return gross, erv, cost_cfg

    def validate_action_coverage(self) -> None:
        """Verify all supported actions are covered by cost configuration."""
        for act in RECOVERY_ACTION_ORDER:
            if act not in self.costs_by_action:
                msg = f"Missing cost configuration for action '{act.value}'."
                raise ValueError(msg)
