"""Unit tests for dataset splitting strategies (Phase 6)."""

import pytest

from apro.dataset.enums import DatasetType, SplitStrategy
from apro.dataset.generator import DatasetGenerator
from apro.dataset.splitter import DatasetSplitter


def test_split_random_deterministic() -> None:
    """AC-06: Test random dataset splitting is deterministic and non-overlapping."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(
        DatasetType.TRAINING, "raw-v1", [10, 20, 30], 20
    )  # 60 records

    splitter = DatasetSplitter()
    train_a, val_a, test_a = splitter.split_random(
        dataset, 0.70, 0.15, 0.15, split_seed=42
    )
    train_b, val_b, test_b = splitter.split_random(
        dataset, 0.70, 0.15, 0.15, split_seed=42
    )

    assert len(train_a) == 42
    assert len(val_a) == 9
    assert len(test_a) == 9
    assert len(train_a) + len(val_a) + len(test_a) == 60

    assert train_a.manifest.dataset_type == DatasetType.TRAINING
    assert val_a.manifest.dataset_type == DatasetType.VALIDATION
    assert test_a.manifest.dataset_type == DatasetType.HELD_OUT_TEST

    # Determinism check
    assert [r.model_input.record_id for r in train_a.records] == [
        r.model_input.record_id for r in train_b.records
    ]


def test_split_temporal_ordering() -> None:
    """AC-07: Test temporal splitting orders records chronologically."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(
        DatasetType.TRAINING, "raw-v1", [100], 30, time_step_seconds=300
    )

    splitter = DatasetSplitter()
    train_ds, val_ds, test_ds = splitter.split_temporal(dataset, 0.60, 0.20, 0.20)

    assert len(train_ds) == 18
    assert len(val_ds) == 6
    assert len(test_ds) == 6

    # Verify chronological bounds
    max_train_ts = max(
        r.model_input.features.decision_timestamp for r in train_ds.records
    )
    min_val_ts = min(r.model_input.features.decision_timestamp for r in val_ds.records)
    max_val_ts = max(r.model_input.features.decision_timestamp for r in val_ds.records)
    min_test_ts = min(
        r.model_input.features.decision_timestamp for r in test_ds.records
    )

    assert max_train_ts <= min_val_ts
    assert max_val_ts <= min_test_ts
    assert train_ds.manifest.split_policy == SplitStrategy.TEMPORAL.value
    assert train_ds.manifest.temporal_cutoff is not None


def test_split_grouped_isolation() -> None:
    """AC-06: Test grouped splitting ensures customers do not cross partitions."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.TRAINING, "raw-v1", [50, 51], 25)

    splitter = DatasetSplitter()
    train_ds, val_ds, test_ds = splitter.split_grouped(
        dataset, group_key="customer_id", split_seed=123
    )

    train_custs = {r.model_input.features.customer_id for r in train_ds.records}
    val_custs = {r.model_input.features.customer_id for r in val_ds.records}
    test_custs = {r.model_input.features.customer_id for r in test_ds.records}

    assert train_custs.isdisjoint(val_custs)
    assert train_custs.isdisjoint(test_custs)
    assert val_custs.isdisjoint(test_custs)


def test_invalid_split_ratios_raise_error() -> None:
    """Test non-summing or negative ratios raise ValueError."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.TRAINING, "raw-v1", [1], 10)
    splitter = DatasetSplitter()

    with pytest.raises(ValueError, match="must sum to 1.0"):
        splitter.split_random(dataset, 0.8, 0.2, 0.2)  # Sum = 1.2

    with pytest.raises(ValueError, match="cannot be negative"):
        splitter.split_random(dataset, 1.1, -0.1, 0.0)
