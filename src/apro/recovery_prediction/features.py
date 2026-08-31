"""Decision-time feature extraction and standardization for APRO Phase 8."""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset, ModelInputRecord
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
    UncertaintyState,
)
from apro.diagnosis.models import DiagnosisResult
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    RecoveryAction,
)
from apro.simulation.enums import SimulatedPaymentMethod

RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION: str = "recovery-outcome-feature-v1"


class RecoveryFeatureVector(BaseModel):
    """Immutable standardized feature vector for a (context, action) pair."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    scenario_id: str
    action: RecoveryAction
    values: list[float]
    feature_names: list[str]
    feature_schema_version: str = Field(default=RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)


class RecoveryFeatureBuilder:
    """Extracts, standardizes, and validates decision-time features for Model B.

    Governance Rules:
    - Feature standardizer MUST be fitted strictly on DatasetType.TRAINING.
    - Only decision-time ModelInputRecord, action, and frozen DiagnosisResult enter.
    - Ground truth EvaluationTruthRecord and potential outcomes are forbidden.
    """

    def __init__(
        self,
        schema_version: str = RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
        action_schema_version: str = RECOVERY_ACTION_SCHEMA_VERSION,
    ) -> None:
        self._schema_version = schema_version
        self._action_schema_version = action_schema_version
        self._is_fitted = False
        self._means: list[float] = []
        self._stds: list[float] = []
        self._feature_names: list[str] = []

    @property
    def schema_version(self) -> str:
        return self._schema_version

    @property
    def action_schema_version(self) -> str:
        return self._action_schema_version

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def feature_names(self) -> list[str]:
        return list(self._feature_names)

    def _extract_raw(
        self,
        record: ModelInputRecord,
        action: RecoveryAction,
        diagnosis_result: DiagnosisResult | None = None,
    ) -> tuple[list[float], list[str]]:
        """Extract raw continuous, discrete, categorical, and interaction features."""
        feats = record.features
        raw_vals: list[float] = []
        names: list[str] = []

        # 1. Payment Context
        raw_vals.append(math.log1p(feats.payment_amount / 100.0))
        names.append("log_payment_amount")

        for meth in (
            SimulatedPaymentMethod.CARD,
            SimulatedPaymentMethod.UPI,
            SimulatedPaymentMethod.NETBANKING,
            SimulatedPaymentMethod.WALLET,
            SimulatedPaymentMethod.OTHER_SUPPORTED_METHOD,
        ):
            raw_vals.append(1.0 if feats.payment_method == meth else 0.0)
            names.append(f"payment_method_{meth.value.lower()}")

        raw_vals.append(float(feats.attempt_count))
        names.append("attempt_count")

        # 2. Failure Keyword Context
        code_text = (feats.failure_code or "").lower()
        reason_text = (feats.failure_reason or "").lower()
        combined_text = f"{code_text} {reason_text}"

        kw_timeout = (
            1.0 if ("timeout" in combined_text or "timed_out" in combined_text) else 0.0
        )
        kw_auth = (
            1.0
            if (
                "auth" in combined_text
                or "otp" in combined_text
                or "3ds" in combined_text
            )
            else 0.0
        )
        kw_bank = (
            1.0
            if (
                "bank" in combined_text
                or "issuer" in combined_text
                or "switch" in combined_text
            )
            else 0.0
        )
        kw_insufficient = (
            1.0
            if (
                "insufficient" in combined_text
                or "limit" in combined_text
                or "funds" in combined_text
            )
            else 0.0
        )
        kw_method = (
            1.0
            if (
                "expired" in combined_text
                or "invalid" in combined_text
                or "card" in combined_text
                or "vpa" in combined_text
            )
            else 0.0
        )
        kw_gateway = (
            1.0
            if (
                "gateway" in combined_text
                or "network" in combined_text
                or "acquirer" in combined_text
            )
            else 0.0
        )
        kw_unknown = (
            1.0 if ("unknown" in combined_text or "error" in combined_text) else 0.0
        )

        raw_vals.extend(
            [
                kw_timeout,
                kw_auth,
                kw_bank,
                kw_insufficient,
                kw_method,
                kw_gateway,
                kw_unknown,
            ]
        )
        names.extend(
            [
                "kw_timeout",
                "kw_auth",
                "kw_bank",
                "kw_insufficient",
                "kw_method_error",
                "kw_gateway",
                "kw_unknown",
            ]
        )

        raw_vals.append(1.0 if feats.decline_code is not None else 0.0)
        names.append("has_decline_code")

        # 3. Pre-decision Historical Statistics
        prev_p = max(0, feats.previous_payment_count)
        prev_f = max(0, feats.previous_failure_count)
        prev_s = max(0, feats.previous_success_count)
        prev_r = max(0, feats.previous_recovery_count)

        raw_vals.extend(
            [
                float(prev_p),
                float(prev_s),
                float(prev_f),
                float(prev_r),
                float(feats.previous_retry_success),
                float(feats.previous_payment_link_success),
                float(prev_f / max(1, prev_p)),
                float(prev_s / max(1, prev_p)),
                float(prev_r / max(1, prev_f)),
            ]
        )
        names.extend(
            [
                "prev_payment_count",
                "prev_success_count",
                "prev_failure_count",
                "prev_recovery_count",
                "prev_retry_success",
                "prev_payment_link_success",
                "hist_failure_rate",
                "hist_success_rate",
                "hist_recovery_rate",
            ]
        )

        # 4. Temporal Context
        hour = feats.hour_of_day
        dow = feats.day_of_week
        raw_vals.extend(
            [
                math.sin(2.0 * math.pi * hour / 24.0),
                math.cos(2.0 * math.pi * hour / 24.0),
                math.sin(2.0 * math.pi * dow / 7.0),
                math.cos(2.0 * math.pi * dow / 7.0),
                1.0 if feats.is_weekend else 0.0,
                math.log1p(feats.time_since_previous_attempt_seconds or 0) / 10.0,
            ]
        )
        names.extend(
            [
                "hour_sin",
                "hour_cos",
                "dow_sin",
                "dow_cos",
                "is_weekend",
                "time_since_prev_attempt_norm",
            ]
        )

        # 5. Optional Model A Diagnosis Features
        diag_probs: dict[DiagnosisCategory, float] = {}
        diag_conf = 0.0
        diag_unc_score = 0.0

        if diagnosis_result is not None:
            diag_probs = diagnosis_result.class_probabilities
            diag_conf = diagnosis_result.confidence
            unc_map = {
                UncertaintyState.HIGH_CONFIDENCE: 3.0,
                UncertaintyState.MEDIUM_CONFIDENCE: 2.0,
                UncertaintyState.LOW_CONFIDENCE: 1.0,
                UncertaintyState.ABSTAIN: 0.0,
            }
            diag_unc_score = unc_map.get(diagnosis_result.uncertainty_state, 0.0)

        for cat in DIAGNOSIS_TAXONOMY_ORDER:
            raw_vals.append(diag_probs.get(cat, 0.0))
            names.append(f"diag_prob_{cat.value.lower()}")

        raw_vals.extend([diag_conf, diag_unc_score])
        names.extend(["diag_confidence", "diag_uncertainty_score"])

        # 6. Action One-Hot Encoding
        is_retry = 1.0 if action == RecoveryAction.RETRY else 0.0
        is_link = 1.0 if action == RecoveryAction.PAYMENT_LINK else 0.0
        is_outreach = 1.0 if action == RecoveryAction.OUTREACH else 0.0
        is_stop = 1.0 if action == RecoveryAction.STOP else 0.0
        is_escalate = 1.0 if action == RecoveryAction.ESCALATE else 0.0

        raw_vals.extend([is_retry, is_link, is_outreach, is_stop, is_escalate])
        names.extend(
            [
                "action_is_retry",
                "action_is_payment_link",
                "action_is_outreach",
                "action_is_stop",
                "action_is_escalate",
            ]
        )

        # 7. Action x Context Synergy / Interaction Features
        p_trans = diag_probs.get(DiagnosisCategory.TRANSIENT_FAILURE, 0.0)
        p_timeout = diag_probs.get(DiagnosisCategory.TIMEOUT, 0.0)
        p_cust = diag_probs.get(DiagnosisCategory.CUSTOMER_SIDE_FAILURE, 0.0)
        p_auth = diag_probs.get(DiagnosisCategory.AUTHENTICATION_FAILURE, 0.0)
        p_method = diag_probs.get(DiagnosisCategory.PAYMENT_METHOD_FAILURE, 0.0)

        raw_vals.extend(
            [
                is_retry * kw_timeout,
                is_retry * kw_gateway,
                is_link * kw_insufficient,
                is_link * kw_auth,
                is_link * kw_method,
                is_outreach * kw_insufficient,
                is_retry * p_trans,
                is_retry * p_timeout,
                is_link * p_cust,
                is_link * p_auth,
                is_link * p_method,
                is_outreach * p_cust,
            ]
        )
        names.extend(
            [
                "act_retry_x_kw_timeout",
                "act_retry_x_kw_gateway",
                "act_link_x_kw_insufficient",
                "act_link_x_kw_auth",
                "act_link_x_kw_method",
                "act_outreach_x_kw_insufficient",
                "act_retry_x_diag_transient",
                "act_retry_x_diag_timeout",
                "act_link_x_diag_cust",
                "act_link_x_diag_auth",
                "act_link_x_diag_method",
                "act_outreach_x_diag_cust",
            ]
        )

        return raw_vals, names

    def fit(
        self,
        training_dataset: GovernedDataset,
        diagnosis_results: dict[str, DiagnosisResult] | None = None,
    ) -> None:
        """Fit normalization parameters exclusively on a TRAINING dataset."""
        if training_dataset.manifest.dataset_type != DatasetType.TRAINING:
            ds_type = training_dataset.manifest.dataset_type.value
            msg = (
                "Feature standardizer fitting strictly requires DatasetType.TRAINING; "
                f"received '{ds_type}'."
            )
            raise ValueError(msg)

        diag_map = diagnosis_results or {}
        raw_matrix: list[list[float]] = []

        for rec in training_dataset.records:
            diag_res = diag_map.get(rec.model_input.record_id)
            for act in RECOVERY_ACTION_ORDER:
                vals, names = self._extract_raw(
                    rec.model_input, act, diagnosis_result=diag_res
                )
                if not self._feature_names:
                    self._feature_names = list(names)
                raw_matrix.append(vals)

        n_samples = len(raw_matrix)
        n_feats = len(self._feature_names)

        self._means = [0.0] * n_feats
        self._stds = [1.0] * n_feats

        for f_idx in range(n_feats):
            col = [raw_matrix[i][f_idx] for i in range(n_samples)]
            m = sum(col) / n_samples
            var = sum((x - m) ** 2 for x in col) / max(1, n_samples - 1)
            s = math.sqrt(var)
            self._means[f_idx] = m
            self._stds[f_idx] = s if s > 1e-4 else 1.0

        self._is_fitted = True

    def transform(
        self,
        record: ModelInputRecord,
        action: RecoveryAction,
        diagnosis_result: DiagnosisResult | None = None,
    ) -> RecoveryFeatureVector:
        """Standardize raw feature vector for a decision-time input and action."""
        if not self._is_fitted:
            msg = (
                "RecoveryFeatureBuilder is unfitted. "
                "Call fit() on TRAINING dataset first."
            )
            raise ValueError(msg)

        raw_vals, names = self._extract_raw(
            record, action, diagnosis_result=diagnosis_result
        )
        standardized_vals = [
            (raw_vals[i] - self._means[i]) / self._stds[i] for i in range(len(raw_vals))
        ]

        return RecoveryFeatureVector(
            record_id=record.record_id,
            scenario_id=record.scenario_id,
            action=action,
            values=standardized_vals,
            feature_names=self._feature_names,
            feature_schema_version=self._schema_version,
            action_schema_version=self._action_schema_version,
        )

    def transform_dataset(
        self,
        dataset: GovernedDataset,
        actions: list[RecoveryAction] | None = None,
        diagnosis_results: dict[str, DiagnosisResult] | None = None,
    ) -> list[RecoveryFeatureVector]:
        """Extract and standardize feature vectors for records and actions."""
        target_actions = actions or list(RECOVERY_ACTION_ORDER)
        diag_map = diagnosis_results or {}
        vectors: list[RecoveryFeatureVector] = []

        for rec in dataset.records:
            diag_res = diag_map.get(rec.model_input.record_id)
            for act in target_actions:
                vectors.append(
                    self.transform(
                        rec.model_input,
                        act,
                        diagnosis_result=diag_res,
                    )
                )
        return vectors

    def to_dict(self) -> dict[str, Any]:
        """Export serializable feature builder metadata."""
        return {
            "schema_version": self._schema_version,
            "action_schema_version": self._action_schema_version,
            "is_fitted": self._is_fitted,
            "feature_names": self._feature_names,
            "means": self._means,
            "stds": self._stds,
        }

    def load_dict(self, data: dict[str, Any]) -> None:
        """Load feature builder from dictionary."""
        self._schema_version = data["schema_version"]
        self._action_schema_version = data["action_schema_version"]
        self._is_fitted = data["is_fitted"]
        self._feature_names = data["feature_names"]
        self._means = data["means"]
        self._stds = data["stds"]
