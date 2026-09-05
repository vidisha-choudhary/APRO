# APRO Phase 17 — Adversarial Security & Attack Harness

**Project:** Adaptive Payment Recovery Orchestrator (APRO)
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery
**Phase:** 17 — Adversarial Security & Attack Harness
**Architecture Leads:** Vidisha + GPT
**Implementation Lead:** Antigravity
**Baseline Commit:** `9805456` — Phase 16 Live Reviewer Dashboard
**Status:** Authoritative phase specification

> **Single authoritative mandate:** “Try to break APRO’s safety boundaries before an attacker, reviewer, or judge does.”

---

## 1. Executive Summary

Phase 17 is the final engineering/security-hardening phase before Phase 18. It introduces a deterministic, local-only adversarial attack harness that deliberately attempts to violate APRO’s established authority boundaries, safety invariants, truth separation, immutability, idempotency, and observational guarantees.

The harness is an evaluation subsystem, not a new business engine. It must never become an alternative recovery orchestrator, decision engine, policy engine, provider transport, or benchmark engine.

Every attack must have an explicit expected security property, an observable failure condition, and reproducible evidence. A passing Phase 17 result means an attempted attack was either rejected, neutralized, contained, or correctly surfaced without producing an unsafe or false business result.

### Phase boundaries

| Phase | Authority | Phase 17 relationship |
|---|---|---|
| Phase 9 | Action selection | Attack it; never replace it |
| Phase 10 | Policy / safety | Attack it; never replace it |
| Phase 11 | Execution / preconditions | Attack preconditions and replay paths |
| Phase 12 | Provider normalization / transport | Use only simulation/test doubles |
| Phase 13 | Outcome / adaptive loop | Attack stale/replay/race behavior |
| Phase 14 | Audit / reconstruction | Attack truth completeness and leakage |
| Phase 15 | Evaluation / statistics | Attack truth-plane isolation and report integrity |
| Phase 16 | Dashboard / reviewer UI | Attack API boundary, leakage, and tampering surfaces |
| Phase 17 | Adversarial harness | Attack-only; no new business authority |
| Phase 18 | Demo / submission | Not implemented here |

---

## 2. Scope & Non-Negotiable Guardrails

### 2.1 In scope

- Deterministic adversarial test generation for APRO inputs, state transitions, correlation context, audit records, benchmark artifacts, and dashboard/API requests.
- Replay, duplication, stale-state, concurrent-race, mutation, truth-leakage, and authorization-boundary attacks.
- Negative testing of refusal, blocking, escalation, containment, and error semantics.
- Security evidence capture with exact attack ID, seed, target component, expected property, observed result, and artifact hashes.
- Isolated PostgreSQL acceptance database and isolated provider simulator/test doubles only.
- AST/source-boundary inspection of the attack harness itself so the harness cannot introduce business authority or hidden network behavior.

### 2.2 Explicitly out of scope

- No live Razorpay API requests, real payment operations, real-money movement, or external provider calls.
- No penetration testing against GitHub, Razorpay, OpenAI, or any third-party service.
- No exploit-development against unrelated software.
- No changes to Phase 9–16 business semantics merely to make an attack pass.
- No dashboard redesign, no Phase 15 metric redesign, and no Phase 18 pitch/demo production.
- No Kafka, Redis, Kubernetes, distributed tracing stack, SIEM, or new infrastructure.

### 2.3 Test isolation

Use a dedicated PostgreSQL database for Phase 17 acceptance:

```text
POSTGRES_TEST_URL=postgresql+asyncpg://<explicit local test credentials>@127.0.0.1:5432/apro_attack_db
```

Credentials must come from the environment. No database credential, provider key, authorization header, or real secret may be embedded in source.

---

## 3. Attack Harness Architecture

