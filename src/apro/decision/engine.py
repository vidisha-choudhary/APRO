"""Core Economic Decision Engine implementing action selection for Phase 9."""

import hashlib
import time
from typing import Any

from apro.dataset.models import ModelInputRecord
from apro.decision.economics import EconomicConfiguration
from apro.decision.eligibility import (
    PolicyConfiguration,
    PolicyEligibilityEngine,
)
from apro.decision.enums import (
    DECISION_MODEL_SCHEMA_VERSION,
    ECONOMIC_CONFIG_SCHEMA_VERSION,
    POLICY_CONFIG_SCHEMA_VERSION,
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    UTILITY_FORMULA_VERSION,
    DecisionStatus,
    RecoveryAction,
)
from apro.decision.models import (
    ActionEligibility,
    ActionUtility,
    RecoveryDecision,
)
from apro.decision.utility import UtilityCalculator
from apro.diagnosis.enums import DIAGNOSIS_TAXONOMY_VERSION
from apro.diagnosis.features import DIAGNOSIS_FEATURE_SCHEMA_VERSION
from apro.diagnosis.models import DiagnosisResult
from apro.recovery_prediction.features import (
    RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
)
from apro.recovery_prediction.models import OutcomePrediction


class EconomicDecisionEngine:
    """Decision engine selecting bounded recovery actions based on economics."""

    def __init__(
        self,
        decision_model_version: str = DECISION_MODEL_SCHEMA_VERSION,
        economic_config: EconomicConfiguration | None = None,
        policy_config: PolicyConfiguration | None = None,
        utility_version: str = UTILITY_FORMULA_VERSION,
        action_schema_version: str = RECOVERY_ACTION_SCHEMA_VERSION,
        feature_schema_version: str = "feature-schema-v1",
        prediction_feature_schema_version: str = (
            RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION
        ),
        audit_service: Any | None = None,
    ) -> None:
        self._decision_model_version = decision_model_version
        self._economic_config = economic_config or EconomicConfiguration()
        self._policy_engine = PolicyEligibilityEngine(policy_config)
        self._utility_calculator = UtilityCalculator(utility_version)
        self._action_schema_version = action_schema_version
        self._feature_schema_version = feature_schema_version
        self._prediction_feature_schema_version = prediction_feature_schema_version
        self.audit_service = audit_service

        # Validate engine configuration versions on initialization
        if self._policy_engine.config.policy_version != POLICY_CONFIG_SCHEMA_VERSION:
            msg = (
                f"Incompatible policy config version "
                f"'{self._policy_engine.config.policy_version}'; "
                f"expected '{POLICY_CONFIG_SCHEMA_VERSION}'."
            )
            raise ValueError(msg)

        if self._economic_config.config_version != ECONOMIC_CONFIG_SCHEMA_VERSION:
            msg = (
                f"Incompatible economic config version "
                f"'{self._economic_config.config_version}'; "
                f"expected '{ECONOMIC_CONFIG_SCHEMA_VERSION}'."
            )
            raise ValueError(msg)

    @property
    def decision_model_version(self) -> str:
        return self._decision_model_version

    @property
    def economic_config(self) -> EconomicConfiguration:
        return self._economic_config

    @property
    def policy_engine(self) -> PolicyEligibilityEngine:
        return self._policy_engine

    @property
    def utility_calculator(self) -> UtilityCalculator:
        return self._utility_calculator

    def compute_decision_confidence(
        self,
        winning_action: RecoveryAction,
        utilities: dict[RecoveryAction, ActionUtility],
        eligible_actions: list[RecoveryAction],
        diagnosis_result: DiagnosisResult | None,
        payment_amount: int,
    ) -> float:
        """Compute holistic decision confidence score (0.0 to 1.0)."""
        winner_u = utilities[winning_action]
        p_conf = max(
            winner_u.predicted_success_probability,
            1.0 - winner_u.predicted_success_probability,
        )

        d_conf = diagnosis_result.confidence if diagnosis_result is not None else 0.50

        # Margin over second-best eligible action
        other_ervs = [
            utilities[a].expected_recovery_value
            for a in eligible_actions
            if a != winning_action
        ]
        if other_ervs:
            runner_up_erv = max(other_ervs)
            erv_margin = max(0, winner_u.expected_recovery_value - runner_up_erv)
            norm_margin = min(1.0, erv_margin / max(100, payment_amount))
        else:
            norm_margin = 1.0

        raw_conf = 0.50 * p_conf + 0.30 * norm_margin + 0.20 * d_conf
        return round(max(0.0, min(1.0, raw_conf)), 4)

    def decide(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[RecoveryAction, OutcomePrediction],
        recovery_case_id: str | None = None,
        evaluation_run_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        """Generate an immutable, auditable RecoveryDecision for context."""
        t0 = time.perf_counter()

        # Step 1: Strict Version & Schema Verification
        if model_input.feature_schema_version != self._feature_schema_version:
            msg = (
                f"Incompatible model_input feature_schema_version "
                f"'{model_input.feature_schema_version}'; "
                f"expected '{self._feature_schema_version}'."
            )
            raise ValueError(msg)

        first_model_ver: str | None = None
        for act in RECOVERY_ACTION_ORDER:
            if act not in outcome_predictions:
                msg = f"Missing Model B outcome prediction for action '{act.value}'."
                raise ValueError(msg)

            pred = outcome_predictions[act]
            if pred.action_schema_version != self._action_schema_version:
                msg = (
                    f"Incompatible action schema version "
                    f"'{pred.action_schema_version}'; "
                    f"expected '{self._action_schema_version}'."
                )
                raise ValueError(msg)

            valid_pred_schemas = {
                self._prediction_feature_schema_version,
                self._feature_schema_version,
                "recovery-outcome-feature-v1",
            }
            if pred.feature_schema_version not in valid_pred_schemas:
                msg = (
                    f"Incompatible outcome prediction feature schema version "
                    f"'{pred.feature_schema_version}'; "
                    f"expected one of {sorted(valid_pred_schemas)}."
                )
                raise ValueError(msg)

            if pred.dataset_version != model_input.dataset_version:
                msg = (
                    f"Dataset version mismatch between prediction "
                    f"('{pred.dataset_version}') and model_input "
                    f"('{model_input.dataset_version}')."
                )
                raise ValueError(msg)

            if pred.record_id != model_input.record_id:
                msg = (
                    f"Record ID mismatch between prediction "
                    f"('{pred.record_id}') and model_input "
                    f"('{model_input.record_id}')."
                )
                raise ValueError(msg)

            if pred.scenario_id != model_input.scenario_id:
                msg = (
                    f"Scenario ID mismatch between prediction "
                    f"('{pred.scenario_id}') and model_input "
                    f"('{model_input.scenario_id}')."
                )
                raise ValueError(msg)

            if first_model_ver is None:
                first_model_ver = pred.model_version
            elif pred.model_version != first_model_ver:
                msg = (
                    f"Inconsistent Model B version across actions: "
                    f"'{pred.model_version}' vs '{first_model_ver}'."
                )
                raise ValueError(msg)

        if diagnosis_result is not None:
            if diagnosis_result.record_id != model_input.record_id:
                msg = (
                    f"Record ID mismatch between diagnosis "
                    f"('{diagnosis_result.record_id}') and model_input "
                    f"('{model_input.record_id}')."
                )
                raise ValueError(msg)

            if diagnosis_result.scenario_id != model_input.scenario_id:
                msg = (
                    f"Scenario ID mismatch between diagnosis "
                    f"('{diagnosis_result.scenario_id}') and model_input "
                    f"('{model_input.scenario_id}')."
                )
                raise ValueError(msg)

            valid_diag_schemas = {
                DIAGNOSIS_FEATURE_SCHEMA_VERSION,
                self._feature_schema_version,
                "diagnosis-feature-v1",
            }
            if diagnosis_result.feature_schema_version not in valid_diag_schemas:
                msg = (
                    f"Incompatible diagnosis feature schema version "
                    f"'{diagnosis_result.feature_schema_version}'; "
                    f"expected one of {sorted(valid_diag_schemas)}."
                )
                raise ValueError(msg)

            if diagnosis_result.dataset_version != model_input.dataset_version:
                msg = (
                    f"Dataset version mismatch between diagnosis "
                    f"('{diagnosis_result.dataset_version}') and model_input "
                    f"('{model_input.dataset_version}')."
                )
                raise ValueError(msg)

            if diagnosis_result.taxonomy_version != DIAGNOSIS_TAXONOMY_VERSION:
                msg = (
                    f"Incompatible diagnosis taxonomy version "
                    f"'{diagnosis_result.taxonomy_version}'; "
                    f"expected '{DIAGNOSIS_TAXONOMY_VERSION}'."
                )
                raise ValueError(msg)

        # Step 2: Policy Eligibility Evaluation
        eligibilities: dict[RecoveryAction, ActionEligibility] = (
            self._policy_engine.evaluate_all_actions(
                model_input=model_input,
                diagnosis_result=diagnosis_result,
            )
        )

        # Step 3: Granular Economic Utility Calculation across All Actions
        utilities: dict[RecoveryAction, ActionUtility] = (
            self._utility_calculator.compute_all_utilities(
                model_input=model_input,
                predictions=outcome_predictions,
                eligibilities=eligibilities,
                economic_config=self._economic_config,
            )
        )

        # Step 4: Candidate Filtering (Eligible Actions Only)
        eligible_actions = [
            act for act in RECOVERY_ACTION_ORDER if eligibilities[act].is_eligible
        ]

        payment_amount = model_input.features.payment_amount
        min_threshold = self._economic_config.minimum_expected_recovery_value
        diag_ver = (
            diagnosis_result.model_version
            if diagnosis_result is not None
            else "unknown"
        )
        out_ver = outcome_predictions[RecoveryAction.STOP].model_version

        # Case A: No eligible actions under policy
        if not eligible_actions:
            t_latency = (time.perf_counter() - t0) * 1000.0
            rationale = (
                "All recovery actions are ineligible under active safety policy."
            )
            decision_id_str = (
                f"{model_input.record_id}|NONE|"
                f"{DecisionStatus.NO_ELIGIBLE_ACTION.value}|"
                f"{self._decision_model_version}"
            )
            h_str = hashlib.sha256(decision_id_str.encode("utf-8")).hexdigest()
            dec_id = f"dec_{h_str[:16]}"

            decision = RecoveryDecision(
                decision_id=dec_id,
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
                rationale=rationale,
                decision_latency_ms=round(t_latency, 4),
                diagnosis_model_version=diag_ver,
                outcome_model_version=out_ver,
                policy_version=self._policy_engine.config.policy_version,
                economic_config_version=self._economic_config.config_version,
                decision_model_version=self._decision_model_version,
                action_schema_version=self._action_schema_version,
                feature_schema_version=self._feature_schema_version,
                dataset_version=model_input.dataset_version,
                evaluation_run_id=evaluation_run_id,
                provenance=provenance or {},
            )
            if self.audit_service is not None and hasattr(
                self.audit_service, "record_decision_sync"
            ):
                candidates_summary = [
                    {"action": k.value, "erv": v.expected_recovery_value}
                    for k, v in decision.utility_by_action.items()
                ]
                self.audit_service.record_decision_sync(
                    decision=decision,
                    candidate_actions=candidates_summary,
                )
            return decision

        # Step 5: Economic Optimization & Ranking
        eligible_ervs = {
            act: utilities[act].expected_recovery_value for act in eligible_actions
        }
        max_erv = max(eligible_ervs.values())

        # Case B: Threshold Check (No action clears minimum ERV threshold)
        if max_erv < min_threshold:
            t_latency = (time.perf_counter() - t0) * 1000.0
            th_rs = min_threshold / 100
            m_rs = max_erv / 100
            rationale = (
                f"No eligible action met minimum ERV threshold (Rs {th_rs:.2f}). "
                f"Highest ERV was Rs {m_rs:.2f}."
            )
            decision_id_str = (
                f"{model_input.record_id}|NONE|"
                f"{DecisionStatus.NO_POSITIVE_UTILITY.value}|{max_erv}|"
                f"{self._decision_model_version}"
            )
            h_str = hashlib.sha256(decision_id_str.encode("utf-8")).hexdigest()
            dec_id = f"dec_{h_str[:16]}"

            decision = RecoveryDecision(
                decision_id=dec_id,
                record_id=model_input.record_id,
                scenario_id=model_input.scenario_id,
                recovery_case_id=recovery_case_id,
                selected_action=None,
                decision_status=DecisionStatus.NO_POSITIVE_UTILITY,
                expected_recovery_value=max_erv,
                expected_gross_recovery=None,
                expected_cost=None,
                utility_by_action=utilities,
                eligibility_by_action=eligibilities,
                decision_confidence=0.50,
                rationale=rationale,
                decision_latency_ms=round(t_latency, 4),
                diagnosis_model_version=diag_ver,
                outcome_model_version=out_ver,
                policy_version=self._policy_engine.config.policy_version,
                economic_config_version=self._economic_config.config_version,
                decision_model_version=self._decision_model_version,
                action_schema_version=self._action_schema_version,
                feature_schema_version=self._feature_schema_version,
                dataset_version=model_input.dataset_version,
                evaluation_run_id=evaluation_run_id,
                provenance=provenance or {},
            )
            if self.audit_service is not None and hasattr(
                self.audit_service, "record_decision_sync"
            ):
                candidates_summary = [
                    {"action": k.value, "erv": v.expected_recovery_value}
                    for k, v in decision.utility_by_action.items()
                ]
                self.audit_service.record_decision_sync(
                    decision=decision,
                    candidate_actions=candidates_summary,
                )
            return decision

        # Step 6: Candidate Set within Tolerance & Deterministic Tie-Breaking
        tolerance = self._economic_config.utility_tolerance
        tied_candidates = [
            act
            for act in eligible_actions
            if (max_erv - eligible_ervs[act]) <= tolerance
        ]

        winning_action = None
        for act in self._economic_config.tie_break_order:
            if act in tied_candidates:
                winning_action = act
                break

        if winning_action is None:
            winning_action = tied_candidates[0]

        winner_utility = utilities[winning_action]
        conf = self.compute_decision_confidence(
            winning_action=winning_action,
            utilities=utilities,
            eligible_actions=eligible_actions,
            diagnosis_result=diagnosis_result,
            payment_amount=payment_amount,
        )

        tol_rs = tolerance / 100
        tie_note = (
            f" (Resolved tie among {len(tied_candidates)} actions within "
            f"Rs {tol_rs:.2f} tolerance via tie-break policy)."
            if len(tied_candidates) > 1
            else ""
        )
        erv_rs = winner_utility.expected_recovery_value / 100
        gross_rs = winner_utility.expected_gross_recovery / 100
        cost_rs = winner_utility.total_cost / 100
        p_str = f"{winner_utility.predicted_success_probability:.2%}"

        rationale = (
            f"Selected action '{winning_action.value}' with ERV Rs {erv_rs:.2f} "
            f"(Gross: Rs {gross_rs:.2f}, Cost: Rs {cost_rs:.2f}, "
            f"P(Success): {p_str}){tie_note}."
        )

        t_latency = (time.perf_counter() - t0) * 1000.0
        decision_id_str = (
            f"{model_input.record_id}|{winning_action.value}|"
            f"{DecisionStatus.ACTION_SELECTED.value}|"
            f"{winner_utility.expected_recovery_value}|"
            f"{self._decision_model_version}"
        )
        dec_id = (
            f"dec_{hashlib.sha256(decision_id_str.encode('utf-8')).hexdigest()[:16]}"
        )

        decision = RecoveryDecision(
            decision_id=dec_id,
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            recovery_case_id=recovery_case_id,
            selected_action=winning_action,
            decision_status=DecisionStatus.ACTION_SELECTED,
            expected_recovery_value=winner_utility.expected_recovery_value,
            expected_gross_recovery=winner_utility.expected_gross_recovery,
            expected_cost=winner_utility.total_cost,
            utility_by_action=utilities,
            eligibility_by_action=eligibilities,
            decision_confidence=conf,
            rationale=rationale,
            decision_latency_ms=round(t_latency, 4),
            diagnosis_model_version=diag_ver,
            outcome_model_version=out_ver,
            policy_version=self._policy_engine.config.policy_version,
            economic_config_version=self._economic_config.config_version,
            decision_model_version=self._decision_model_version,
            action_schema_version=self._action_schema_version,
            feature_schema_version=self._feature_schema_version,
            dataset_version=model_input.dataset_version,
            evaluation_run_id=evaluation_run_id,
            provenance=provenance or {},
        )
        if self.audit_service is not None and hasattr(
            self.audit_service, "record_decision_sync"
        ):
            candidates_summary = [
                {"action": k.value, "erv": v.expected_recovery_value}
                for k, v in decision.utility_by_action.items()
            ]
            self.audit_service.record_decision_sync(
                decision=decision,
                candidate_actions=candidates_summary,
            )
        return decision

    async def record_audit(
        self,
        decision: RecoveryDecision,
        cycle_number: int = 1,
        uow: Any | None = None,
    ) -> Any | None:
        """Record decision audit event via configured AuditService."""
        if self.audit_service is None:
            return None
        candidates_summary = [
            {"action": k.value, "erv": v.expected_recovery_value}
            for k, v in decision.utility_by_action.items()
        ]
        return await self.audit_service.record_decision(
            decision=decision,
            candidate_actions=candidates_summary,
            cycle_number=cycle_number,
            uow=uow,
        )
