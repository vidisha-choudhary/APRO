"""Unit and integration tests for dataset generation (Phase 6)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.models import GovernedDataset, TrainingObservation


def test_dataset_generation_all_types() -> None:
    """AC-01, AC-02, AC-03: Test generating all four governed dataset types."""
    generator = DatasetGenerator()
    seeds = [42, 101]

    for dtype in DatasetType:
        dataset = generator.generate_dataset(
            dataset_type=dtype,
            dataset_version=f"{dtype.value.lower()}-v1",
            seeds=seeds,
            cases_per_seed=5,
            benchmark_version=(
                "benchmark-v1" if dtype == DatasetType.BENCHMARK else None
            ),
        )

        assert isinstance(dataset, GovernedDataset)
        assert len(dataset) == 10
        assert dataset.manifest.dataset_type == dtype
        assert dataset.manifest.dataset_version == f"{dtype.value.lower()}-v1"
        assert dataset.manifest.scenario_version == "scenario-v1"
        assert dataset.manifest.configuration_version == "config-v1"
        assert dataset.manifest.feature_schema_version == "feature-schema-v1"
        assert dataset.manifest.seed_list == seeds
        assert dataset.manifest.record_count == 10

        # Check records
        for rec in dataset.records:
            assert rec.model_input.dataset_type == dtype
            assert rec.model_input.dataset_version == f"{dtype.value.lower()}-v1"
            assert rec.model_input.scenario_version == "scenario-v1"
            assert rec.model_input.configuration_version == "config-v1"
            assert rec.model_input.feature_schema_version == "feature-schema-v1"
            assert rec.model_input.features.payment_amount > 0
            assert rec.model_input.features.decision_timestamp is not None
            assert rec.evaluation_truth.best_achievable_value >= 0

            # Training datasets have typed TrainingObservation
            if dtype == DatasetType.TRAINING:
                assert isinstance(rec.model_input.training_label, TrainingObservation)
                assert (
                    rec.model_input.training_label.observed_action
                    in rec.model_input.features.candidate_actions
                )
                assert rec.model_input.training_label.recovered_amount >= 0
            else:
                assert rec.model_input.training_label is None


def test_exact_case_count_three_seeds_1000() -> None:
    """Correction A: Guarantee exact 1,000 cases with 3 seeds."""
    generator = DatasetGenerator()
    seeds = [42, 101, 2026]

    # Remainder allocation: 334, 333, 333
    cases_per_seed = [334, 333, 333]
    dataset = generator.generate_dataset(
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="bench-1000-v1",
        seeds=seeds,
        cases_per_seed=cases_per_seed,
        benchmark_version="benchmark-v1",
    )

    assert len(dataset) == 1000
    assert dataset.manifest.record_count == 1000
    assert dataset.manifest.seed_list == seeds

    # Check distribution of sub-seeds
    s42 = [r for r in dataset.records if r.model_input.generation_seed // 100000 == 42]
    s101 = [
        r for r in dataset.records if r.model_input.generation_seed // 100000 == 101
    ]
    s2026 = [
        r for r in dataset.records if r.model_input.generation_seed // 100000 == 2026
    ]

    assert len(s42) == 334
    assert len(s101) == 333
    assert len(s2026) == 333


def test_deterministic_dataset_reproducibility() -> None:
    """AC-20: Test identical generation inputs produce identical datasets."""
    generator = DatasetGenerator()
    seeds = [2026, 9999]

    ds_1 = generator.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-v1",
        seeds=seeds,
        cases_per_seed=10,
    )
    ds_2 = generator.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-v1",
        seeds=seeds,
        cases_per_seed=10,
    )

    assert len(ds_1) == len(ds_2)
    for r1, r2 in zip(ds_1.records, ds_2.records, strict=True):
        assert r1.model_input.record_id == r2.model_input.record_id
        assert r1.model_input.scenario_id == r2.model_input.scenario_id
        assert (
            r1.model_input.features.payment_amount
            == r2.model_input.features.payment_amount
        )
        assert (
            r1.evaluation_truth.best_achievable_action
            == r2.evaluation_truth.best_achievable_action
        )
        assert (
            r1.evaluation_truth.best_achievable_value
            == r2.evaluation_truth.best_achievable_value
        )


def test_governed_dataset_immutability() -> None:
    """Correction G: Test GovernedDataset and records are immutable."""
    generator = DatasetGenerator()
    dataset = generator.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-v1",
        seeds=[42],
        cases_per_seed=5,
    )

    assert isinstance(dataset.records, tuple)
    with pytest.raises(TypeError):
        dataset.records[0] = dataset.records[1]  # type: ignore[index]


def test_invalid_generation_arguments_raise_error() -> None:
    """Test empty seeds or zero cases per seed raise ValueError."""
    generator = DatasetGenerator()
    with pytest.raises(ValueError, match="At least one seed"):
        generator.generate_dataset(
            dataset_type=DatasetType.TRAINING,
            dataset_version="train-v1",
            seeds=[],
            cases_per_seed=5,
        )

    with pytest.raises(ValueError, match="cases_per_seed must be positive"):
        generator.generate_dataset(
            dataset_type=DatasetType.TRAINING,
            dataset_version="train-v1",
            seeds=[42],
            cases_per_seed=0,
        )
