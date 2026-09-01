"""Non-economic and heuristic baseline decision strategies for APRO Phase 9."""

from abc import ABC, abstractmethod
from typing import Any

from apro.dataset.models import ModelInputRecord
from apro.decision.economics import EconomicConfiguration
from apro.decision.eligibility import (
    PolicyConfiguration,
    PolicyEligibilityEngine,
)
from apro.decision.enums import (
    DECISION_MODEL_SCHEMA_VERSION,
    RECOVERY_ACTION_ORDER,
    DecisionStatus,
    RecoveryAction,
)
from apro.decision.models import RecoveryDecision
from apro.decision.utility import UtilityCalculator
from apro.diagnosis.enums import DiagnosisCategory
from apro.diagnosis.models import DiagnosisResult
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import SimulatedPaymentMethod


class BaseDecisionModel(ABC):
    """Abstract interface for all recovery decision strategies and baselines."""

    def __init__(
        self,
        model_name: str,
        decision_model_version: str = DECISION_MODEL_SCHEMA_VERSION,
        policy_config: PolicyConfiguration | None = None,
        economic_config: EconomicConfiguration | None = None,
    ) -> None:
        self._model_name = model_name
        self._decision_model_version = decision_model_version
        self._policy_engine = PolicyEligibilityEngine(policy_config)
        self._economic_config = economic_config or EconomicConfiguration()
        self._utility_calculator = UtilityCalculator()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def decision_model_version(self) -> str:
        return self._decision_model_version

    @property
    def policy_engine(self) -> PolicyEligibilityEngine:
        return self._policy_engine

    @property
    def economic_config(self) -> EconomicConfiguration:
        return self._economic_config

    @abstractmethod
    def decide(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
        recovery_case_id: str | None = None,
        evaluation_run_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        """Produce a RecoveryDecision for the context."""


class NoInterventionBaseline(BaseDecisionModel):
    """Baseline 0: Passive no-intervention strategy always selecting STOP."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(model_name="No Intervention (STOP)", **kwargs)

    def decide(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
        recovery_case_id: str | None = None,
        evaluation_run_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        eligibilities = self._policy_engine.evaluate_all_actions(
            model_input=model_input,
            diagnosis_result=diagnosis_result,
        )
        utilities = self._utility_calculator.compute_all_utilities(
            model_input=model_input,
            predictions=outcome_predictions,
            eligibilities=eligibilities,
            economic_config=self._economic_config,
        )
        stop_u = utilities[RecoveryAction.STOP]

        return RecoveryDecision(
            decision_id=f"dec_stop_{model_input.record_id[:12]}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            recovery_case_id=recovery_case_id,
            selected_action=RecoveryAction.STOP,
            decision_status=DecisionStatus.ACTION_SELECTED,
            expected_recovery_value=stop_u.expected_recovery_value,
            expected_gross_recovery=stop_u.expected_gross_recovery,
            expected_cost=stop_u.total_cost,
            utility_by_action=utilities,
            eligibility_by_action=eligibilities,
            decision_confidence=1.0,
            rationale="Baseline 0: Always select STOP (no active intervention).",
            decision_latency_ms=0.0,
            diagnosis_model_version=diagnosis_result.model_version
            if diagnosis_result
            else "unknown",
            outcome_model_version=outcome_predictions[
                RecoveryAction.STOP
            ].model_version,
            policy_version=self._policy_engine.config.policy_version,
            economic_config_version=self._economic_config.config_version,
            decision_model_version=self._decision_model_version,
            dataset_version=model_input.dataset_version,
            evaluation_run_id=evaluation_run_id,
            provenance=provenance or {},
        )


class HighestSuccessProbabilityBaseline(BaseDecisionModel):
    """Baseline 1: Selects eligible action with highest P(success)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(model_name="Highest Predicted Success Probability", **kwargs)

    def decide(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
        recovery_case_id: str | None = None,
        evaluation_run_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        eligibilities = self._policy_engine.evaluate_all_actions(
            model_input=model_input,
            diagnosis_result=diagnosis_result,
        )
        utilities = self._utility_calculator.compute_all_utilities(
            model_input=model_input,
            predictions=outcome_predictions,
            eligibilities=eligibilities,
            economic_config=self._economic_config,
        )

        eligible_actions = [
            act for act in RECOVERY_ACTION_ORDER if eligibilities[act].is_eligible
        ]
        if not eligible_actions:
            return RecoveryDecision(
                decision_id=f"dec_noelig_{model_input.record_id[:12]}",
                record_id=model_input.record_id,
                scenario_id=model_input.scenario_id,
                recovery_case_id=recovery_case_id,
                selected_action=None,
                decision_status=DecisionStatus.NO_ELIGIBLE_ACTION,
                expected_recovery_value=None,
                expected_gross_recovery=None,
                expected_cost=None,
                utility_by_action=utilities,
                eligibility_by_action=eligibilities,
                decision_confidence=0.0,
                rationale="No eligible actions under policy.",
                decision_latency_ms=0.0,
                diagnosis_model_version=diagnosis_result.model_version
                if diagnosis_result
                else "unknown",
                outcome_model_version=outcome_predictions[
                    RecoveryAction.STOP
                ].model_version,
                policy_version=self._policy_engine.config.policy_version,
                economic_config_version=self._economic_config.config_version,
                decision_model_version=self._decision_model_version,
                dataset_version=model_input.dataset_version,
                evaluation_run_id=evaluation_run_id,
                provenance=provenance or {},
            )

        # Select highest P(success) among eligible actions
        winning_action = max(
            eligible_actions,
            key=lambda a: outcome_predictions[a].predicted_success_probability,
        )
        winner_u = utilities[winning_action]
        p_str = f"{winner_u.predicted_success_probability:.2%}"

        return RecoveryDecision(
            decision_id=f"dec_maxp_{model_input.record_id[:12]}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            recovery_case_id=recovery_case_id,
            selected_action=winning_action,
            decision_status=DecisionStatus.ACTION_SELECTED,
            expected_recovery_value=winner_u.expected_recovery_value,
            expected_gross_recovery=winner_u.expected_gross_recovery,
            expected_cost=winner_u.total_cost,
            utility_by_action=utilities,
            eligibility_by_action=eligibilities,
            decision_confidence=winner_u.predicted_success_probability,
            rationale=(
                f"Baseline 1: Selected '{winning_action.value}' with highest "
                f"P(Success) {p_str}."
            ),
            decision_latency_ms=0.0,
            diagnosis_model_version=diagnosis_result.model_version
            if diagnosis_result
            else "unknown",
            outcome_model_version=outcome_predictions[
                RecoveryAction.STOP
            ].model_version,
            policy_version=self._policy_engine.config.policy_version,
            economic_config_version=self._economic_config.config_version,
            decision_model_version=self._decision_model_version,
            dataset_version=model_input.dataset_version,
            evaluation_run_id=evaluation_run_id,
            provenance=provenance or {},
        )


class HighestRecoveryAmountBaseline(BaseDecisionModel):
    """Baseline 2: Selects eligible action with highest predicted amount."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(model_name="Highest Predicted Recovery Amount", **kwargs)

    def decide(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
        recovery_case_id: str | None = None,
        evaluation_run_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        eligibilities = self._policy_engine.evaluate_all_actions(
            model_input=model_input,
            diagnosis_result=diagnosis_result,
        )
        utilities = self._utility_calculator.compute_all_utilities(
            model_input=model_input,
            predictions=outcome_predictions,
            eligibilities=eligibilities,
            economic_config=self._economic_config,
        )

        eligible_actions = [
            act for act in RECOVERY_ACTION_ORDER if eligibilities[act].is_eligible
        ]
        if not eligible_actions:
            return RecoveryDecision(
                decision_id=f"dec_noelig_{model_input.record_id[:12]}",
                record_id=model_input.record_id,
                scenario_id=model_input.scenario_id,
                recovery_case_id=recovery_case_id,
                selected_action=None,
                decision_status=DecisionStatus.NO_ELIGIBLE_ACTION,
                expected_recovery_value=None,
                expected_gross_recovery=None,
                expected_cost=None,
                utility_by_action=utilities,
                eligibility_by_action=eligibilities,
                decision_confidence=0.0,
                rationale="No eligible actions under policy.",
                decision_latency_ms=0.0,
                diagnosis_model_version=diagnosis_result.model_version
                if diagnosis_result
                else "unknown",
                outcome_model_version=outcome_predictions[
                    RecoveryAction.STOP
                ].model_version,
                policy_version=self._policy_engine.config.policy_version,
                economic_config_version=self._economic_config.config_version,
                decision_model_version=self._decision_model_version,
                dataset_version=model_input.dataset_version,
                evaluation_run_id=evaluation_run_id,
                provenance=provenance or {},
            )

        winning_action = max(
            eligible_actions,
            key=lambda a: outcome_predictions[a].predicted_recovered_amount,
        )
        winner_u = utilities[winning_action]
        rec_rs = winner_u.predicted_recovered_amount / 100

        return RecoveryDecision(
            decision_id=f"dec_maxv_{model_input.record_id[:12]}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            recovery_case_id=recovery_case_id,
            selected_action=winning_action,
            decision_status=DecisionStatus.ACTION_SELECTED,
            expected_recovery_value=winner_u.expected_recovery_value,
            expected_gross_recovery=winner_u.expected_gross_recovery,
            expected_cost=winner_u.total_cost,
            utility_by_action=utilities,
            eligibility_by_action=eligibilities,
            decision_confidence=winner_u.predicted_success_probability,
            rationale=(
                f"Baseline 2: Selected '{winning_action.value}' with highest predicted "
                f"recovered amount Rs {rec_rs:.2f}."
            ),
            decision_latency_ms=0.0,
            diagnosis_model_version=diagnosis_result.model_version
            if diagnosis_result
            else "unknown",
            outcome_model_version=outcome_predictions[
                RecoveryAction.STOP
            ].model_version,
            policy_version=self._policy_engine.config.policy_version,
            economic_config_version=self._economic_config.config_version,
            decision_model_version=self._decision_model_version,
            dataset_version=model_input.dataset_version,
            evaluation_run_id=evaluation_run_id,
            provenance=provenance or {},
        )


class StaticActionRuleBaseline(BaseDecisionModel):
    """Baseline 3: Deterministic context-driven heuristic rules."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(model_name="Static Action Rule Baseline", **kwargs)

    def decide(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
        recovery_case_id: str | None = None,
        evaluation_run_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        eligibilities = self._policy_engine.evaluate_all_actions(
            model_input=model_input,
            diagnosis_result=diagnosis_result,
        )
        utilities = self._utility_calculator.compute_all_utilities(
            model_input=model_input,
            predictions=outcome_predictions,
            eligibilities=eligibilities,
            economic_config=self._economic_config,
        )

        feats = model_input.features
        diag_cat = (
            diagnosis_result.predicted_category
            if diagnosis_result
            else DiagnosisCategory.UNKNOWN_FAILURE
        )

        target_action = RecoveryAction.STOP
        if (
            feats.attempt_count <= 1
            and feats.payment_method
            in (SimulatedPaymentMethod.CARD, SimulatedPaymentMethod.UPI)
            and diag_cat
            not in (
                DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
                DiagnosisCategory.AUTHENTICATION_FAILURE,
            )
        ):
            target_action = RecoveryAction.RETRY
        elif diag_cat in (
            DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
            DiagnosisCategory.PAYMENT_METHOD_FAILURE,
            DiagnosisCategory.AUTHENTICATION_FAILURE,
        ):
            target_action = RecoveryAction.PAYMENT_LINK
        elif feats.previous_retry_success > 0:
            target_action = RecoveryAction.RETRY

        # Verify eligibility of target action, otherwise fallback
        if not eligibilities[target_action].is_eligible:
            target_action = (
                RecoveryAction.STOP
                if eligibilities[RecoveryAction.STOP].is_eligible
                else RecoveryAction.ESCALATE
            )

        winner_u = utilities[target_action]
        return RecoveryDecision(
            decision_id=f"dec_rule_{model_input.record_id[:12]}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            recovery_case_id=recovery_case_id,
            selected_action=target_action,
            decision_status=DecisionStatus.ACTION_SELECTED,
            expected_recovery_value=winner_u.expected_recovery_value,
            expected_gross_recovery=winner_u.expected_gross_recovery,
            expected_cost=winner_u.total_cost,
            utility_by_action=utilities,
            eligibility_by_action=eligibilities,
            decision_confidence=0.70,
            rationale=(
                f"Baseline 3: Selected '{target_action.value}' via "
                "deterministic heuristic."
            ),
            decision_latency_ms=0.0,
            diagnosis_model_version=diagnosis_result.model_version
            if diagnosis_result
            else "unknown",
            outcome_model_version=outcome_predictions[
                RecoveryAction.STOP
            ].model_version,
            policy_version=self._policy_engine.config.policy_version,
            economic_config_version=self._economic_config.config_version,
            decision_model_version=self._decision_model_version,
            dataset_version=model_input.dataset_version,
            evaluation_run_id=evaluation_run_id,
            provenance=provenance or {},
        )
