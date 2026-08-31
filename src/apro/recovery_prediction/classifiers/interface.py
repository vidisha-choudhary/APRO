"""Abstract base class and interface for Model B recovery outcome prediction models."""

import hashlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset, ModelInputRecord
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.diagnosis.models import DiagnosisResult
from apro.recovery_prediction.enums import (
    OUTCOME_TAXONOMY_VERSION,
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    PredictedOutcomeState,
    PredictionUncertaintyState,
    RecoveryAction,
)
from apro.recovery_prediction.features import (
    RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
    RecoveryFeatureBuilder,
    RecoveryFeatureVector,
)
from apro.recovery_prediction.labels import (
    construct_outcome_labels_from_dataset,
)
from apro.recovery_prediction.models import (
    MultiActionOutcomePrediction,
    OutcomePrediction,
    RecoveryOutcomeLabel,
    RecoveryOutcomeModelArtifact,
)


class BaseRecoveryOutcomeModel(ABC):
    """Abstract interface for all Model B recovery outcome prediction models.

    Governance Boundary:
    - Canonical application training is strictly performed via `fit_on_dataset()`.
    - `fit_on_dataset()` mandates a verified GovernedDataset of type TRAINING.
    - Low-level algorithm fitting logic is protected under `_fit_internal()`.
    """

    def __init__(
        self,
        model_name: str = "",
        model_version: str = "v1.0",
        feature_schema_version: str = RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
        action_schema_version: str = RECOVERY_ACTION_SCHEMA_VERSION,
        outcome_schema_version: str = OUTCOME_TAXONOMY_VERSION,
        feature_builder: RecoveryFeatureBuilder | None = None,
        high_confidence_threshold: float = 0.75,
        medium_confidence_threshold: float = 0.55,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._feature_schema_version = feature_schema_version
        self._action_schema_version = action_schema_version
        self._outcome_schema_version = outcome_schema_version
        self._feature_builder = feature_builder or RecoveryFeatureBuilder(
            feature_schema_version, action_schema_version
        )
        self._diagnosis_model_version: str | None = None
        self._calibrator: Any = None
        self._high_conf_thresh = high_confidence_threshold
        self._med_conf_thresh = medium_confidence_threshold
        self._is_fitted = False

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def feature_schema_version(self) -> str:
        return self._feature_schema_version

    @property
    def action_schema_version(self) -> str:
        return self._action_schema_version

    @property
    def outcome_schema_version(self) -> str:
        return self._outcome_schema_version

    @property
    def diagnosis_model_version(self) -> str | None:
        return self._diagnosis_model_version

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def feature_builder(self) -> RecoveryFeatureBuilder:
        return self._feature_builder

    @property
    def calibrator(self) -> Any:
        return self._calibrator

    @calibrator.setter
    def calibrator(self, cal: Any) -> None:
        self._calibrator = cal

    @abstractmethod
    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        """Internal algorithm-specific fitting machinery."""

    def fit_on_dataset(
        self,
        training_dataset: GovernedDataset,
        diagnosis_model: BaseDiagnosisModel | None = None,
        feature_builder: RecoveryFeatureBuilder | None = None,
    ) -> None:
        """Canonical public entrypoint to fit Model B on a TRAINING dataset."""
        if training_dataset.manifest.dataset_type != DatasetType.TRAINING:
            ds_type = training_dataset.manifest.dataset_type.value
            msg = (
                "Model fitting is strictly permitted on TRAINING datasets; "
                f"received '{ds_type}'."
            )
            raise ValueError(msg)

        diag_map: dict[str, DiagnosisResult] = {}
        if diagnosis_model is not None:
            self._diagnosis_model_version = diagnosis_model.model_version
            for rec in training_dataset.records:
                diag_map[rec.model_input.record_id] = diagnosis_model.predict(
                    rec.model_input
                )

        fb = feature_builder or self._feature_builder
        if not fb.is_fitted:
            fb.fit(training_dataset, diagnosis_results=diag_map)
        self._feature_builder = fb

        features = fb.transform_dataset(
            training_dataset,
            diagnosis_results=diag_map,
        )
        labels = construct_outcome_labels_from_dataset(training_dataset)

        self._fit_internal(features, labels)
        self._is_fitted = True

    @abstractmethod
    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        """Produce raw uncalibrated probability P(success | context, action)."""

    def predict_proba(
        self,
        model_input: ModelInputRecord,
        action: RecoveryAction,
        diagnosis_result: DiagnosisResult | None = None,
        feature_vector: RecoveryFeatureVector | None = None,
    ) -> float:
        """Predict calibrated success probability for a context and action."""
        if not self._is_fitted:
            msg = (
                f"{self._model_name} is unfitted. "
                "Call fit_on_dataset() before predicting."
            )
            raise ValueError(msg)

        feat = feature_vector or self._feature_builder.transform(
            model_input, action, diagnosis_result=diagnosis_result
        )
        raw_p = self.predict_proba_raw(feat)

        if self._calibrator is not None and hasattr(
            self._calibrator, "calibrate_probability"
        ):
            cal_p = float(self._calibrator.calibrate_probability(raw_p, action))
        else:
            cal_p = raw_p

        return float(max(0.0, min(1.0, cal_p)))

    def predict_recovered_amount(
        self,
        model_input: ModelInputRecord,
        action: RecoveryAction,
        diagnosis_result: DiagnosisResult | None = None,
        feature_vector: RecoveryFeatureVector | None = None,
    ) -> int:
        """Predict expected recovery amount in minor units (e.g. paise)."""
        p = self.predict_proba(
            model_input,
            action,
            diagnosis_result=diagnosis_result,
            feature_vector=feature_vector,
        )
        tot_amount = model_input.features.payment_amount
        exp_amount = int(round(p * tot_amount))
        return max(0, min(tot_amount, exp_amount))

    def determine_uncertainty_state(
        self, confidence: float
    ) -> PredictionUncertaintyState:
        """Map confidence score to structured uncertainty state."""
        if confidence >= self._high_conf_thresh:
            return PredictionUncertaintyState.HIGH_CONFIDENCE
        if confidence >= self._med_conf_thresh:
            return PredictionUncertaintyState.MEDIUM_CONFIDENCE
        return PredictionUncertaintyState.LOW_CONFIDENCE

    def predict(
        self,
        model_input: ModelInputRecord,
        action: RecoveryAction,
        diagnosis_result: DiagnosisResult | None = None,
        feature_vector: RecoveryFeatureVector | None = None,
    ) -> OutcomePrediction:
        """Generate structured OutcomePrediction for an action."""
        p_success = self.predict_proba(
            model_input,
            action,
            diagnosis_result=diagnosis_result,
            feature_vector=feature_vector,
        )
        exp_amount = self.predict_recovered_amount(
            model_input,
            action,
            diagnosis_result=diagnosis_result,
            feature_vector=feature_vector,
        )

        outcome_state = (
            PredictedOutcomeState.SUCCESS
            if p_success >= 0.50
            else PredictedOutcomeState.FAILURE
        )
        confidence = max(p_success, 1.0 - p_success)
        unc_state = self.determine_uncertainty_state(confidence)

        identity_str = (
            f"{model_input.record_id}|"
            f"{model_input.dataset_version}|"
            f"{self._model_name}|"
            f"{self._model_version}|"
            f"{action.value}|"
            f"{self._feature_schema_version}|"
            f"{self._action_schema_version}"
        )
        pred_hash = hashlib.sha256(identity_str.encode("utf-8")).hexdigest()[:16]
        prediction_id = f"pred_rec_{pred_hash}"

        return OutcomePrediction(
            prediction_id=prediction_id,
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            action=action,
            model_name=self._model_name,
            model_version=self._model_version,
            dataset_version=model_input.dataset_version,
            feature_schema_version=self._feature_schema_version,
            action_schema_version=self._action_schema_version,
            diagnosis_model_version=self._diagnosis_model_version,
            predicted_success_probability=round(p_success, 4),
            predicted_outcome_state=outcome_state,
            predicted_recovered_amount=exp_amount,
            confidence=round(confidence, 4),
            uncertainty_state=unc_state,
            decision_latency_ms=0.0,
        )

    def predict_all_actions(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None = None,
    ) -> MultiActionOutcomePrediction:
        """Generate outcome predictions for all candidate actions."""
        preds: dict[RecoveryAction, OutcomePrediction] = {}
        for act in RECOVERY_ACTION_ORDER:
            preds[act] = self.predict(
                model_input, act, diagnosis_result=diagnosis_result
            )
        return MultiActionOutcomePrediction(
            scenario_id=model_input.scenario_id,
            record_id=model_input.record_id,
            predictions=preds,
        )

    @abstractmethod
    def export_parameters(self) -> dict[str, Any]:
        """Export trained model parameters for serialization."""

    @abstractmethod
    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load trained model parameters from artifact."""

    def to_artifact(
        self,
        training_dataset_version: str = "unknown",
        training_seed: int = 42,
        created_at: str | None = None,
        hyperparameters: dict[str, Any] | None = None,
    ) -> RecoveryOutcomeModelArtifact:
        """Serialize model into a portable RecoveryOutcomeModelArtifact."""
        actual_created_at = created_at or datetime.now(UTC).isoformat()
        cal_dict = self._calibrator.to_dict() if self._calibrator is not None else {}

        artifact = RecoveryOutcomeModelArtifact(
            model_name=self._model_name,
            model_version=self._model_version,
            algorithm=self.__class__.__name__,
            feature_schema_version=self._feature_schema_version,
            action_schema_version=self._action_schema_version,
            outcome_schema_version=self._outcome_schema_version,
            training_dataset_version=training_dataset_version,
            training_seed=training_seed,
            created_at=actual_created_at,
            parameters=self.export_parameters(),
            feature_names=self._feature_builder.feature_names,
            diagnosis_model_version=self._diagnosis_model_version,
            calibration_method=cal_dict.get("method"),
            calibration_parameters=cal_dict,
            hyperparameters=hyperparameters or {},
            action_order=list(RECOVERY_ACTION_ORDER),
            metadata={"feature_builder": self._feature_builder.to_dict()},
        )
        det_id = artifact.compute_deterministic_identity()
        return artifact.model_copy(update={"deterministic_identity": det_id})
