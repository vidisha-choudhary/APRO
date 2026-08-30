"""Dataset generation, snapshotting, and splitting foundation for APRO Phase 6."""

from apro.dataset.enums import DatasetType, SplitStrategy
from apro.dataset.feature_snapshot import create_feature_snapshot
from apro.dataset.generator import (
    DatasetGenerator,
    determine_best_achievable_action_and_value,
)
from apro.dataset.leakage_checks import (
    validate_feature_snapshot,
    validate_model_input_record,
    validate_split_integrity,
)
from apro.dataset.models import (
    DatasetManifest,
    DatasetRecord,
    EvaluationTruthRecord,
    FeatureSnapshot,
    GovernedDataset,
    ModelInputRecord,
)
from apro.dataset.splitter import DatasetSplitter

__all__ = [
    "DatasetGenerator",
    "DatasetManifest",
    "DatasetRecord",
    "DatasetSplitter",
    "DatasetType",
    "EvaluationTruthRecord",
    "FeatureSnapshot",
    "GovernedDataset",
    "ModelInputRecord",
    "SplitStrategy",
    "create_feature_snapshot",
    "determine_best_achievable_action_and_value",
    "validate_feature_snapshot",
    "validate_model_input_record",
    "validate_split_integrity",
]
