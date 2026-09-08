# APRO — Security & Adversarial Attack Verification Results

This document summarizes the adversarial security architecture, attack scenarios, acceptance criteria, and verified invariants implemented in Phase 17 ([`src/apro/adversarial/`](../src/apro/adversarial)).

---

## 1. Adversarial Harness Overview

Phase 17 introduced a deterministic, automated adversarial security harness that systematically attempts to violate APRO’s authority boundaries, safety invariants, truth-plane separation, immutability, idempotency, and data sanitization.

### Core Testing Invariants

1. **Local-Only Execution:** All attacks execute locally within isolated test fixtures. No live external network or provider calls are made.
2. **Deterministic & Seeded:** Attack suites run with a deterministic random seed (default: `1701`), generating an immutable input manifest and a stable SHA-256 canonical evidence hash.
3. **Dual-Database Topology:** Attacks run strictly against `apro_attack_db`. The judge/demo database (`apro_test_db`) is cryptographically fingerprinted before and after execution to prove zero mutations occur.
4. **AST Self-Inspection:** The harness uses Python AST analysis to verify that no unconditional pass shortcuts, hardcoded credentials, or test fixture imports exist in production code.

---

## 2. The 10 Adversarial Attack Scenarios

| Scenario ID | Attack Vector Tested | Invariant Verified | Result Disposition |
|---|---|---|---|
| `SCENARIO_01_POLICY_BYPASS` | Injecting unapproved, denied, or forged policy decisions into execution framework. | Unapproved requests are rejected with `ExecutionAuthorizationError`. 0 unauthorized executions. | **BLOCKED** |
| `SCENARIO_02_STALE_AUTHORITY` | Replaying expired authorization tokens after case state or version changes. | Stale authorization tokens are rejected; requires fresh policy evaluation. | **REJECTED** |
| `SCENARIO_03_DUPLICATE_REPLAY_STORM` | Flooding 50 concurrent duplicate webhook deliveries and execution requests. | Transactional idempotency ensures single execution record and exactly-once advancement. | **CONTAINED** |
| `SCENARIO_04_CAPTURE_RACE` | Concurrent race conditions attempting double-captures or double-recoveries. | Atomicity guards ensure only one capture succeeds; secondary calls return consistent state. | **CONTAINED** |
| `SCENARIO_05_ILLEGAL_STATE` | Attempting to reopen or mutate closed cases (`CLOSED_RECOVERED`, `CLOSED_UNRECOVERED`). | State machine rejects illegal transitions. Terminal states remain immutable. | **REJECTED** |
| `SCENARIO_06_TRUTH_PLANE` | Injecting counterfactual oracle labels into runtime decision and policy inputs. | Complete truth-plane isolation; runtime logic observes only historical telemetry. | **BLOCKED** |
| `SCENARIO_07_AUDIT_TAMPERING` | Executing direct SQL `UPDATE` and `DELETE` queries on `audit_events`. | Blocked by PostgreSQL trigger `prevent_audit_events_mutation`. Rows remain unchanged. | **BLOCKED** |
| `SCENARIO_08_BENCHMARK_TAMPERING` | Executing direct SQL mutations on persisted `evaluation_reports` or overwriting existing runs. | Blocked by PostgreSQL trigger `prevent_benchmark_reports_mutation`. Reports remain immutable. | **BLOCKED** |
| `SCENARIO_09_DASHBOARD_ABUSE` | Sending mutating HTTP methods (`POST`, `PUT`, `DELETE`, `PATCH`) and malformed parameters to dashboard. | All mutations rejected with HTTP 405 Method Not Allowed. Dashboard remains strictly read-only. | **REJECTED** |
| `SCENARIO_10_SECRET_EXFILTRATION` | Persisting 5 canonical sentinels into case attributes and inspecting all outputs. | Sentinels are masked across logs, audit records, API endpoints, and exported manifests. | **CONTAINED** |

---

## 3. Acceptance Criteria Structure (AC-01 through AC-90)

