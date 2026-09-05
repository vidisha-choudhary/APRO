"""Deterministic adversarial test case generators for Phase 17."""

import random

from apro.adversarial.enums import (
    CANONICAL_SENTINELS,
    AttackCategory,
    ScenarioId,
    Severity,
)
from apro.adversarial.models import AttackCase


def generate_policy_bypass_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate deterministic attack cases attempting to bypass Phase 10 policy authorization."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Blocked action execution
    cases.append(
        AttackCase.create(
            attack_id=f"att_auth_block_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
            category=AttackCategory.AUTH,
            severity=Severity.CRITICAL,
            target_component="ExecutionOrchestrator.validate_policy_authorization",
            expected_property="PolicyOutcome.BLOCK must reject execution without provider dispatch",
            input_payload={
                "outcome": "BLOCK",
                "effective_action": "RETRY",
                "reason_code": "MAX_RETRIES_REACHED",
                "has_approval": False,
            },
            seed=seed,
        )
    )

    # Vector 2: Missing human approval token
    cases.append(
        AttackCase.create(
            attack_id=f"att_auth_approval_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
            category=AttackCategory.AUTH,
            severity=Severity.HIGH,
            target_component="ExecutionOrchestrator.validate_policy_authorization",
            expected_property="REQUIRE_HUMAN_APPROVAL must reject execution when approval token is missing",
            input_payload={
                "outcome": "REQUIRE_HUMAN_APPROVAL",
                "effective_action": "ALTERNATE_RECOVERY",
                "approval_reference": None,
                "reason_code": "HIGH_VALUE_THRESHOLD",
            },
            seed=seed,
        )
    )

    # Vector 3: Effective action mismatch (tampered dispatch)
    cases.append(
        AttackCase.create(
            attack_id=f"att_auth_mismatch_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
            category=AttackCategory.AUTH,
            severity=Severity.CRITICAL,
            target_component="ExecutionOrchestrator.validate_policy_authorization",
            expected_property="Action type mismatch between policy approval and execution request must be rejected",
            input_payload={
                "outcome": "ALLOW",
                "policy_effective_action": "STOP",
                "requested_execution_action": "RETRY",
                "reason_code": "POLICY_ALLOWED",
            },
            seed=seed,
        )
    )

    # Vector 4: Forged reason code against safety budget overflow
    cases.append(
        AttackCase.create(
            attack_id=f"att_auth_forged_reason_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
            category=AttackCategory.AUTH,
            severity=Severity.HIGH,
            target_component="PolicyEngine.evaluate",
            expected_property="Forged reason code cannot override hard daily safety budget rules",
            input_payload={
                "daily_attempt_count": 10,
                "max_allowed_attempts": 3,
                "forged_reason": "POLICY_ALLOWED",
            },
            seed=seed,
        )
    )

    # Vector 5: Forged decision provenance signature
    cases.append(
        AttackCase.create(
            attack_id=f"att_auth_signature_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
            category=AttackCategory.AUTH,
            severity=Severity.HIGH,
            target_component="ExecutionOrchestrator.validate_policy_authorization",
            expected_property="Forged decision_id not matching case_id must be rejected",
            input_payload={
                "case_id": "case_legit_001",
                "forged_case_id_in_policy": "case_attacker_999",
                "outcome": "ALLOW",
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_stale_authority_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate deterministic attack cases attempting to replay stale decisions and policies."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Expired decision cycle replay
    cases.append(
        AttackCase.create(
            attack_id=f"att_stale_cycle_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_02_STALE_AUTHORITY,
            category=AttackCategory.STALE,
            severity=Severity.HIGH,
            target_component="ExecutionOrchestrator",
            expected_property="Decision from previous cycle cannot authorize execution in current cycle",
            input_payload={
                "decision_cycle": 1,
                "case_current_cycle": 2,
                "action": "RETRY",
            },
            seed=seed,
        )
    )

    # Vector 2: Replay against changed case state
    cases.append(
        AttackCase.create(
            attack_id=f"att_stale_state_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_02_STALE_AUTHORITY,
            category=AttackCategory.STALE,
            severity=Severity.HIGH,
            target_component="StateGuard.recheck",
            expected_property="Policy issued during FAILED state must be rejected if payment transitioned to CAPTURED",
            input_payload={
                "policy_payment_state": "FAILED",
                "current_payment_state": "CAPTURED",
                "action": "RETRY",
            },
            seed=seed,
        )
    )

    # Vector 3: Stale policy reused for different action
    cases.append(
        AttackCase.create(
            attack_id=f"att_stale_action_mutation_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_02_STALE_AUTHORITY,
            category=AttackCategory.STALE,
            severity=Severity.HIGH,
            target_component="ExecutionOrchestrator",
            expected_property="Policy authorization bound to Action A cannot authorize Action B",
            input_payload={
                "policy_action_id": "act_001_retry",
                "target_action_id": "act_002_payment_link",
            },
            seed=seed,
        )
    )

    # Vector 4: Replay against terminal STOPPED case
    cases.append(
        AttackCase.create(
            attack_id=f"att_stale_terminal_stopped_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_02_STALE_AUTHORITY,
            category=AttackCategory.STALE,
            severity=Severity.CRITICAL,
            target_component="ExecutionOrchestrator.validate_execution_preconditions",
            expected_property="Stale authorization cannot resurrect or execute on a STOPPED case",
            input_payload={
                "case_status": "STOPPED",
                "action": "RETRY",
            },
            seed=seed,
        )
    )

    # Vector 5: Replay against terminal RECOVERED case
    cases.append(
        AttackCase.create(
            attack_id=f"att_stale_terminal_recovered_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_02_STALE_AUTHORITY,
            category=AttackCategory.STALE,
            severity=Severity.CRITICAL,
            target_component="ExecutionOrchestrator.validate_execution_preconditions",
            expected_property="Stale authorization cannot execute on an already RECOVERED case",
            input_payload={
                "case_status": "RECOVERED",
                "action": "RETRY",
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_replay_storm_cases(seed: int, count: int = 50) -> list[AttackCase]:
    """Generate a concurrent duplicate replay storm of 50+ identical operations."""
    rng = random.Random(seed)
    base_idempotency_key = f"idem_storm_key_{rng.randint(100000, 999999)}"
    cases: list[AttackCase] = []

    for i in range(count):
        cases.append(
            AttackCase.create(
                attack_id=f"att_replay_storm_{i:03d}_{rng.randint(100, 999)}",
                scenario_id=ScenarioId.SCENARIO_03_DUPLICATE_REPLAY_STORM,
                category=AttackCategory.REPLAY,
                severity=Severity.CRITICAL if i == 0 else Severity.MEDIUM,
                target_component="ExecutionOrchestrator.execute (PostgreSQL Idempotency)",
                expected_property="Duplicate replay storm must result in exactly 1 execution and 1 side-effect",
                input_payload={
                    "storm_index": i,
                    "idempotency_key": base_idempotency_key,
                    "case_id": "case_storm_001",
                    "action_id": "act_storm_001",
                    "action_type": "RETRY",
                },
                seed=seed,
            )
        )

    return cases


def generate_capture_race_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases simulating race conditions between capture and execution."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    for i in range(count):
        cases.append(
            AttackCase.create(
                attack_id=f"att_race_capture_{i:02d}_{rng.randint(1000, 9999)}",
                scenario_id=ScenarioId.SCENARIO_04_CAPTURE_RACE,
                category=AttackCategory.RACE,
                severity=Severity.CRITICAL,
                target_component="StateGuard / ExecutionOrchestrator",
                expected_property="StateGuard rejects the stale/unsafe execution attempt before provider dispatch",
                input_payload={
                    "race_index": i,
                    "payment_id": f"pay_race_{i:02d}",
                    "initial_status": "FAILED",
                    "webhook_transition_status": "CAPTURED",
                    "concurrent_execution_action": "RETRY",
                },
                seed=seed,
            )
        )

    return cases[:count]


def generate_illegal_state_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases attempting illegal state machine transitions."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Terminal RECOVERED to EXECUTING
    cases.append(
        AttackCase.create(
            attack_id=f"att_state_rec_exec_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_05_ILLEGAL_STATE,
            category=AttackCategory.STATE,
            severity=Severity.CRITICAL,
            target_component="transition_recovery_case",
            expected_property="Terminal RECOVERED cannot transition to EXECUTING",
            input_payload={
                "current_status": "RECOVERED",
                "target_status": "EXECUTING",
            },
            seed=seed,
        )
    )

    # Vector 2: Terminal STOPPED to DIAGNOSING
    cases.append(
        AttackCase.create(
            attack_id=f"att_state_stop_diag_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_05_ILLEGAL_STATE,
            category=AttackCategory.STATE,
            severity=Severity.HIGH,
            target_component="transition_recovery_case",
            expected_property="Terminal STOPPED cannot transition to DIAGNOSING",
            input_payload={
                "current_status": "STOPPED",
                "target_status": "DIAGNOSING",
            },
            seed=seed,
        )
    )

    # Vector 3: Terminal ESCALATED to ACTION_APPROVED
    cases.append(
        AttackCase.create(
            attack_id=f"att_state_esc_approved_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_05_ILLEGAL_STATE,
            category=AttackCategory.STATE,
            severity=Severity.HIGH,
            target_component="transition_recovery_case",
            expected_property="Terminal ESCALATED cannot transition to ACTION_APPROVED automatically",
            input_payload={
                "current_status": "ESCALATED",
                "target_status": "ACTION_APPROVED",
            },
            seed=seed,
        )
    )

    # Vector 4: Outcome reversal from RECOVERED to FAILED
    cases.append(
        AttackCase.create(
            attack_id=f"att_state_outcome_reversal_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_05_ILLEGAL_STATE,
            category=AttackCategory.STATE,
            severity=Severity.CRITICAL,
            target_component="OutcomeProcessor",
            expected_property="Observed RECOVERED outcome cannot be reversed or invalidated to FAILED",
            input_payload={
                "initial_outcome": "RECOVERED",
                "attempted_reversal": "FAILED",
            },
            seed=seed,
        )
    )

    # Vector 5: Arbitrary status skip from NEW to OBSERVING
    cases.append(
        AttackCase.create(
            attack_id=f"att_state_skip_observing_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_05_ILLEGAL_STATE,
            category=AttackCategory.STATE,
            severity=Severity.MEDIUM,
            target_component="transition_recovery_case",
            expected_property="NEW cannot jump directly to OBSERVING bypassing execution",
            input_payload={
                "current_status": "NEW",
                "target_status": "OBSERVING",
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_truth_plane_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases injecting oracle and latent evaluation truth into runtime inputs."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Injected oracle_action into diagnosis payload
    cases.append(
        AttackCase.create(
            attack_id=f"att_truth_oracle_action_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_06_TRUTH_PLANE,
            category=AttackCategory.TRUTH,
            severity=Severity.CRITICAL,
            target_component="EconomicDecisionEngine.decide",
            expected_property="Injected oracle_action must not influence EconomicDecisionEngine ranking or leak into output",
            input_payload={
                "injected_field": "oracle_action",
                "injected_value": "ESCALATE",
                "legitimate_recommended": "RETRY",
            },
            seed=seed,
        )
    )

    # Vector 2: Injected potential_outcomes into prediction payload
    cases.append(
        AttackCase.create(
            attack_id=f"att_truth_potential_outcomes_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_06_TRUTH_PLANE,
            category=AttackCategory.TRUTH,
            severity=Severity.HIGH,
            target_component="OutcomePrediction / DecisionEngine",
            expected_property="Injected potential_outcomes must not alter runtime decision logic or evidence",
            input_payload={
                "injected_field": "potential_outcomes",
                "injected_value": {
                    "RETRY": {"status": "SUCCESS", "recovered_amount": 50000}
                },
            },
            seed=seed,
        )
    )

    # Vector 3: Injected latent_recoverability into input record
    cases.append(
        AttackCase.create(
            attack_id=f"att_truth_latent_rec_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_06_TRUTH_PLANE,
            category=AttackCategory.TRUTH,
            severity=Severity.HIGH,
            target_component="EconomicDecisionEngine",
            expected_property="Hidden recoverability truth must be isolated from runtime decision authority",
            input_payload={
                "injected_field": "hidden_recoverability",
                "injected_value": True,
            },
            seed=seed,
        )
    )

    # Vector 4: Injected latent_probability
    cases.append(
        AttackCase.create(
            attack_id=f"att_truth_latent_prob_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_06_TRUTH_PLANE,
            category=AttackCategory.TRUTH,
            severity=Severity.HIGH,
            target_component="EconomicDecisionEngine",
            expected_property="Latent simulator probability cannot control action selection",
            input_payload={
                "injected_field": "latent_probability",
                "injected_value": 0.999,
            },
            seed=seed,
        )
    )

    # Vector 5: Injected ground_truth_recovered into audit trail
    cases.append(
        AttackCase.create(
            attack_id=f"att_truth_audit_leak_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_06_TRUTH_PLANE,
            category=AttackCategory.TRUTH,
            severity=Severity.HIGH,
            target_component="AuditService.record_event",
            expected_property="Audit events cannot record or expose simulator ground truth",
            input_payload={
                "injected_field": "ground_truth_recovered",
                "injected_value": True,
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_audit_tampering_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases attempting to mutate audit logs and corrupt reconstruction."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Direct SQL UPDATE on audit_events
    cases.append(
        AttackCase.create(
            attack_id=f"att_audit_sql_update_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_07_AUDIT_TAMPERING,
            category=AttackCategory.AUDIT,
            severity=Severity.CRITICAL,
            target_component="PostgreSQL trg_audit_events_immutability",
            expected_property="Direct SQL UPDATE on audit_events must be rejected by PostgreSQL append-only trigger",
            input_payload={
                "sql_operation": "UPDATE",
                "table": "audit_events",
            },
            seed=seed,
        )
    )

    # Vector 2: Direct SQL DELETE on audit_events
    cases.append(
        AttackCase.create(
            attack_id=f"att_audit_sql_delete_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_07_AUDIT_TAMPERING,
            category=AttackCategory.AUDIT,
            severity=Severity.CRITICAL,
            target_component="PostgreSQL trg_audit_events_immutability",
            expected_property="Direct SQL DELETE on audit_events must be rejected by PostgreSQL append-only trigger",
            input_payload={
                "sql_operation": "DELETE",
                "table": "audit_events",
            },
            seed=seed,
        )
    )

    # Vector 3: Duplicate audit event ID insertion conflict
    cases.append(
        AttackCase.create(
            attack_id=f"att_audit_dup_pk_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_07_AUDIT_TAMPERING,
            category=AttackCategory.AUDIT,
            severity=Severity.HIGH,
            target_component="AuditEventRepository.append",
            expected_property="Duplicate primary key insertion into audit_events must fail closed without corruption",
            input_payload={
                "duplicate_audit_event_id": "ev_fixed_duplicate_001",
            },
            seed=seed,
        )
    )

    # Vector 4: Case reconstruction with truncated/missing mandatory lifecycle events
    cases.append(
        AttackCase.create(
            attack_id=f"att_audit_reconstruction_incomplete_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_07_AUDIT_TAMPERING,
            category=AttackCategory.AUDIT,
            severity=Severity.HIGH,
            target_component="CaseReconstructionService.reconstruct_case",
            expected_property="Missing mandatory lifecycle stages must yield INCOMPLETE/CORRUPT, never false COMPLETE",
            input_payload={
                "missing_stages": ["DIAGNOSIS", "DECISION", "POLICY"],
            },
            seed=seed,
        )
    )

    # Vector 5: Event timestamp out-of-order tamper
    cases.append(
        AttackCase.create(
            attack_id=f"att_audit_order_tamper_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_07_AUDIT_TAMPERING,
            category=AttackCategory.AUDIT,
            severity=Severity.HIGH,
            target_component="AuditIntegrityChecker.validate_events_integrity",
            expected_property="Out-of-order or inverted timestamps must be flagged as integrity invalid",
            input_payload={
                "tampered_order": ["EXECUTION_STARTED", "CASE_CREATED"],
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_benchmark_tampering_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases attempting to tamper with immutable benchmark evaluation reports."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Overwrite existing benchmark run with conflicting payload
    cases.append(
        AttackCase.create(
            attack_id=f"att_eval_conflict_overwrite_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING,
            category=AttackCategory.EVAL,
            severity=Severity.CRITICAL,
            target_component="PostgreSQLEvaluationArtifactStore.save_report",
            expected_property="Attempt to save conflicting benchmark report for existing run_id must raise EvaluationPersistenceError",
            input_payload={
                "target_run_id": "run_tamper_001",
                "tampered_recovery_rate": 0.99,
            },
            seed=seed,
        )
    )

    # Vector 2: Direct SQL UPDATE on evaluation_benchmark_reports
    cases.append(
        AttackCase.create(
            attack_id=f"att_eval_sql_update_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING,
            category=AttackCategory.EVAL,
            severity=Severity.CRITICAL,
            target_component="PostgreSQL trg_evaluation_benchmark_reports_immutability",
            expected_property="Direct SQL UPDATE on evaluation_benchmark_reports must be rejected by PostgreSQL trigger",
            input_payload={
                "sql_operation": "UPDATE",
                "table": "evaluation_benchmark_reports",
            },
            seed=seed,
        )
    )

    # Vector 3: Direct SQL DELETE on evaluation_benchmark_reports
    cases.append(
        AttackCase.create(
            attack_id=f"att_eval_sql_delete_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING,
            category=AttackCategory.EVAL,
            severity=Severity.CRITICAL,
            target_component="PostgreSQL trg_evaluation_benchmark_reports_immutability",
            expected_property="Direct SQL DELETE on evaluation_benchmark_reports must be rejected by PostgreSQL trigger",
            input_payload={
                "sql_operation": "DELETE",
                "table": "evaluation_benchmark_reports",
            },
            seed=seed,
        )
    )

    # Vector 4: Config tampering changes report_hash
    cases.append(
        AttackCase.create(
            attack_id=f"att_eval_hash_integrity_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING,
            category=AttackCategory.EVAL,
            severity=Severity.HIGH,
            target_component="compute_report_hash",
            expected_property="Tampering with bootstrap seed or metrics produces mismatched report_hash",
            input_payload={
                "modified_seed": 9999,
            },
            seed=seed,
        )
    )

    # Vector 5: Run cross-talk isolation
    cases.append(
        AttackCase.create(
            attack_id=f"att_eval_run_isolation_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING,
            category=AttackCategory.EVAL,
            severity=Severity.HIGH,
            target_component="DashboardService.resolve_benchmark_report",
            expected_property="Querying Run A returns strictly Run A's data, never Run B's metadata",
            input_payload={
                "query_run_id": "run_a",
                "other_run_id": "run_b",
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_dashboard_abuse_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases targeting Phase 16 read-only dashboard API surfaces."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    # Vector 1: Mutating HTTP POST request
    cases.append(
        AttackCase.create(
            attack_id=f"att_api_post_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_09_DASHBOARD_ABUSE,
            category=AttackCategory.API,
            severity=Severity.HIGH,
            target_component="DashboardRouter",
            expected_property="POST /api/dashboard/* must return 405 Method Not Allowed",
            input_payload={
                "method": "POST",
                "path": "/api/dashboard/overview",
                "body": {"override": True},
            },
            seed=seed,
        )
    )

    # Vector 2: Mutating HTTP DELETE request
    cases.append(
        AttackCase.create(
            attack_id=f"att_api_delete_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_09_DASHBOARD_ABUSE,
            category=AttackCategory.API,
            severity=Severity.HIGH,
            target_component="DashboardRouter",
            expected_property="DELETE /api/dashboard/cases/123 must return 405 Method Not Allowed",
            input_payload={
                "method": "DELETE",
                "path": "/api/dashboard/cases/case_001",
            },
            seed=seed,
        )
    )

    # Vector 3: Unknown benchmark run ID returns 404
    cases.append(
        AttackCase.create(
            attack_id=f"att_api_unknown_run_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_09_DASHBOARD_ABUSE,
            category=AttackCategory.API,
            severity=Severity.MEDIUM,
            target_component="DashboardRouter.get_overview",
            expected_property="GET /api/dashboard/overview?benchmark_run_id=unknown_999 must return 404 Not Found",
            input_payload={
                "method": "GET",
                "path": "/api/dashboard/overview",
                "params": {"benchmark_run_id": "unknown_run_non_existent_999"},
            },
            seed=seed,
        )
    )

    # Vector 4: SQL injection attempt in search parameter
    cases.append(
        AttackCase.create(
            attack_id=f"att_api_sqli_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_09_DASHBOARD_ABUSE,
            category=AttackCategory.API,
            severity=Severity.HIGH,
            target_component="DashboardRouter.list_cases",
            expected_property="SQL injection in search param is parameterized and safely returns 200 with 0 matches",
            input_payload={
                "method": "GET",
                "path": "/api/dashboard/cases",
                "params": {"search": "case_1' OR 1=1 --"},
            },
            seed=seed,
        )
    )

    # Vector 5: Non-existent case detail returns 404
    cases.append(
        AttackCase.create(
            attack_id=f"att_api_case_404_{rng.randint(1000, 9999)}",
            scenario_id=ScenarioId.SCENARIO_09_DASHBOARD_ABUSE,
            category=AttackCategory.API,
            severity=Severity.MEDIUM,
            target_component="DashboardRouter.get_case_detail",
            expected_property="GET /api/dashboard/cases/non_existent_uuid returns 404 Not Found",
            input_payload={
                "method": "GET",
                "path": "/api/dashboard/cases/00000000-0000-0000-0000-000000000000",
            },
            seed=seed,
        )
    )

    return cases[:count]


def generate_secret_exfiltration_cases(seed: int, count: int = 5) -> list[AttackCase]:
    """Generate attack cases injecting sensitive sentinels to test sanitization and exfiltration resistance."""
    rng = random.Random(seed)
    cases: list[AttackCase] = []

    for i, sentinel in enumerate(CANONICAL_SENTINELS[:count]):
        cases.append(
            AttackCase.create(
                attack_id=f"att_secret_{i:02d}_{rng.randint(1000, 9999)}",
                scenario_id=ScenarioId.SCENARIO_10_SECRET_EXFILTRATION,
                category=AttackCategory.SECRET,
                severity=Severity.CRITICAL,
                target_component="TelemetrySanitizer / API Response Boundary",
                expected_property=f"Sentinel {sentinel} must be completely redacted and never appear in API responses or logs",
                input_payload={
                    "sentinel_index": i,
                    "sentinel_token": sentinel,
                    "target_surface": "audit_and_api",
                },
                seed=seed,
            )
        )

    return cases[:count]


def generate_all_attack_cases(
    seed: int, count_per_scenario: int | None = None
) -> dict[ScenarioId, list[AttackCase]]:
    """Generate deterministic attack cases for all 10 authoritative scenarios."""
    cnt = count_per_scenario if count_per_scenario is not None else 5
    storm_cnt = count_per_scenario if count_per_scenario is not None else 50
    return {
        ScenarioId.SCENARIO_01_POLICY_BYPASS: generate_policy_bypass_cases(seed, cnt),
        ScenarioId.SCENARIO_02_STALE_AUTHORITY: generate_stale_authority_cases(
            seed, cnt
        ),
        ScenarioId.SCENARIO_03_DUPLICATE_REPLAY_STORM: generate_replay_storm_cases(
            seed, storm_cnt
        ),
        ScenarioId.SCENARIO_04_CAPTURE_RACE: generate_capture_race_cases(seed, cnt),
        ScenarioId.SCENARIO_05_ILLEGAL_STATE: generate_illegal_state_cases(seed, cnt),
        ScenarioId.SCENARIO_06_TRUTH_PLANE: generate_truth_plane_cases(seed, cnt),
        ScenarioId.SCENARIO_07_AUDIT_TAMPERING: generate_audit_tampering_cases(
            seed, cnt
        ),
        ScenarioId.SCENARIO_08_BENCHMARK_TAMPERING: generate_benchmark_tampering_cases(
            seed, cnt
        ),
        ScenarioId.SCENARIO_09_DASHBOARD_ABUSE: generate_dashboard_abuse_cases(
            seed, cnt
        ),
        ScenarioId.SCENARIO_10_SECRET_EXFILTRATION: generate_secret_exfiltration_cases(
            seed, cnt
        ),
    }
