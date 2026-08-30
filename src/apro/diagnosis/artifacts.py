"""Artifact persistence, serialization, and compatibility loading for Model A."""

import json
from pathlib import Path

from apro.diagnosis.calibration import TemperatureCalibrator
from apro.diagnosis.classifiers import (
    BaseDiagnosisModel,
    DecisionTreeDiagnosisModel,
    MultinomialLogisticRegressionDiagnosisModel,
    RandomForestDiagnosisModel,
)
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_VERSION,
)
from apro.diagnosis.features import (
    DIAGNOSIS_FEATURE_SCHEMA_VERSION,
    DiagnosisFeatureBuilder,
)
from apro.diagnosis.models import DiagnosisModelArtifact

ALGORITHM_REGISTRY: dict[str, type[BaseDiagnosisModel]] = {
    "MultinomialLogisticRegressionDiagnosisModel": (
        MultinomialLogisticRegressionDiagnosisModel
    ),
    "DecisionTreeDiagnosisModel": DecisionTreeDiagnosisModel,
    "RandomForestDiagnosisModel": RandomForestDiagnosisModel,
}


def save_model_artifact(
    model: BaseDiagnosisModel,
    target_path: str | Path,
    training_dataset_version: str = "unknown",
    training_seed: int = 42,
    created_at: str | None = None,
) -> DiagnosisModelArtifact:
    """Serialize model artifact to a JSON file with truthful creation timestamp."""
    artifact = model.to_artifact(
        training_dataset_version=training_dataset_version,
        training_seed=training_seed,
        created_at=created_at,
    )
    p = Path(target_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(artifact.model_dump(), indent=2), encoding="utf-8")
    return artifact


def load_model_artifact(
    artifact_path: str | Path,
    expected_feature_schema_version: str = DIAGNOSIS_FEATURE_SCHEMA_VERSION,
    expected_taxonomy_version: str = DIAGNOSIS_TAXONOMY_VERSION,
) -> BaseDiagnosisModel:
    """Load a model artifact from JSON, enforcing strict schema compatibility."""
    p = Path(artifact_path)
    if not p.exists():
        msg = f"Model artifact not found at '{artifact_path}'."
        raise FileNotFoundError(msg)

    raw_json = json.loads(p.read_text(encoding="utf-8"))
    artifact = DiagnosisModelArtifact(**raw_json)

    # Validate Schema & Taxonomy Compatibility
    if artifact.feature_schema_version != expected_feature_schema_version:
        msg = (
            f"Incompatible feature schema version '{artifact.feature_schema_version}'; "
            f"expected '{expected_feature_schema_version}'."
        )
        raise ValueError(msg)

    if artifact.taxonomy_version != expected_taxonomy_version:
        msg = (
            f"Incompatible taxonomy version '{artifact.taxonomy_version}'; "
            f"expected '{expected_taxonomy_version}'."
        )
        raise ValueError(msg)

    alg = artifact.algorithm
    if alg not in ALGORITHM_REGISTRY:
        msg = f"Unknown model algorithm '{alg}' in artifact."
        raise ValueError(msg)

    model_cls = ALGORITHM_REGISTRY[alg]

    # Reconstruct Feature Builder
    fb_data = artifact.metadata.get("feature_builder")
    feature_builder = (
        DiagnosisFeatureBuilder.from_dict(fb_data)
        if fb_data
        else DiagnosisFeatureBuilder(artifact.feature_schema_version)
    )

    # Reconstruct Calibrator
    cal_data = artifact.calibration_parameters
    calibrator = (
        TemperatureCalibrator.from_dict(cal_data)
        if cal_data
        else TemperatureCalibrator()
    )

    model = model_cls(
        model_name=artifact.model_name,
        model_version=artifact.model_version,
        feature_schema_version=artifact.feature_schema_version,
        taxonomy_version=artifact.taxonomy_version,
        calibrator=calibrator,
        feature_builder=feature_builder,
    )
    model.load_parameters(artifact.parameters)
    return model