```text
Canonical APRO Runtime
        |
        +--> Phase 9 Decision Authority
        +--> Phase 10 Policy Authority
        +--> Phase 11 Execution Authority
        +--> Phase 12 Provider Simulator Boundary
        +--> Phase 13 Outcome / Loop Authority
        +--> Phase 14 Audit / Reconstruction
        +--> Phase 15 Evaluation Truth
        +--> Phase 16 Dashboard API
                       ^
                       |
            Phase 17 Attack Harness
            -----------------------
            Generates attacks
            Executes attacks
            Observes outcomes
            Compares with expected invariants
            Persists evidence
            NEVER selects actions for APRO
```

### 3.1 Proposed package

```text
src/apro/adversarial/
├── __init__.py
├── enums.py
├── models.py
├── generators.py
├── scenarios.py
├── executor.py
├── assertions.py
├── evidence.py
└── replay.py
```

| Path | Responsibility |
|---|---|
| `src/apro/adversarial/__init__.py` | Public exports |
| `src/apro/adversarial/enums.py` | AttackCategory, AttackDisposition, Severity, attack IDs |
| `src/apro/adversarial/models.py` | Immutable AttackCase, AttackResult, AttackEvidence, AttackRun |
| `src/apro/adversarial/generators.py` | Deterministic adversarial input generation |
| `src/apro/adversarial/scenarios.py` | Scenario definitions and target bindings |
| `src/apro/adversarial/executor.py` | Local attack execution coordinator; no business authority |
| `src/apro/adversarial/assertions.py` | Security/safety invariant assertions |
| `src/apro/adversarial/evidence.py` | Sanitized evidence capture and run hashing |
| `src/apro/adversarial/replay.py` | Deterministic replay and attack-case reproduction |
| `scripts/run_phase_17_acceptance.py` | Authoritative 10-scenario / 90-criterion runner |
| `tests/adversarial/` | Unit, integration, concurrency, security, and boundary tests |

---

## 4. Attack Taxonomy

| Category | Examples | Required property |
|---|---|---|
| AUTH | Policy bypass, approval spoofing | Unauthorized action is never authorized |
| STALE | Old policy/decision/state replay | Stale authority cannot authorize current execution |
| REPLAY | Duplicate decision/execution/outcome delivery | No duplicate semantic advancement |
| RACE | Capture race, concurrent workers | Exactly-once / precondition guarantees hold |
| STATE | Illegal lifecycle transition | State guards reject impossible transitions |
| TRUTH | Oracle / latent-truth injection | Runtime cannot consume evaluator hidden truth |
| AUDIT | Audit deletion, mutation, missing artifact | History stays immutable/reconstructable |
| EVAL | Benchmark tampering / run confusion | Immutable benchmark provenance remains intact |
| API | Invalid IDs, unsupported methods, parameter confusion | Dashboard remains read-only and truthful |
| SECRET | Credential/sentinel injection | Secrets/PII never leak |
| BOUNDARY | Import/runtime authority probes | Phase 17 introduces no business authority |

---

## 5. Ten Authoritative Adversarial Scenarios

### Scenario 1 — Policy Bypass Attack

**Attack:** Attempt to execute a blocked/high-risk action by manipulating action, approval, reason-code, or policy context.

**Required security property:** Execution remains blocked/contained; no unauthorized provider side effect; authoritative policy evidence remains intact.

### Scenario 2 — Stale Decision / Stale Policy Replay

**Attack:** Replay an older decision or policy artifact against a changed case state or changed cycle.

**Required security property:** Stale authority is rejected; current state/policy remains authoritative; no unsafe execution.

### Scenario 3 — Duplicate / Replay Storm

**Attack:** Deliver duplicate decision, policy, execution, and outcome messages repeatedly and concurrently.

**Required security property:** Exactly one semantic advancement per authoritative artifact; no duplicate execution/outcome side effects.

### Scenario 4 — Capture-Race / Concurrent State Attack

**Attack:** Race payment capture/terminal state against an execution attempt and concurrent workers.

