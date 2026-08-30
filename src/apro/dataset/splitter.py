"""Deterministic dataset splitting utilities for APRO Phase 6."""

import math
import random
from collections import defaultdict
from datetime import UTC, datetime

from apro.dataset.enums import DatasetType, SplitStrategy
from apro.dataset.leakage_checks import validate_split_integrity
from apro.dataset.models import (
    DatasetManifest,
    DatasetRecord,
    GovernedDataset,
    ModelInputRecord,
)


def _retype_records(
    records: list[DatasetRecord], target_type: DatasetType
) -> list[DatasetRecord]:
    """Create new DatasetRecord copies with updated dataset_type in model inputs."""
    retyped: list[DatasetRecord] = []
    for r in records:
        new_model_input = ModelInputRecord(
            record_id=r.model_input.record_id,
            dataset_type=target_type,
            dataset_version=r.model_input.dataset_version,
            scenario_id=r.model_input.scenario_id,
            generation_seed=r.model_input.generation_seed,
            scenario_version=r.model_input.scenario_version,
            configuration_version=r.model_input.configuration_version,
            feature_schema_version=r.model_input.feature_schema_version,
            benchmark_version=r.model_input.benchmark_version,
            features=r.model_input.features,
            training_label=r.model_input.training_label,
        )
        retyped.append(
            DatasetRecord(
                model_input=new_model_input,
                evaluation_truth=r.evaluation_truth,
            )
        )
    return retyped


def _create_split_dataset(
    original: GovernedDataset,
    records: list[DatasetRecord],
    split_type: DatasetType,
    split_strategy: SplitStrategy,
    temporal_cutoff: str | None = None,
) -> GovernedDataset:
    """Build a GovernedDataset partition with appropriate manifest."""
    retyped = _retype_records(records, split_type)
    manifest = DatasetManifest(
        dataset_version=(
            f"{original.manifest.dataset_version}-{split_type.value.lower()}"
        ),
        dataset_type=split_type,
        scenario_version=original.manifest.scenario_version,
        configuration_version=original.manifest.configuration_version,
        feature_schema_version=original.manifest.feature_schema_version,
        benchmark_version=original.manifest.benchmark_version,
        seed_list=original.manifest.seed_list,
        record_count=len(retyped),
        split_policy=split_strategy.value,
        temporal_cutoff=temporal_cutoff,
        created_at=datetime.now(UTC).isoformat(),
        metadata={"parent_dataset_version": original.manifest.dataset_version},
    )
    return GovernedDataset(manifest=manifest, records=tuple(retyped))


