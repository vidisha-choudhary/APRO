"""Unit tests for Phase 10 PolicyArtifact serialization, hashing,
and version compatibility.
"""

import tempfile
from pathlib import Path

import pytest

from apro.policy.artifacts import (
    load_policy_artifact,
    save_policy_artifact,
)
from apro.policy.config import PolicyConfig


def test_artifact_save_load_roundtrip():
    """Verify saving PolicyArtifact to file and loading it recovers exact config."""
    cfg = PolicyConfig(
        max_retries=4,
        high_value_threshold=250000,
        min_decision_confidence=0.60,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        art_path = Path(tmpdir) / "policy_artifact.json"
        save_policy_artifact(cfg, art_path, metadata={"author": "vidisha"})

        assert art_path.exists()
        reloaded_cfg, reloaded_art = load_policy_artifact(art_path)

        assert reloaded_cfg.max_retries == 4
        assert reloaded_cfg.high_value_threshold == 250000
        assert reloaded_cfg.min_decision_confidence == 0.60
        assert (
            reloaded_art.deterministic_identity == cfg.compute_deterministic_identity()
        )
        assert reloaded_art.metadata.get("author") == "vidisha"


def test_artifact_load_nonexistent_file():
    """Verify loading nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_policy_artifact("nonexistent_policy_artifact.json")


def test_artifact_tamper_detection():
    """Verify modifying configuration payload invalidates SHA-256 hash identity."""
    cfg = PolicyConfig(max_retries=3)
    with tempfile.TemporaryDirectory() as tmpdir:
        art_path = Path(tmpdir) / "policy_artifact.json"
        save_policy_artifact(cfg, art_path)

        # Tamper with file contents directly
        with open(art_path, encoding="utf-8") as f:
            content = f.read()
        tampered_content = content.replace('"max_retries": 3', '"max_retries": 99')
        with open(art_path, "w", encoding="utf-8") as f:
            f.write(tampered_content)

        with pytest.raises(ValueError, match="Artifact hash mismatch"):
            load_policy_artifact(art_path)