**Required security property:** Authoritative precondition wins deterministically; unsafe execution is rejected; no unauthorized money movement or contradictory final state.

### Scenario 5 — Illegal State Transition Attack

**Attack:** Attempt impossible transitions such as terminal `RECOVERED` followed by new execution, `STOPPED` followed by new execution, or unauthorized automated recovery after escalation.

**Required security property:** Explicit state rejection; prior facts remain unchanged; terminal state remains authoritative.

### Scenario 6 — Oracle / Truth-Plane Leakage Attack

**Attack:** Inject `oracle_action`, `potential_outcomes`, hidden recoverability, latent truth, or simulator oracle fields into runtime artifacts.

**Required security property:** Runtime authorities cannot consume hidden evaluator truth; no oracle-derived action selection; no hidden truth in exposed evidence.

### Scenario 7 — Audit Tampering / Reconstruction Attack

**Attack:** Attempt direct SQL `UPDATE`/`DELETE`, ORM mutation, conflicting duplicate event insertion, and removal of mandatory lifecycle artifacts.

**Required security property:** Append-only protection blocks mutation; reconstruction reports `INCOMPLETE`/`CORRUPT` when appropriate; never false `COMPLETE`.

### Scenario 8 — Benchmark / Reproducibility Tampering

**Attack:** Attempt to overwrite an immutable benchmark run, change hashes/configuration, or confuse Run A with Run B.

**Required security property:** Immutable run remains unchanged; conflicting persistence is rejected; hashes remain stable; run selection remains coherent.

Also verify direct SQL `UPDATE`/`DELETE` against `evaluation_benchmark_reports`.

### Scenario 9 — Dashboard/API Abuse

**Attack:** Attempt POST/PUT/PATCH/DELETE, malformed case IDs, unknown benchmark runs, parameter confusion, cross-run confusion, unavailable database, and unsupported paths.

**Required security property:** API remains read-only and truthful; writes are rejected; unknown data returns correct error semantics; no business state mutation.

### Scenario 10 — Secret / Evidence Exfiltration

**Attack:** Inject:

```text
sentinel_phase17_secret_87654321
sentinel_card_number_4111222233334444
sentinel_auth_header_bearer_xyz999
sentinel_db_password_topsecret_2026
sentinel_raw_provider_payload
```

through realistic supported paths and inspect logs, audit, evaluation, API, and exported evidence.

**Required security property:** Zero secret/sentinel leakage.

The sentinel-bearing artifact must actually be persisted in the isolated attack database before inspection.

---

## 6. Determinism, Seeds & Reproducibility

Every adversarial run must be reproducible from a versioned attack manifest.

Required metadata:

- `attack_run_id`
- `attack_suite_version`
- `seed`
- `scenario_ids`
- `code_revision`
- `environment`
- `input_manifest_hash`
- `evidence_hash`

Repeating the same attack run with the same seed and immutable fixtures must produce equivalent security outcomes and an identical canonical evidence hash.

---

## 7. Security Assertions & Invariants

| Invariant | Required result |
|---|---|
| No unauthorized action | Blocked/approval-required policy cannot result in authorized execution |
| No stale authority | Stale policy/decision cannot be reused after authoritative context changes |
| No duplicate semantic event | Replay cannot create duplicate logical decisions/policies/executions/outcomes |
| No duplicate side effect | Replay/race cannot cause a second provider-side effect in the harness |
| Terminal-state integrity | `RECOVERED`, `STOPPED`, `ESCALATED` cannot silently reopen |
| Audit immutability | Audit rows cannot be updated or deleted, including direct SQL |
| Audit completeness truth | Missing mandatory artifacts produce `INCOMPLETE`/`CORRUPT`, never false `COMPLETE` |
| Truth-plane separation | Oracle/latent truth never reaches runtime decision/policy/execution artifacts |
| Benchmark immutability | Existing benchmark run content cannot be overwritten |
| Run coherence | Selected benchmark run ID maps to one immutable report |
| Read-only dashboard | Adversarial HTTP mutations cannot alter business/evaluation state |
| Secret non-leakage | Sentinels do not appear in logs, audit, benchmark reports, API responses, or evidence |

