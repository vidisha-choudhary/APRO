"""APRO Phase 7: Failure Diagnosis Intelligence (Model A) Package."""

from apro.diagnosis.artifacts import (
    load_model_artifact,
    save_model_artifact,
)
from apro.diagnosis.baselines import (
    HistoricalConditionalBaseline,
    MajorityClassBaseline,
    NaiveBayesDiagnosisModel,
    ProviderRuleBaseline,
)
from apro.diagnosis.calibration import (
    TemperatureCalibrator,
)
from apro.diagnosis.classifiers import (
    BaseDiagnosisModel,
    DecisionTreeDiagnosisModel,
    MultinomialLogisticRegressionDiagnosisModel,
    RandomForestDiagnosisModel,
)
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisAlgorithmType,
    DiagnosisCategory,
    UncertaintyState,
)
from apro.diagnosis.evaluation import (
    DiagnosisEvaluator,
)
from apro.diagnosis.features import (
    DIAGNOSIS_FEATURE_SCHEMA_VERSION,
    DiagnosisFeatureBuilder,
    DiagnosisFeatureDescriptor,
    DiagnosisFeatureSchema,
    DiagnosisFeatureVector,
)
from apro.diagnosis.labels import (
    construct_diagnosis_label,
    construct_labels_from_dataset,
)
from apro.diagnosis.metrics import (
    DiagnosisMetrics,
    PerClassMetric,
    calculate_diagnosis_metrics,
)
from apro.diagnosis.models import (
    DiagnosisExperimentConfig,
    DiagnosisLabel,
    DiagnosisModelArtifact,
    DiagnosisResult,
)
from apro.diagnosis.reports import (
    generate_confusion_matrix_json,
    generate_diagnosis_evaluation_json,
    generate_diagnosis_evaluation_markdown,
    generate_model_manifest_json,
    generate_prediction_traces_jsonl,
)
from apro.diagnosis.traces import (
    DiagnosisPredictionTrace,
)

__all__ = [
    # Enums
    "DiagnosisCategory",
    "DIAGNOSIS_TAXONOMY_ORDER",
    "DIAGNOSIS_TAXONOMY_VERSION",
    "UncertaintyState",
    "DiagnosisAlgorithmType",
    # Models & Artifacts
    "DiagnosisLabel",
    "DiagnosisResult",
    "DiagnosisModelArtifact",
    "DiagnosisExperimentConfig",
    "DiagnosisPredictionTrace",
    # Labels & Features
    "construct_diagnosis_label",
    "construct_labels_from_dataset",
    "DIAGNOSIS_FEATURE_SCHEMA_VERSION",
    "DiagnosisFeatureDescriptor",
    "DiagnosisFeatureSchema",
    "DiagnosisFeatureVector",
    "DiagnosisFeatureBuilder",
    # Classifiers & Baselines
    "BaseDiagnosisModel",
    "MultinomialLogisticRegressionDiagnosisModel",
    "DecisionTreeDiagnosisModel",
    "RandomForestDiagnosisModel",
    "MajorityClassBaseline",
    "ProviderRuleBaseline",
    "HistoricalConditionalBaseline",
    "NaiveBayesDiagnosisModel",
    # Calibration & Metrics
    "TemperatureCalibrator",
    "PerClassMetric",
    "DiagnosisMetrics",
    "calculate_diagnosis_metrics",
    # Evaluation & Artifacts
    "DiagnosisEvaluator",
    "save_model_artifact",
    "load_model_artifact",
    # Reports
    "generate_diagnosis_evaluation_json",
    "generate_diagnosis_evaluation_markdown",
    "generate_confusion_matrix_json",
    "generate_prediction_traces_jsonl",
    "generate_model_manifest_json",
]
