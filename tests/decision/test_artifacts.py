"""Unit tests for decision artifact serialization, loading, and identity."""

import json
from pathlib import Path

import pytest

from apro.decision.artifacts import (
    DECISION_ARTIFACT_SCHEMA_VERSION,
    DecisionEngineArtifact,
    load_decision_artifact,
    save_decision_artifact,
)
from apro.decision.economics import EconomicConfiguration
from apro.decision.eligibility import PolicyConfiguration


def test_save_and_load_decision_artifact(tmp_path: Path) -> None:
    """Verify artifact serialization and deterministic identity loading."""
    artifact = DecisionEngineArtifact.create(
        economic_config=EconomicConfiguration(minimum_expected_recovery_value=500),
        policy_config=PolicyConfiguration(max_retries=2),
    )
    art_path = tmp_path / "decision_engine.json"
    save_decision_artifact(artifact, art_path)

    loaded = load_decision_artifact(art_path)
    assert loaded.deterministic_identity == artifact.deterministic_identity
    assert loaded.economic_config.minimum_expected_recovery_value == 500
    assert loaded.policy_config.max_retries == 2


def test_incompatible_artifact_rejection(tmp_path: Path) -> None:
    """Verify rejection of incompatible schema version or corrupted fingerprint."""
    artifact = DecisionEngineArtifact.create()
    art_path = tmp_path / "corrupt_artifact.json"
    save_decision_artifact(artifact, art_path)

    # 1. Corrupt schema version
    data = json.loads(art_path.read_text(encoding="utf-8"))
    data["artifact_schema_version"] = "decision-artifact-v999"
    art_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Incompatible artifact schema version"):
        load_decision_artifact(art_path)

    # 2. Corrupt deterministic identity
    data["artifact_schema_version"] = DECISION_ARTIFACT_SCHEMA_VERSION
    data["deterministic_identity"] = "bad_hash_12345"
    art_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Corrupted deterministic identity"):
        load_decision_artifact(art_path)