---

## 8. Comprehensive Test Suite

Create:

```text
tests/adversarial/
├── test_attack_models.py
├── test_attack_generators.py
├── test_policy_bypass.py
├── test_stale_replay.py
├── test_replay_idempotency.py
├── test_concurrent_attacks.py
├── test_state_attacks.py
├── test_truth_plane_attacks.py
├── test_audit_tampering.py
├── test_evaluation_tampering.py
├── test_dashboard_attacks.py
├── test_secret_exfiltration.py
├── test_replay_reproducibility.py
└── test_attack_boundaries.py
```

Tests must use genuine runtime behavior.

No:
- unconditional PASS
- fixture-vs-fixture self-comparison as proof
- `hasattr()`-only validation
- broad exception → PASS logic

---

## 9. Authoritative Acceptance Runner

Create:

```text
scripts/run_phase_17_acceptance.py
```

Requirements:

- Exactly 10 executable adversarial scenarios.
- Exactly 90 acceptance criteria: `AC-01` through `AC-90`.
- Explicit deterministic seed support, e.g. `--seed 1701`.
- Isolated PostgreSQL acceptance database.
- No live external network/provider calls.
- Sanitized evidence only.
- Deterministic manifest + evidence hash.
- Non-zero exit on any failed criterion.

Add:

```text
--injected-failure
```

or equivalent self-test path.

The acceptance evaluator must prove:

```text
all 90 criteria true
→ exit code 0

one criterion false
→ non-zero

empty/missing mandatory criterion set
→ non-zero

injected failure
→ non-zero
```

The runner must print every AC result.

---

## 10. Acceptance Criteria Mapping

| Criteria | Verification scope |
|---|---|
| AC-01 to AC-10 | Harness integrity, immutable result models, deterministic IDs, seed/replay manifest, zero PASS placeholders |
| AC-11 to AC-20 | Policy-bypass resistance and approval-boundary enforcement |
| AC-21 to AC-30 | Stale decision/policy replay rejection and provenance preservation |
| AC-31 to AC-40 | Duplicate/replay storm idempotency and exactly-once semantic advancement |
| AC-41 to AC-50 | Concurrency/race and illegal state-transition resistance |
| AC-51 to AC-58 | Oracle/latent truth isolation and evaluator truth-plane separation |
| AC-59 to AC-66 | Audit immutability, completeness, corruption detection, reconstruction truth |
| AC-67 to AC-72 | Benchmark run immutability, report/config/snapshot hash integrity, run coherence |
| AC-73 to AC-78 | Dashboard read-only/API abuse, unknown-run handling, and database failure semantics |
| AC-79 to AC-84 | Secret/sentinel non-leakage across logs, audit, evaluation, API, and evidence |
| AC-85 to AC-88 | Cross-phase boundaries: no decision/policy/execution/provider/evaluation/dashboard authority duplication |
| AC-89 to AC-90 | Acceptance self-test, failure detection, deterministic rerun/evidence hash reproducibility |

---

## 11. Required Evidence Output

The final acceptance output should include:

