"""Authoritative scenario definitions and target metadata for Phase 17."""

from pydantic import BaseModel, ConfigDict

from apro.adversarial.enums import AttackCategory, ScenarioId, Severity


class ScenarioDefinition(BaseModel):
    """Metadata definition for an authoritative adversarial scenario."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: ScenarioId
    name: str
    category: AttackCategory
    severity: Severity
    target_component: str
    target_phase: str
    description: str
    expected_invariant: str


SCENARIO_REGISTRY: dict[ScenarioId, ScenarioDefinition] = {
    ScenarioId.SCENARIO_01_POLICY_BYPASS: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
        name="Policy Bypass & Unauthorized Action Execution Attack",
        category=AttackCategory.AUTH,
        severity=Severity.CRITICAL,
        target_component="ExecutionOrchestrator / PolicyEngine",
        target_phase="Phase 10 / Phase 11",
        description="Attempts to execute unapproved actions, spoof approvals, or forge reason codes.",
        expected_invariant="Unauthorized actions are rejected before execution with zero provider side-effects.",
    ),
    ScenarioId.SCENARIO_02_STALE_AUTHORITY: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_02_STALE_AUTHORITY,
        name="Stale Decision / Stale Policy Replay Attack",
        category=AttackCategory.STALE,
        severity=Severity.HIGH,
        target_component="ExecutionOrchestrator / StateGuard",
        target_phase="Phase 10 / Phase 11 / Phase 13",
        description="Replays older decision/policy artifacts against changed state or newer cycles.",
        expected_invariant="Stale authority is rejected; current state and policy remain authoritative.",
    ),
    ScenarioId.SCENARIO_03_DUPLICATE_REPLAY_STORM: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_03_DUPLICATE_REPLAY_STORM,
        name="Duplicate Replay Storm & Idempotency Attack",
        category=AttackCategory.REPLAY,
        severity=Severity.CRITICAL,
        target_component="ExecutionOrchestrator (PostgreSQL Idempotency)",
        target_phase="Phase 11 / Phase 13 / Phase 14",
        description="Concurrently replays identical execution requests to test exactly-once semantic advancement.",
        expected_invariant="Duplicate delivery produces exactly 1 execution and 1 side-effect.",
    ),
    ScenarioId.SCENARIO_04_CAPTURE_RACE: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_04_CAPTURE_RACE,
        name="Payment Capture Race & Concurrent State Attack",
        category=AttackCategory.RACE,
        severity=Severity.CRITICAL,
        target_component="StateGuard / ExecutionOrchestrator",
        target_phase="Phase 10 / Phase 11",
        description="Races payment webhook capture against scheduled retry dispatch.",
        expected_invariant="StateGuard rejects the stale/unsafe execution attempt before provider dispatch.",
    ),
    ScenarioId.SCENARIO_05_ILLEGAL_STATE: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_05_ILLEGAL_STATE,
        name="Illegal State Machine Transition Attack",
        category=AttackCategory.STATE,
        severity=Severity.CRITICAL,
        target_component="RecoveryCase / transition_recovery_case",
        target_phase="Phase 2 / Phase 11 / Phase 13",
        description="Attempts illegal transitions such as RECOVERED -> EXECUTING or STOPPED -> RETRY.",
        expected_invariant="Invalid state transitions are rejected with explicit state errors; terminal state holds.",
    ),
    ScenarioId.SCENARIO_06_TRUTH_PLANE: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_06_TRUTH_PLANE,
        name="Oracle / Truth-Plane Leakage & Runtime Manipulation Attack",
        category=AttackCategory.TRUTH,
        severity=Severity.CRITICAL,
        target_component="EconomicDecisionEngine / TruthPlaneSeparation",
        target_phase="Phase 9 / Phase 14 / Phase 15",
        description="Injects oracle_action and latent evaluator truth to attempt runtime action selection control.",
        expected_invariant="Runtime authorities cannot consume evaluator hidden truth; zero oracle-driven decision control.",
    ),
    ScenarioId.SCENARIO_07_AUDIT_TAMPERING: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_07_AUDIT_TAMPERING,
        name="Audit Tampering & Case Reconstruction Attack",
        category=AttackCategory.AUDIT,
        severity=Severity.CRITICAL,
        target_component="PostgreSQL trg_audit_events_immutability / CaseReconstructionService",
        target_phase="Phase 14",
        description="Attempts direct SQL UPDATE/DELETE on audit_events and reconstruction of truncated logs.",
        expected_invariant="Append-only trigger prevents mutation; missing mandatory stages report INCOMPLETE.",
    ),
    ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING,
        name="Benchmark Report Tampering & Hash Integrity Attack",
        category=AttackCategory.EVAL,
        severity=Severity.CRITICAL,
        target_component="PostgreSQLEvaluationArtifactStore / Evaluation Triggers",
        target_phase="Phase 15",
        description="Attempts to overwrite persisted benchmark runs or mutate report payloads via direct SQL.",
        expected_invariant="Immutable reports cannot be overwritten or mutated; cryptographic hashes remain stable.",
    ),
    ScenarioId.SCENARIO_09_DASHBOARD_ABUSE: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_09_DASHBOARD_ABUSE,
        name="Dashboard / API Read-Only Boundary Abuse",
        category=AttackCategory.API,
        severity=Severity.HIGH,
        target_component="DashboardRouter / FastAPI app",
        target_phase="Phase 16",
        description="Attacks API using mutating HTTP methods (POST/PUT/DELETE) and SQL injection strings.",
        expected_invariant="API remains strictly read-only (405 on writes) with zero state change in PostgreSQL.",
    ),
    ScenarioId.SCENARIO_10_SECRET_EXFILTRATION: ScenarioDefinition(
        scenario_id=ScenarioId.SCENARIO_10_SECRET_EXFILTRATION,
        name="Secret & PII Sentinel Exfiltration Attack",
        category=AttackCategory.SECRET,
        severity=Severity.CRITICAL,
        target_component="TelemetrySanitizer / API Response Boundary",
        target_phase="Cross-Phase",
        description="Injects 5 persistent sentinels into PostgreSQL to verify redaction across audit logs and API responses.",
        expected_invariant="Zero sentinel leakage in logs, audit payloads, benchmark reports, or API responses.",
    ),
}
