import functools
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.adversarial.enums import (
    ATTACK_SUITE_VERSION,
    AttackCategory,
    AttackDisposition,
    ScenarioId,
    Severity,
)

PHASE_17_BASELINE_REVISION = "9805456"


@functools.lru_cache(maxsize=1)
def get_current_code_revision() -> str:
    """Derive current git commit revision in a sanitized, deterministic way with fallback."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return PHASE_17_BASELINE_REVISION


def compute_canonical_hash(data: Any) -> str:
    """Compute a deterministic SHA-256 hash over canonically serialized JSON."""
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AttackCase(BaseModel):
    """Immutable specification of an adversarial test vector."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attack_id: str
    scenario_id: ScenarioId | str
    category: AttackCategory
    severity: Severity = Severity.HIGH
    seed: int = 42
    code_revision: str = Field(default_factory=get_current_code_revision)
    target_component: str
    expected_property: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    input_manifest_hash: str = ""

    @classmethod
    def create(
        cls,
        attack_id: str,
        scenario_id: ScenarioId | str,
        category: AttackCategory,
        target_component: str,
        expected_property: str,
        input_payload: dict[str, Any],
        seed: int = 42,
        severity: Severity = Severity.HIGH,
        code_revision: str | None = None,
    ) -> "AttackCase":
        """Factory method computing input manifest hash automatically."""
        rev = code_revision or get_current_code_revision()
        raw_dict = {
            "attack_id": attack_id,
            "scenario_id": str(scenario_id),
            "category": str(category),
            "severity": str(severity),
            "seed": seed,
            "code_revision": rev,
            "target_component": target_component,
            "expected_property": expected_property,
            "input_payload": input_payload,
        }
        manifest_hash = compute_canonical_hash(raw_dict)
        return cls(
            attack_id=attack_id,
            scenario_id=scenario_id,
            category=category,
            severity=severity,
            seed=seed,
            code_revision=rev,
            target_component=target_component,
            expected_property=expected_property,
            input_payload=input_payload,
            input_manifest_hash=manifest_hash,
        )


class AttackResult(BaseModel):
    """Immutable outcome of an executed attack case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attack_id: str
    scenario_id: ScenarioId | str
    disposition: AttackDisposition
    passed: bool
    expected_property: str
    observed_property: str
    sanitized_evidence: dict[str, Any] = Field(default_factory=dict)
    exception_type: str | None = None
    evidence_hash: str = ""
    executed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        attack_id: str,
        scenario_id: ScenarioId | str,
        disposition: AttackDisposition,
        passed: bool,
        expected_property: str,
        observed_property: str,
        sanitized_evidence: dict[str, Any],
        exception_type: str | None = None,
        executed_at: str | None = None,
    ) -> "AttackResult":
        """Factory method computing evidence hash automatically."""
        ts = executed_at or datetime.now(UTC).isoformat()
        raw = {
            "attack_id": attack_id,
            "scenario_id": str(scenario_id),
            "disposition": str(disposition),
            "passed": passed,
            "expected_property": expected_property,
            "observed_property": observed_property,
            "sanitized_evidence": sanitized_evidence,
            "exception_type": exception_type,
        }
        ev_hash = compute_canonical_hash(raw)
        return cls(
            attack_id=attack_id,
            scenario_id=scenario_id,
            disposition=disposition,
            passed=passed,
            expected_property=expected_property,
            observed_property=observed_property,
            sanitized_evidence=sanitized_evidence,
            exception_type=exception_type,
            evidence_hash=ev_hash,
            executed_at=ts,
        )


class AttackEvidence(BaseModel):
    """Immutable aggregate collection of attack results for forensic auditing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attack_run_id: str
    scenario_results: dict[str, list[AttackResult]] = Field(default_factory=dict)
    total_attacks: int = 0
    passed_attacks: int = 0
    failed_attacks: int = 0
    manifest_hash: str = ""
    evidence_hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AttackRun(BaseModel):
    """Immutable summary manifest of an entire adversarial test run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attack_run_id: str
    attack_suite_version: str = ATTACK_SUITE_VERSION
    seed: int
    scenario_ids: list[str]
    code_revision: str = Field(default_factory=get_current_code_revision)
    environment: str = "isolated_local_test"
    input_manifest_hash: str
    evidence_hash: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