The acceptance runner ([`scripts/run_phase_17_acceptance.py`](../scripts/run_phase_17_acceptance.py)) evaluates 90 discrete criteria:

- **AC-01 to AC-10 (Harness Integrity & Invariants):**
  - AC-01: AST self-inspection (no unconditional pass placeholders, no hardcoded DB credentials).
  - AC-02: Evaluator self-test returns 0 on pass, 1 on failure.
  - AC-03 & AC-06: Frozen immutable Pydantic models (`AttackCase`, `AttackResult`).
  - AC-04 & AC-10: Input manifest and evidence canonical SHA-256 hash stability.
  - AC-05: Attack suite version constant frozen (`1.0.0`) and matching Git revision.
  - AC-07: Sanitized evidence builder redacts sensitive fields.
  - AC-08 & AC-09: Generator produces deterministic case counts across all 10 scenario categories.
- **AC-11 to AC-20 (Scenario 1 — Policy Bypass Resistance):** Verifies all denial reason codes, forged authorizations, and boundary violations are blocked.
- **AC-21 to AC-30 (Scenario 2 — Stale Authority Replay):** Verifies expired tokens, version mismatches, and mutated amounts are rejected.
- **AC-31 to AC-40 (Scenario 3 — Replay Storms & Idempotency):** Verifies 50 concurrent replay bursts advance case state exactly once.
- **AC-41 to AC-50 (Scenario 4 — Capture Race Conditions):** Verifies concurrent race protection and duplicate settlement prevention.
- **AC-51 to AC-60 (Scenario 5 — Illegal State Transitions):** Verifies terminal state immutability across all enum values.
- **AC-61 to AC-70 (Scenario 6 — Truth-Plane Separation):** Verifies zero latent feature leakage into runtime decisions.
- **AC-71 to AC-75 (Scenario 7 — Audit Immutability):** Verifies PostgreSQL trigger blocks direct SQL `UPDATE` and `DELETE` on audit events.
- **AC-76 to AC-80 (Scenario 8 — Benchmark Immutability):** Verifies PostgreSQL trigger blocks direct SQL mutations on evaluation reports.
- **AC-81 to AC-85 (Scenario 9 — Dashboard Abuse):** Verifies HTTP 405 on mutations and clean 404 handling on unknown runs.
- **AC-86 to AC-89 (Scenario 10 — Secret Exfiltration):** Verifies zero leakage of the 5 canonical sentinels across API endpoints, logs, and exports.
- **AC-90 (Overall Suite Integrity & Demo DB Protection):** Requires all previous 89 criteria to pass and verifies that the pre-attack and post-attack cryptographic snapshots of `apro_test_db` are identical (0 mutations).

---

## 4. Canonical Sentinels Checked

The harness tracks five specific sentinels defined in [`src/apro/adversarial/enums.py`](../src/apro/adversarial/enums.py):

```python
CANONICAL_SENTINELS = [
    "sentinel_phase17_secret_87654321",
    "sentinel_card_number_4111222233334444",
    "sentinel_auth_header_bearer_xyz999",
    "sentinel_db_password_topsecret_2026",
    "sentinel_raw_provider_payload",
]
```

In Scenario 10, these tokens are persisted into `apro_attack_db` and inspected across all 13 dashboard API endpoints, audit reconstruction records, and JSON exports. The test verifies that **zero sentinels leak unmasked**.

---

## 5. Running the Phase 17 Acceptance Suite

To execute the authoritative security suite:

```powershell
# Configure database URLs (must point to different databases)
$env:POSTGRES_TEST_URL="postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/apro_attack_db"
$env:POSTGRES_DEMO_URL="postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/apro_test_db"

# Execute runner
python scripts/run_phase_17_acceptance.py --seed 1701
```

### Self-Testing Failure Injection

The runner supports failure simulation flags to prove negative testing sensitivity:
- `--injected-failure`: Simulates an invariant failure, causing AC-90 to fail and returning exit code 1.
- `--self-test-mock-failure`: Immediately exits with code 1 for subprocess caller verification.
