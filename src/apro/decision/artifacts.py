"""Artifact serialization, fingerprinting, and persistence for Phase 9."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from apro.decision.economics import EconomicConfiguration
from apro.decision.eligibility import PolicyConfiguration
from apro.decision.enums import (
    DECISION_MODEL_SCHEMA_VERSION,
    RECOVERY_ACTION_SCHEMA_VERSION,
    UTILITY_FORMULA_VERSION,
)
from apro.recovery_prediction.features import (
    RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
)

DECISION_ARTIFACT_SCHEMA_VERSION: str = "decision-artifact-v1"


class DecisionEngineArtifact(BaseModel):
    """Portable, serializable representation of Decision Engine configuration."""

    model_config = ConfigDict(frozen=True)

    artifact_schema_version: str = Field(default=DECISION_ARTIFACT_SCHEMA_VERSION)
    decision_model_version: str = Field(default=DECISION_MODEL_SCHEMA_VERSION)
    economic_config: EconomicConfiguration
    policy_config: PolicyConfiguration
    utility_formula_version: str = Field(default=UTILITY_FORMULA_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    feature_schema_version: str = Field(default="feature-schema-v1")
    prediction_feature_schema_version: str = Field(
        default=RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION
    )
    deterministic_identity: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def compute_deterministic_identity(
        cls,
        decision_model_version: str,
        economic_config: EconomicConfiguration,
        policy_config: PolicyConfiguration,
        utility_formula_version: str,
        action_schema_version: str,
        feature_schema_version: str,
        prediction_feature_schema_version: str = (
            RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION
        ),
    ) -> str:
        """Generate a SHA-256 fingerprint from invariant configuration components."""
        ident_dict = {
            "decision_model_version": decision_model_version,
            "economic_config": economic_config.model_dump(mode="json"),
            "policy_config": policy_config.model_dump(mode="json"),
            "utility_formula_version": utility_formula_version,
            "action_schema_version": action_schema_version,
            "feature_schema_version": feature_schema_version,
            "prediction_feature_schema_version": prediction_feature_schema_version,
        }
        serialized = json.dumps(ident_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        economic_config: EconomicConfiguration | None = None,
        policy_config: PolicyConfiguration | None = None,
        decision_model_version: str = DECISION_MODEL_SCHEMA_VERSION,
        feature_schema_version: str = "feature-schema-v1",
        prediction_feature_schema_version: str = (
            RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION
        ),
    ) -> "DecisionEngineArtifact":
        """Factory creating a DecisionEngineArtifact with calculated hash."""
        econ = economic_config or EconomicConfiguration()
        pol = policy_config or PolicyConfiguration()
        ident = cls.compute_deterministic_identity(
            decision_model_version=decision_model_version,
            economic_config=econ,
            policy_config=pol,
            utility_formula_version=UTILITY_FORMULA_VERSION,
            action_schema_version=RECOVERY_ACTION_SCHEMA_VERSION,
            feature_schema_version=feature_schema_version,
            prediction_feature_schema_version=prediction_feature_schema_version,
        )
        return cls(
            decision_model_version=decision_model_version,
            economic_config=econ,
            policy_config=pol,
            feature_schema_version=feature_schema_version,
            prediction_feature_schema_version=prediction_feature_schema_version,
            deterministic_identity=ident,
        )


def save_decision_artifact(
    artifact: DecisionEngineArtifact, file_path: Path | str
) -> Path:
    """Save a DecisionEngineArtifact to disk as JSON."""
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        f.write(artifact.model_dump_json(indent=2))
    return target


def load_decision_artifact(file_path: Path | str) -> DecisionEngineArtifact:
    """Load and validate a DecisionEngineArtifact from disk."""
    target = Path(file_path)
    if not target.exists():
        msg = f"Decision artifact file not found: {target}"
        raise FileNotFoundError(msg)

    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate Schema Version Compatibility
    schema_ver = data.get("artifact_schema_version")
    if schema_ver != DECISION_ARTIFACT_SCHEMA_VERSION:
        msg = (
            f"Incompatible artifact schema version '{schema_ver}'; "
            f"expected '{DECISION_ARTIFACT_SCHEMA_VERSION}'."
        )
        raise ValueError(msg)

    artifact = DecisionEngineArtifact.model_validate(data)

    # Re-verify deterministic hash
    expected_hash = DecisionEngineArtifact.compute_deterministic_identity(
        decision_model_version=artifact.decision_model_version,
        economic_config=artifact.economic_config,
        policy_config=artifact.policy_config,
        utility_formula_version=artifact.utility_formula_version,
        action_schema_version=artifact.action_schema_version,
        feature_schema_version=artifact.feature_schema_version,
    )
    if artifact.deterministic_identity != expected_hash:
        msg = (
            f"Corrupted deterministic identity: stored "
            f"'{artifact.deterministic_identity}', calculated '{expected_hash}'."
        )
        raise ValueError(msg)

    return artifact
