"""Sensitivity analysis evaluating decision stability under controlled shocks."""

from pydantic import BaseModel, ConfigDict

from apro.dataset.models import ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import RECOVERY_ACTION_ORDER, RecoveryAction
from apro.decision.models import ActionCostConfig
from apro.diagnosis.models import DiagnosisResult
from apro.recovery_prediction.models import OutcomePrediction


class SensitivityPerturbation(BaseModel):
    """Result of a single controlled parameter perturbation on decision outcome."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    delta_factor: float
    original_decision: RecoveryAction | None = None
    resulting_action: RecoveryAction | None = None
    is_action_switched: bool
    original_erv: int | None = None
    new_erv: int | None = None
    erv_delta: int = 0
    stability_state: str = "STABLE"


class DecisionSensitivityResult(BaseModel):
    """Consolidated sensitivity assessment for a single recovery decision."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    scenario_id: str
    baseline_action: RecoveryAction | None
    baseline_erv: int | None
    is_stable: bool
    perturbations: list[SensitivityPerturbation]


class DecisionSensitivityAnalyzer:
    """Evaluates decision robustness under input and economic parameter shocks."""

    def __init__(
        self,
        engine: EconomicDecisionEngine,
        delta_factors: list[float] | None = None,
    ) -> None:
        self._engine = engine
        self._delta_factors = delta_factors or [-0.20, -0.10, +0.10, +0.20]

    def analyze(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
    ) -> DecisionSensitivityResult:
        """Run sensitivity suite across probability, amount, and cost dimensions."""
        base_decision = self._engine.decide(
            model_input=model_input,
            diagnosis_result=diagnosis_result,
            outcome_predictions=outcome_predictions,
        )
        base_action = base_decision.selected_action
        base_erv = base_decision.expected_recovery_value
        payment_amount = model_input.features.payment_amount

        perturbation_results: list[SensitivityPerturbation] = []
        is_overall_stable = True

        # 1. Perturb Winning Action Success Probability
        if base_action is not None:
            orig_pred = outcome_predictions[base_action]
            for factor in self._delta_factors:
                new_p = max(
                    0.0,
                    min(
                        1.0,
                        orig_pred.predicted_success_probability * (1.0 + factor),
                    ),
                )
                tampered_preds = dict(outcome_predictions)
                tampered_preds[base_action] = orig_pred.model_copy(
                    update={"predicted_success_probability": round(new_p, 4)}
                )

                dec = self._engine.decide(
                    model_input=model_input,
                    diagnosis_result=diagnosis_result,
                    outcome_predictions=tampered_preds,
                )
                switched = dec.selected_action != base_action
                if switched:
                    is_overall_stable = False

                erv_d = (dec.expected_recovery_value or 0) - (base_erv or 0)
                perturbation_results.append(
                    SensitivityPerturbation(
                        dimension="predicted_success_probability",
                        delta_factor=factor,
                        original_decision=base_action,
                        resulting_action=dec.selected_action,
                        is_action_switched=switched,
                        original_erv=base_erv,
                        new_erv=dec.expected_recovery_value,
                        erv_delta=erv_d,
                        stability_state="SENSITIVE" if switched else "STABLE",
                    )
                )

        # 2. Perturb Winning Action Predicted Recovered Amount
        if base_action is not None:
            orig_pred = outcome_predictions[base_action]
            for factor in self._delta_factors:
                new_v = max(
                    0,
                    min(
                        payment_amount,
                        int(
                            round(orig_pred.predicted_recovered_amount * (1.0 + factor))
                        ),
                    ),
                )
                tampered_preds = dict(outcome_predictions)
                tampered_preds[base_action] = orig_pred.model_copy(
                    update={"predicted_recovered_amount": new_v}
                )

                dec = self._engine.decide(
                    model_input=model_input,
                    diagnosis_result=diagnosis_result,
                    outcome_predictions=tampered_preds,
                )
                switched = dec.selected_action != base_action
                if switched:
                    is_overall_stable = False

                erv_d = (dec.expected_recovery_value or 0) - (base_erv or 0)
                perturbation_results.append(
                    SensitivityPerturbation(
                        dimension="predicted_recovered_amount",
                        delta_factor=factor,
                        original_decision=base_action,
                        resulting_action=dec.selected_action,
                        is_action_switched=switched,
                        original_erv=base_erv,
                        new_erv=dec.expected_recovery_value,
                        erv_delta=erv_d,
                        stability_state="SENSITIVE" if switched else "STABLE",
                    )
                )

        # 3. Perturb Action Costs
        for factor in self._delta_factors:
            tampered_costs: dict[RecoveryAction, ActionCostConfig] = {}
            for act in RECOVERY_ACTION_ORDER:
                orig_c = self._engine.economic_config.get_cost_config(act)
                tampered_costs[act] = ActionCostConfig(
                    action_cost=max(0, int(round(orig_c.action_cost * (1.0 + factor)))),
                    operational_cost=orig_c.operational_cost,
                    customer_friction_cost=orig_c.customer_friction_cost,
                    risk_penalty=orig_c.risk_penalty,
                )

            tampered_econ = self._engine.economic_config.model_copy(
                update={"costs_by_action": tampered_costs}
            )
            tampered_engine = EconomicDecisionEngine(
                decision_model_version=self._engine.decision_model_version,
                economic_config=tampered_econ,
                policy_config=self._engine.policy_engine.config,
            )

            dec = tampered_engine.decide(
                model_input=model_input,
                diagnosis_result=diagnosis_result,
                outcome_predictions=outcome_predictions,
            )
            switched = dec.selected_action != base_action
            if switched:
                is_overall_stable = False

            erv_d = (dec.expected_recovery_value or 0) - (base_erv or 0)
            perturbation_results.append(
                SensitivityPerturbation(
                    dimension="action_cost",
                    delta_factor=factor,
                    original_decision=base_action,
                    resulting_action=dec.selected_action,
                    is_action_switched=switched,
                    original_erv=base_erv,
                    new_erv=dec.expected_recovery_value,
                    erv_delta=erv_d,
                    stability_state="SENSITIVE" if switched else "STABLE",
                )
            )

        # 4. Perturb Risk Penalties
        for factor in self._delta_factors:
            tampered_costs = {}
            for act in RECOVERY_ACTION_ORDER:
                orig_c = self._engine.economic_config.get_cost_config(act)
                tampered_costs[act] = ActionCostConfig(
                    action_cost=orig_c.action_cost,
                    operational_cost=orig_c.operational_cost,
                    customer_friction_cost=orig_c.customer_friction_cost,
                    risk_penalty=max(
                        0, int(round(orig_c.risk_penalty * (1.0 + factor)))
                    ),
                )

            tampered_econ = self._engine.economic_config.model_copy(
                update={"costs_by_action": tampered_costs}
            )
            tampered_engine = EconomicDecisionEngine(
                decision_model_version=self._engine.decision_model_version,
                economic_config=tampered_econ,
                policy_config=self._engine.policy_engine.config,
            )

            dec = tampered_engine.decide(
                model_input=model_input,
                diagnosis_result=diagnosis_result,
                outcome_predictions=outcome_predictions,
            )
            switched = dec.selected_action != base_action
            if switched:
                is_overall_stable = False

            erv_d = (dec.expected_recovery_value or 0) - (base_erv or 0)
            perturbation_results.append(
                SensitivityPerturbation(
                    dimension="risk_penalty",
                    delta_factor=factor,
                    original_decision=base_action,
                    resulting_action=dec.selected_action,
                    is_action_switched=switched,
                    original_erv=base_erv,
                    new_erv=dec.expected_recovery_value,
                    erv_delta=erv_d,
                    stability_state="SENSITIVE" if switched else "STABLE",
                )
            )

        # 5. Perturb Minimum Utility Threshold
        for factor in self._delta_factors:
            orig_thresh = self._engine.economic_config.minimum_expected_recovery_value
            new_thresh = max(0, int(round(orig_thresh * (1.0 + factor))))

            tampered_econ = self._engine.economic_config.model_copy(
                update={"minimum_expected_recovery_value": new_thresh}
            )
            tampered_engine = EconomicDecisionEngine(
                decision_model_version=self._engine.decision_model_version,
                economic_config=tampered_econ,
                policy_config=self._engine.policy_engine.config,
            )

            dec = tampered_engine.decide(
                model_input=model_input,
                diagnosis_result=diagnosis_result,
                outcome_predictions=outcome_predictions,
            )
            switched = dec.selected_action != base_action
            if switched:
                is_overall_stable = False

            erv_d = (dec.expected_recovery_value or 0) - (base_erv or 0)
            perturbation_results.append(
                SensitivityPerturbation(
                    dimension="minimum_utility_threshold",
                    delta_factor=factor,
                    original_decision=base_action,
                    resulting_action=dec.selected_action,
                    is_action_switched=switched,
                    original_erv=base_erv,
                    new_erv=dec.expected_recovery_value,
                    erv_delta=erv_d,
                    stability_state="SENSITIVE" if switched else "STABLE",
                )
            )

        return DecisionSensitivityResult(
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            baseline_action=base_action,
            baseline_erv=base_erv,
            is_stable=is_overall_stable,
            perturbations=perturbation_results,
        )
