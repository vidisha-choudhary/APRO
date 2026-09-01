"""Economic utility calculation and bound validation for Phase 9."""

from apro.dataset.models import ModelInputRecord
from apro.decision.economics import EconomicConfiguration
from apro.decision.enums import (
    RECOVERY_ACTION_ORDER,
    UTILITY_FORMULA_VERSION,
    RecoveryAction,
)
from apro.decision.models import ActionEligibility, ActionUtility
from apro.recovery_prediction.models import OutcomePrediction


class UtilityCalculator:
    """Calculates economic utility and validates prediction bounds."""

    def __init__(
        self,
        utility_version: str = UTILITY_FORMULA_VERSION,
    ) -> None:
        self._utility_version = utility_version

    @property
    def utility_version(self) -> str:
        return self._utility_version

    def compute_action_utility(
        self,
        model_input: ModelInputRecord,
        action: RecoveryAction,
        prediction: OutcomePrediction,
        eligibility: ActionEligibility,
        economic_config: EconomicConfiguration,
    ) -> ActionUtility:
        """Compute complete economic utility for a candidate recovery action."""
        tot_amount = model_input.features.payment_amount
        p_success = prediction.predicted_success_probability
        pred_recovered = prediction.predicted_recovered_amount

        # Strict Recovery Bounds Validation
        if not (0.0 <= p_success <= 1.0):
            msg = (
                f"Invalid predicted success probability {p_success} for action "
                f"'{action.value}'. Must satisfy 0.0 <= p <= 1.0."
            )
            raise ValueError(msg)

        if not (0 <= pred_recovered <= tot_amount):
            msg = (
                f"Invalid predicted recovered amount {pred_recovered} for action "
                f"'{action.value}'. Must satisfy 0 <= v <= {tot_amount}."
            )
            raise ValueError(msg)

        gross, erv, cost_cfg = economic_config.compute_erv(
            action=action,
            predicted_success_probability=p_success,
            predicted_recovered_amount=pred_recovered,
        )

        return ActionUtility(
            action=action,
            eligible=eligibility.is_eligible,
            reason_if_ineligible=eligibility.reason
            if not eligibility.is_eligible
            else None,
            predicted_success_probability=p_success,
            predicted_recovered_amount=pred_recovered,
            expected_gross_recovery=gross,
            action_cost=cost_cfg.action_cost,
            operational_cost=cost_cfg.operational_cost,
            customer_friction_cost=cost_cfg.customer_friction_cost,
            risk_penalty=cost_cfg.risk_penalty,
            expected_recovery_value=erv,
            utility_version=self._utility_version,
        )

    def compute_all_utilities(
        self,
        model_input: ModelInputRecord,
        predictions: dict[RecoveryAction, OutcomePrediction],
        eligibilities: dict[RecoveryAction, ActionEligibility],
        economic_config: EconomicConfiguration,
    ) -> dict[RecoveryAction, ActionUtility]:
        """Compute utility across all 5 candidate actions in deterministic order."""
        utilities: dict[RecoveryAction, ActionUtility] = {}
        for act in RECOVERY_ACTION_ORDER:
            if act not in predictions:
                msg = f"Missing Model B outcome prediction for action '{act.value}'."
                raise ValueError(msg)
            if act not in eligibilities:
                msg = f"Missing policy eligibility result for action '{act.value}'."
                raise ValueError(msg)

            utilities[act] = self.compute_action_utility(
                model_input=model_input,
                action=act,
                prediction=predictions[act],
                eligibility=eligibilities[act],
                economic_config=economic_config,
            )
        return utilities
