"""Authoritative enums and vocabulary constants for Phase 17 Adversarial Harness."""

from enum import StrEnum

ATTACK_SUITE_VERSION = "1.0.0"


class AttackCategory(StrEnum):
    """Classification taxonomy for adversarial attack vectors."""

    AUTH = "AUTH"
    STALE = "STALE"
    REPLAY = "REPLAY"
    RACE = "RACE"
    STATE = "STATE"
    TRUTH = "TRUTH"
    AUDIT = "AUDIT"
    EVAL = "EVAL"
    API = "API"
    SECRET = "SECRET"
    BOUNDARY = "BOUNDARY"


class AttackDisposition(StrEnum):
    """Observed outcome disposition of an adversarial attack."""

    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    CONTAINED = "CONTAINED"
    DETECTED = "DETECTED"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    UNEXPECTED_SUCCESS = "UNEXPECTED_SUCCESS"
    LEAKED = "LEAKED"
    CORRUPTED = "CORRUPTED"
    FAILED = "FAILED"


class Severity(StrEnum):
    """Security severity classification."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class ScenarioId(StrEnum):
    """Stable identifiers for the 10 authoritative adversarial scenarios."""

    SCENARIO_01_POLICY_BYPASS = "SCENARIO_01_POLICY_BYPASS"
    SCENARIO_02_STALE_AUTHORITY = "SCENARIO_02_STALE_AUTHORITY"
    SCENARIO_03_DUPLICATE_REPLAY_STORM = "SCENARIO_03_DUPLICATE_REPLAY_STORM"
    SCENARIO_04_CAPTURE_RACE = "SCENARIO_04_CAPTURE_RACE"
    SCENARIO_05_ILLEGAL_STATE = "SCENARIO_05_ILLEGAL_STATE"
    SCENARIO_06_TRUTH_PLANE = "SCENARIO_06_TRUTH_PLANE"
    SCENARIO_07_AUDIT_TAMPERING = "SCENARIO_07_AUDIT_TAMPERING"
    SCENARIO_08_BENCHMARK_TAMPERING = "SCENARIO_08_BENCHMARK_TAMPERING"
    SCENARIO_09_DASHBOARD_ABUSE = "SCENARIO_09_DASHBOARD_ABUSE"
    SCENARIO_10_SECRET_EXFILTRATION = "SCENARIO_10_SECRET_EXFILTRATION"


CANONICAL_SENTINELS: list[str] = [
    "sentinel_phase17_secret_87654321",
    "sentinel_card_number_4111222233334444",
    "sentinel_auth_header_bearer_xyz999",
    "sentinel_db_password_topsecret_2026",
    "sentinel_raw_provider_payload",
]

FORBIDDEN_EXTERNAL_MODULES: set[str] = {
    "requests",
    "aiohttp",
    "urllib.request",
    "socket",
}
