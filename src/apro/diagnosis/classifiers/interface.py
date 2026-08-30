import hashlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset, ModelInputRecord
from apro.diagnosis.calibration import TemperatureCalibrator
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisCategory,
    UncertaintyState,
)
from apro.diagnosis.features import (
    DIAGNOSIS_FEATURE_SCHEMA_VERSION,
    DiagnosisFeatureBuilder,
    DiagnosisFeatureVector,
)
from apro.diagnosis.labels import (
    construct_labels_from_dataset,
)
from apro.diagnosis.models import (
    DiagnosisLabel,
    DiagnosisModelArtifact,
    DiagnosisResult,
)


class BaseDiagnosisModel(ABC):
    """Abstract interface for all Model A failure diagnosis models.

    Governance Boundary:
    - Canonical application training is strictly performed via `fit_on_dataset()`.
    - `fit_on_dataset()` mandates a verified GovernedDataset of type TRAINING.
    - Low-level algorithm fitting logic is protected under `_fit_internal()`.
    """

    def __init__(
        self,
        model_name: str = "",
        model_version: str = "v1.0",
        feature_schema_version: str = DIAGNOSIS_FEATURE_SCHEMA_VERSION,
        taxonomy_version: str = DIAGNOSIS_TAXONOMY_VERSION,
        calibrator: TemperatureCalibrator | None = None,
        feature_builder: DiagnosisFeatureBuilder | None = None,
        high_confidence_threshold: float = 0.70,
        medium_confidence_threshold: float = 0.45,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._feature_schema_version = feature_schema_version
        self._taxonomy_version = taxonomy_version
        self._calibrator = calibrator or TemperatureCalibrator()
        self._feature_builder = feature_builder or DiagnosisFeatureBuilder(
            feature_schema_version
        )
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
    def taxonomy_version(self) -> str:
        return self._taxonomy_version

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def calibrator(self) -> TemperatureCalibrator:
        return self._calibrator

    @calibrator.setter
    def calibrator(self, cal: TemperatureCalibrator) -> None:
        self._calibrator = cal

    @property
    def feature_builder(self) -> DiagnosisFeatureBuilder:
        return self._feature_builder

    @abstractmethod
    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        """Internal algorithm-specific fitting machinery."""

    def fit_on_dataset(
        self,
        training_dataset: GovernedDataset,
        feature_builder: DiagnosisFeatureBuilder | None = None,
    ) -> None:
        """Canonical public entrypoint to fit model on a governed TRAINING dataset."""
        if training_dataset.manifest.dataset_type != DatasetType.TRAINING:
            ds_type = training_dataset.manifest.dataset_type.value
            msg = (
                "Model fitting is strictly permitted on TRAINING datasets; "
                f"received '{ds_type}'."
            )
            raise ValueError(msg)

        fb = feature_builder or self._feature_builder
        if not fb.is_fitted:
            fb.fit(training_dataset)
        self._feature_builder = fb

        features = fb.transform_dataset(training_dataset)
        labels = construct_labels_from_dataset(training_dataset)

        self._fit_internal(features, labels)
        self._is_fitted = True

    @abstractmethod
    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        """Produce raw uncalibrated probability distribution over diagnosis classes."""

    def predict_proba(
        self,
        model_input: ModelInputRecord,
        feature_vector: DiagnosisFeatureVector | None = None,
    ) -> dict[DiagnosisCategory, float]:
        """Predict calibrated probability distribution over all diagnosis classes."""
        if not self._is_fitted:
            msg = (
                f"{self._model_name} is unfitted. "
                "Call fit_on_dataset() before predicting."
            )
            raise ValueError(msg)

        feat = feature_vector or self._feature_builder.transform(model_input)
        raw_probs = self.predict_proba_raw(feat)

        # Apply temperature calibration if calibrated
        calibrated_probs = self._calibrator.calibrate(raw_probs)

        # Enforce all 8 classes are present and sum to 1.0
        complete_probs: dict[DiagnosisCategory, float] = {}
        for c in DIAGNOSIS_TAXONOMY_ORDER:
            complete_probs[c] = max(0.0, min(1.0, calibrated_probs.get(c, 0.0)))

        tot = sum(complete_probs.values())
        if tot > 0:
            for c in DIAGNOSIS_TAXONOMY_ORDER:
                complete_probs[c] = round(complete_probs[c] / tot, 6)
            residual = round(1.0 - sum(complete_probs.values()), 6)
            complete_probs[DIAGNOSIS_TAXONOMY_ORDER[0]] += residual

        return complete_probs

    def determine_uncertainty_state(self, confidence: float) -> UncertaintyState:
        """Map maximum class confidence to structured uncertainty state."""
        if confidence >= self._high_conf_thresh:
            return UncertaintyState.HIGH_CONFIDENCE
        if confidence >= self._med_conf_thresh:
            return UncertaintyState.MEDIUM_CONFIDENCE
        return UncertaintyState.LOW_CONFIDENCE

    def predict(
        self,
        model_input: ModelInputRecord,
        feature_vector: DiagnosisFeatureVector | None = None,
    ) -> DiagnosisResult:
        """Generate structured DiagnosisResult for observable payment failure."""
        probs = self.predict_proba(model_input, feature_vector)

        # Best category has highest probability, tie-breaking by taxonomy order
        best_cat = max(
            DIAGNOSIS_TAXONOMY_ORDER,
            key=lambda c: (
                probs.get(c, 0.0),
                -DIAGNOSIS_TAXONOMY_ORDER.index(c),
            ),
        )
        conf = probs[best_cat]
        unc_state = self.determine_uncertainty_state(conf)

        # Deterministic prediction ID derived from stable identity fields
        identity_str = (
            f"{model_input.record_id}|"
            f"{model_input.dataset_version}|"
            f"{self._model_name}|"
            f"{self._model_version}|"
            f"{self._feature_schema_version}|"
            f"{self._taxonomy_version}"
        )
        pred_hash = hashlib.sha256(identity_str.encode("utf-8")).hexdigest()[:16]
        prediction_id = f"pred_diag_{pred_hash}"

        res = DiagnosisResult(
            prediction_id=prediction_id,
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            model_name=self._model_name,
            model_version=self._model_version,
            dataset_version=model_input.dataset_version,
            feature_schema_version=self._feature_schema_version,
            taxonomy_version=self._taxonomy_version,
            predicted_category=best_cat,
            class_probabilities=probs,
            confidence=round(conf, 4),
            uncertainty_state=unc_state,
            decision_latency_ms=0.0,
        )
        res.validate_probabilities()
        return res

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
    ) -> DiagnosisModelArtifact:
        """Serialize model into a portable DiagnosisModelArtifact."""
        actual_created_at = created_at or datetime.now(UTC).isoformat()
        artifact = DiagnosisModelArtifact(
            model_name=self._model_name,
            model_version=self._model_version,
            algorithm=self.__class__.__name__,
            feature_schema_version=self._feature_schema_version,
            taxonomy_version=self._taxonomy_version,
            training_dataset_version=training_dataset_version,
            training_seed=training_seed,
            created_at=actual_created_at,
            parameters=self.export_parameters(),
            feature_names=self._feature_builder.feature_names,
            calibration_method=(
                self._calibrator.to_dict().get("method")
                if self._calibrator.is_fitted
                else None
            ),
            calibration_parameters=self._calibrator.to_dict(),
            hyperparameters=hyperparameters or {},
            class_order=list(DIAGNOSIS_TAXONOMY_ORDER),
            metadata={"feature_builder": self._feature_builder.to_dict()},
        )
        det_id = artifact.compute_deterministic_identity()
        return artifact.model_copy(update={"deterministic_identity": det_id})
