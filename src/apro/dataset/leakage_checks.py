"""Automated anti-leakage validators and split integrity checks for APRO Phase 6."""

from typing import Any

from apro.dataset.models import FeatureSnapshot, GovernedDataset, ModelInputRecord

FORBIDDEN_HIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "recoverability",
        "customer_behavior",
        "true_failure_mechanism",
        "latent_customer_intent",
        "latent_bank_condition",
        "true_action_probabilities",
        "potential_outcomes",
        "best_achievable_action",
        "best_achievable_value",
        "true_prob",
        "hidden_state",
    }
)

FORBIDDEN_FEATURE_KEYS: frozenset[str] = FORBIDDEN_HIDDEN_KEYS | frozenset(
    {"outcome_status", "recovered_amount"}
)


def _check_dict_for_leakage(
    d: dict[str, Any],
    path: str = "",
    forbidden_keys: frozenset[str] = FORBIDDEN_HIDDEN_KEYS,
) -> None:
    """Recursively check that no forbidden hidden keys exist in a dictionary."""
    for k, v in d.items():
        curr_path = f"{path}.{k}" if path else k
        k_lower = k.lower()
        for forbidden in forbidden_keys:
            if forbidden == k_lower:
                msg = (
                    f"Anti-leakage violation: forbidden key '{k}' "
                    f"found at '{curr_path}'!"
                )
                raise ValueError(msg)
        if isinstance(v, dict):
            _check_dict_for_leakage(v, curr_path, forbidden_keys=forbidden_keys)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    _check_dict_for_leakage(
                        item, f"{curr_path}[{i}]", forbidden_keys=forbidden_keys
                    )


def validate_feature_snapshot(snapshot: FeatureSnapshot) -> None:
    """Validate that a feature snapshot contains no hidden or post-decision fields."""
    snap_dict = snapshot.model_dump()
    _check_dict_for_leakage(
        snap_dict, "FeatureSnapshot", forbidden_keys=FORBIDDEN_FEATURE_KEYS
    )


def validate_model_input_record(record: ModelInputRecord) -> None:
    """Validate that a model input record contains only legitimate features."""
    validate_feature_snapshot(record.features)

    # Extra check on training labels if present
    if record.training_label is not None:
        _check_dict_for_leakage(
            record.training_label.model_dump(),
            "ModelInputRecord.training_label",
            forbidden_keys=FORBIDDEN_HIDDEN_KEYS,
        )


def validate_split_integrity(
    train_set: GovernedDataset,
    val_set: GovernedDataset,
    test_set: GovernedDataset,
) -> None:
    """Verify zero record or scenario overlap across dataset splits."""
    train_scenarios = {r.model_input.scenario_id for r in train_set.records}
    val_scenarios = {r.model_input.scenario_id for r in val_set.records}
    test_scenarios = {r.model_input.scenario_id for r in test_set.records}

    train_val_overlap = train_scenarios.intersection(val_scenarios)
    if train_val_overlap:
        msg = (
            f"Split integrity failure: {len(train_val_overlap)} "
            "scenario IDs overlap between TRAIN and VAL!"
        )
        raise ValueError(msg)

    train_test_overlap = train_scenarios.intersection(test_scenarios)
    if train_test_overlap:
        msg = (
            f"Split integrity failure: {len(train_test_overlap)} "
            "scenario IDs overlap between TRAIN and TEST!"
        )
        raise ValueError(msg)

    val_test_overlap = val_scenarios.intersection(test_scenarios)
    if val_test_overlap:
        msg = (
            f"Split integrity failure: {len(val_test_overlap)} "
            "scenario IDs overlap between VAL and TEST!"
        )
        raise ValueError(msg)

    # Check unique record IDs across all splits
    all_record_ids: set[str] = set()
    for s_name, ds in [
        ("TRAIN", train_set),
        ("VAL", val_set),
        ("TEST", test_set),
    ]:
        for r in ds.records:
            rid = r.model_input.record_id
            if rid in all_record_ids:
                msg = (
                    f"Split integrity failure: duplicate record_id '{rid}' "
                    f"found in {s_name}!"
                )
                raise ValueError(msg)
            all_record_ids.add(rid)
