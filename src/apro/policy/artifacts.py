"""Policy artifact serialization, JSON export, hashing, and version loading."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.policy.config import PolicyConfig
from apro.policy.enums import (
    POLICY_ARTIFACT_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    POLICY_VERSION,
    RuleId,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_SCHEMA_VERSION,
)


class PolicyArtifact(BaseModel):
    """Declarative, portable, versioned policy artifact."""

    model_config = ConfigDict(frozen=True)

    policy_version: str = Field(default=POLICY_VERSION)
    policy_schema_version: str = Field(default=POLICY_SCHEMA_VERSION)
    artifact_schema_version: str = Field(default=POLICY_ARTIFACT_SCHEMA_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    deterministic_identity: str
    config: dict[str, Any]
    registered_rules: list[str]
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_policy_artifact(
    config: PolicyConfig,
    metadata: dict[str, Any] | None = None,
) -> PolicyArtifact:
    """Construct an immutable PolicyArtifact from a PolicyConfig instance."""
    ident = config.compute_deterministic_identity()
    return PolicyArtifact(
        policy_version=config.policy_version,
        policy_schema_version=config.policy_schema_version,
        artifact_schema_version=POLICY_ARTIFACT_SCHEMA_VERSION,
        action_schema_version=config.action_schema_version,
        deterministic_identity=ident,
        config=config.to_dict(),
        registered_rules=[r.value for r in RuleId],
        created_at=datetime.now(UTC).isoformat(),
        metadata=metadata or {},
    )


def save_policy_artifact(
    config: PolicyConfig,
    file_path: Path | str,
    metadata: dict[str, Any] | None = None,
) -> PolicyArtifact:
    """Save a PolicyArtifact to a JSON file."""
    artifact = build_policy_artifact(config, metadata=metadata)
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(artifact.model_dump(), indent=2, sort_keys=True))
    return artifact


def load_policy_artifact(file_path: Path | str) -> tuple[PolicyConfig, PolicyArtifact]:
    """Load and validate a PolicyArtifact from a JSON file (fail-closed)."""
    path = Path(file_path)
    if not path.exists():
        msg = f"Policy artifact not found at {path}"
        raise FileNotFoundError(msg)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    artifact = PolicyArtifact(**data)

    # Schema compatibility validation
    if artifact.policy_schema_version != POLICY_SCHEMA_VERSION:
        msg = (
            f"Incompatible policy schema version '{artifact.policy_schema_version}' "
            f"(expected '{POLICY_SCHEMA_VERSION}')"
        )
        raise ValueError(msg)
    if artifact.action_schema_version != RECOVERY_ACTION_SCHEMA_VERSION:
        msg = (
            f"Incompatible action schema version '{artifact.action_schema_version}' "
            f"(expected '{RECOVERY_ACTION_SCHEMA_VERSION}')"
        )
        raise ValueError(msg)

    # Reconstruct and validate configuration
    config = PolicyConfig.from_dict(artifact.config)
    expected_ident = config.compute_deterministic_identity()
    if artifact.deterministic_identity != expected_ident:
        msg = (
            f"Artifact hash mismatch: computed '{expected_ident}' "
            f"vs recorded '{artifact.deterministic_identity}'"
        )
        raise ValueError(msg)

    return config, artifact


__all__ = [
    "PolicyArtifact",
    "build_policy_artifact",
    "load_policy_artifact",
    "save_policy_artifact",
]
