"""Unit tests for automated anti-leakage checks (Phase 6)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.feature_snapshot import create_feature_snapshot
from apro.dataset.generator import DatasetGenerator
from apro.dataset.leakage_checks import (
    _check_dict_for_leakage,
    validate_feature_snapshot,
    validate_model_input_record,
    validate_split_integrity,
)
from apro.dataset.models import ModelInputRecord
from apro.simulation.generator import ScenarioGenerator


def test_leakage_checker_detects_forbidden_keys() -> None:
    """AC-05: Test recursive leakage checker flags hidden attributes."""
    clean_dict = {
        "payment_amount": 1000,
        "customer_id": "c1",
        "nested": {"hour": 10},
    }
    _check_dict_for_leakage(clean_dict)  # Should pass

    dirty_dict_1 = {
        "payment_amount": 1000,
        "recoverability": "HIGHLY_RECOVERABLE",
    }
    with pytest.raises(ValueError, match="forbidden key 'recoverability'"):
        _check_dict_for_leakage(dirty_dict_1)

    dirty_dict_2 = {"nested": {"potential_outcomes": {"RETRY": "SUCCESS"}}}
    with pytest.raises(ValueError, match="forbidden key 'potential_outcomes'"):
        _check_dict_for_leakage(dirty_dict_2)


def test_model_input_validation_passes_clean_records() -> None:
    """AC-05: Test standard model input records pass validation."""
    scen = ScenarioGenerator().generate(seed=777)
    snap = create_feature_snapshot(scen.observable_state)
    validate_feature_snapshot(snap)

    record = ModelInputRecord(
        record_id="rec_1",
        dataset_type=DatasetType.TRAINING,
        dataset_version="v1",
        scenario_id="scen_1",
        generation_seed=777,
        scenario_version="scenario-v1",
        configuration_version="config-v1",
        feature_schema_version="feature-schema-v1",
        features=snap,
    )
    validate_model_input_record(record)


def test_split_integrity_detects_scenario_overlap() -> None:
    """AC-05, AC-08: Test split validator detects overlapping scenarios."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "v1", [1], 5)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "v1", [2], 5)
    # Dirty test dataset sharing a seed/scenario from train
    dirty_test_ds = gen.generate_dataset(DatasetType.HELD_OUT_TEST, "v1", [1], 5)

    with pytest.raises(ValueError, match="overlap between TRAIN and TEST"):
        validate_split_integrity(train_ds, val_ds, dirty_test_ds)