class DatasetSplitter:
    """Provides deterministic splitting with zero cross-split leakage."""

    @staticmethod
    def _validate_ratios(
        train_ratio: float, val_ratio: float, test_ratio: float
    ) -> None:
        total = train_ratio + val_ratio + test_ratio
        if not math.isclose(total, 1.0, abs_tol=1e-5):
            msg = f"Split ratios must sum to 1.0 (got {total:.5f})."
            raise ValueError(msg)
        if any(r < 0.0 for r in (train_ratio, val_ratio, test_ratio)):
            msg = "Split ratios cannot be negative."
            raise ValueError(msg)

    def split_random(
        self,
        dataset: GovernedDataset,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        split_seed: int = 42,
    ) -> tuple[GovernedDataset, GovernedDataset, GovernedDataset]:
        """Split a dataset randomly and deterministically into train, val, and test."""
        self._validate_ratios(train_ratio, val_ratio, test_ratio)
        n = len(dataset.records)
        if n < 3:
            msg = f"Dataset must contain at least 3 records to split (got {n})."
            raise ValueError(msg)

        indices = list(range(n))
        rng = random.Random(split_seed)
        rng.shuffle(indices)

        n_train = max(1, int(round(n * train_ratio)))
        n_val = max(1, int(round(n * val_ratio)))
        if n_train + n_val >= n:
            n_train = max(1, n - 2)
            n_val = 1

        train_idx = indices[:n_train]
        val_idx = indices[n_train : n_train + n_val]
        test_idx = indices[n_train + n_val :]

        train_records = [dataset.records[i] for i in train_idx]
        val_records = [dataset.records[i] for i in val_idx]
        test_records = [dataset.records[i] for i in test_idx]

        train_ds = _create_split_dataset(
            dataset, train_records, DatasetType.TRAINING, SplitStrategy.RANDOM
        )
        val_ds = _create_split_dataset(
            dataset, val_records, DatasetType.VALIDATION, SplitStrategy.RANDOM
        )
        test_ds = _create_split_dataset(
            dataset, test_records, DatasetType.HELD_OUT_TEST, SplitStrategy.RANDOM
        )

        validate_split_integrity(train_ds, val_ds, test_ds)
        return train_ds, val_ds, test_ds

    def split_temporal(
        self,
        dataset: GovernedDataset,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
    ) -> tuple[GovernedDataset, GovernedDataset, GovernedDataset]:
        """Split a dataset temporally by sorting decision timestamps chronologically."""
        self._validate_ratios(train_ratio, val_ratio, test_ratio)
        n = len(dataset.records)
        if n < 3:
            msg = f"Dataset must contain at least 3 records to split (got {n})."
            raise ValueError(msg)

        # Sort chronologically by decision timestamp
        sorted_records = sorted(
            dataset.records,
            key=lambda r: (
                r.model_input.features.decision_timestamp,
                r.model_input.record_id,
            ),
        )

        n_train = max(1, int(round(n * train_ratio)))
        n_val = max(1, int(round(n * val_ratio)))
        if n_train + n_val >= n:
            n_train = max(1, n - 2)
            n_val = 1

        train_records = sorted_records[:n_train]
        val_records = sorted_records[n_train : n_train + n_val]
        test_records = sorted_records[n_train + n_val :]

        train_cutoff = train_records[-1].model_input.features.decision_timestamp
        val_cutoff = val_records[-1].model_input.features.decision_timestamp

        train_ds = _create_split_dataset(
            dataset,
            train_records,
            DatasetType.TRAINING,
            SplitStrategy.TEMPORAL,
            temporal_cutoff=train_cutoff,
        )
        val_ds = _create_split_dataset(
            dataset,
            val_records,
            DatasetType.VALIDATION,
            SplitStrategy.TEMPORAL,
            temporal_cutoff=val_cutoff,
        )
        test_ds = _create_split_dataset(
            dataset,
            test_records,
            DatasetType.HELD_OUT_TEST,
            SplitStrategy.TEMPORAL,
            temporal_cutoff=None,
        )

        validate_split_integrity(train_ds, val_ds, test_ds)
        return train_ds, val_ds, test_ds

    def split_grouped(
        self,
        dataset: GovernedDataset,
        group_key: str = "customer_id",
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        split_seed: int = 42,
    ) -> tuple[GovernedDataset, GovernedDataset, GovernedDataset]:
        """Split a dataset ensuring group keys stay in same partition."""
        self._validate_ratios(train_ratio, val_ratio, test_ratio)
        n = len(dataset.records)
        if n < 3:
            msg = f"Dataset must contain at least 3 records to split (got {n})."
            raise ValueError(msg)

        groups: dict[str, list[DatasetRecord]] = defaultdict(list)
        for r in dataset.records:
            if group_key == "customer_id":
                k = r.model_input.features.customer_id
            else:
                k = r.model_input.scenario_id
            groups[k].append(r)

        unique_keys = list(groups.keys())
        rng = random.Random(split_seed)
        rng.shuffle(unique_keys)

        num_keys = len(unique_keys)
        n_train_k = max(1, int(round(num_keys * train_ratio)))
        n_val_k = max(1, int(round(num_keys * val_ratio)))
        if n_train_k + n_val_k >= num_keys and num_keys >= 3:
            n_train_k = max(1, num_keys - 2)
            n_val_k = 1

        train_keys = set(unique_keys[:n_train_k])
        val_keys = set(unique_keys[n_train_k : n_train_k + n_val_k])
        test_keys = set(unique_keys[n_train_k + n_val_k :])

        train_records = [r for k in train_keys for r in groups[k]]
        val_records = [r for k in val_keys for r in groups[k]]
        test_records = [r for k in test_keys for r in groups[k]]

        train_ds = _create_split_dataset(
            dataset, train_records, DatasetType.TRAINING, SplitStrategy.GROUPED
        )
        val_ds = _create_split_dataset(
            dataset, val_records, DatasetType.VALIDATION, SplitStrategy.GROUPED
        )
        test_ds = _create_split_dataset(
            dataset, test_records, DatasetType.HELD_OUT_TEST, SplitStrategy.GROUPED
        )

        validate_split_integrity(train_ds, val_ds, test_ds)
        return train_ds, val_ds, test_ds