```text
APRO PHASE 17 — ADVERSARIAL SECURITY & ATTACK HARNESS
==========================================================
Attack suite version: ...
Seed: ...
Scenarios: 10/10
Acceptance criteria: 90/90

Policy bypass attacks: PASS
Stale authority attacks: PASS
Replay/idempotency attacks: PASS
Concurrency/race attacks: PASS
Illegal state attacks: PASS
Oracle/truth-plane attacks: PASS
Audit tampering attacks: PASS
Benchmark tampering attacks: PASS
Dashboard/API abuse attacks: PASS
Secret exfiltration attacks: PASS

Unauthorized executions: 0
Duplicate semantic advancements: 0
Duplicate provider side effects: 0
Illegal terminal reopenings: 0
Audit mutations accepted: 0
Benchmark mutations accepted: 0
Truth-plane leaks: 0
Dashboard write operations accepted: 0
Secret/sentinel leaks: 0

Reproducibility:
same seed -> identical evidence hash: PASS

Failure self-test:
all-pass -> exit 0: PASS
false criterion -> non-zero: PASS
empty criteria -> non-zero: PASS
injected failure -> non-zero: PASS

Full regression: PASS
Ruff: PASS
Format: PASS
Mypy: PASS

Git commits: 0
Git pushes: 0
```

---

## 12. Verification Commands

Acceptance/testing MUST use an isolated local PostgreSQL database:

```powershell
# 1. Isolated database
$env:POSTGRES_TEST_URL="postgresql+asyncpg://<explicit-test-credentials>@127.0.0.1:5432/apro_attack_db"
python -m alembic upgrade head

# 2. Adversarial unit/integration suite
pytest tests/adversarial/ -v

# 3. Cross-phase regression
pytest tests/audit/ tests/evaluation/ tests/dashboard/ tests/policy/ tests/execution/ tests/providers/ tests/recovery_loop/ -v

# 4. Full repository regression
pytest tests/ -q

# 5. Quality
ruff check .
ruff format --check .
mypy src

# 6. Authoritative attack runner
python scripts/run_phase_17_acceptance.py --seed 1701
```

---

## 13. Completion / Sign-Off Conditions

Phase 17 is complete only when:

- All 10 adversarial scenarios execute against the isolated acceptance environment.
- All 90 acceptance criteria pass from genuine executable evidence.
- The failure-detection self-test proves the runner cannot silently pass a failed criterion.
- The attack suite is deterministic under a fixed seed and immutable fixture set.
- No live external provider calls occur.
- No Phase 0–16 business semantics are changed to accommodate an attack.
- No security or audit bypass is accepted as a fixture shortcut.
- No new business authority exists in `src/apro/adversarial/`.
- No secrets or raw credentials appear in attack inputs, logs, reports, evidence, or committed files.
- Full repository regression remains green.
- The judge/demo database is never reused as the attack acceptance database.
- Git remains untouched by the implementation agent: 0 commits and 0 pushes.

---

## 14. Expected Operational Model

```text
Developer / CI
   |
   +--> apro_attack_db
           |
           +--> seed deterministic attack fixtures
           +--> execute adversarial scenarios
           +--> capture sanitized evidence
           +--> compute evidence hash
           +--> destroy/reinitialize acceptance state as required

Judge / Demo
   |
   +--> apro_test_db
           |
           +--> clean benchmark runs
           +--> complete cases/audit trails
           +--> Phase 16 reviewer dashboard

These environments MUST remain separate.
```

Phase 17 must never contaminate the judge/demo database with attack fixtures, sentinels, mutated benchmark runs, or deliberately corrupt audit records.

---

## 15. Explicit Phase 18 Boundary

Phase 18 will handle final demo orchestration, pitch/storyline, submission assets, and presentation polish.

Phase 17 must produce the security evidence that Phase 18 can truthfully present, but it must not contain the pitch, final video, submission copy, or judge-facing presentation workflow.

---

## 16. Authoritative Final Invariants

**Phase 17 is an attack harness, not a second APRO.**

The canonical authority remains:

- Phase 9 selects the action.
- Phase 10 authorizes or blocks it.
- Phase 11 controls execution and preconditions.
- Phase 12 normalizes/simulates provider transport.
- Phase 13 classifies outcomes and governs adaptive recovery.
- Phase 14 records/reconstructs what happened.
- Phase 15 evaluates persisted truth.
- Phase 16 presents persisted truth.
- Phase 17 attacks those boundaries and proves they hold.
- Phase 18 presents the finished system.
