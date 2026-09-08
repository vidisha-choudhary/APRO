# APRO — Technical Architecture Guide

This document provides a comprehensive technical overview of APRO's architecture from Phase 09 through Phase 17, detailing module responsibilities, authority boundaries, data flows, and safety mechanisms.

---

## 1. Architectural Philosophy

APRO models payment recovery as an **adaptive decision problem under uncertainty and policy constraints**, rather than a static retry mechanism.

Key architectural pillars:
1. **Separation of Economic Optimization from Safety Authorization:** The economic decision engine maximizes expected net recovery value; the policy engine independently verifies that candidates adhere to compliance, risk, and cooling-off constraints.
2. **Deterministic State Machine Enforcement:** Cases transition through explicit, unidirectional lifecycle states. Terminal states (`CLOSED_RECOVERED`, `CLOSED_UNRECOVERED`) are immutable.
3. **Immutable Causal Audit Trail:** All state transitions and decisions generate append-only audit events protected at the database level by PostgreSQL triggers.
4. **Persisted Benchmark Truth:** Evaluation reports are cryptographically hashed and persisted in PostgreSQL, preventing counterfactual distortion and ensuring that observability dashboards read genuine data.
5. **Defense-in-Depth Adversarial Hardening:** Authority boundaries, idempotency, and secret redaction are continuously validated via automated attack suites.

---

## 2. End-to-End Pipeline & Authority Ownership

The following diagram illustrates the unidirectional authority pipeline:

```text
[ Incoming Webhook / Ingestion ]
               │
               ▼
┌─────────────────────────────────┐
│ 1. Canonical Event Pipeline     │ (Phase 03) Normalizes payloads into CanonicalPaymentFailureEvent
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. Failure Diagnosis Engine     │ (Phase 07) Maps raw errors to semantic FailureArchetype & Telemetry
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 3. Recovery Prediction Engine   │ (Phase 08) Generates calibrated probability estimates (p_hat)
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 4. Economic Decision Engine     │ (Phase 09) Ranks actions by Expected Net Recovery Value (ENRV)
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 5. Policy & Safety Engine       │ (Phase 10) AUTHORIZATION GATE: Validates risk, cooling, limits
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 6. Execution Framework          │ (Phase 11) Dispatches approved actions with transactional idempotency
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 7. Provider Transport Layer     │ (Phase 12) Executes via Razorpay Test Mode or local simulation
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 8. Outcome Processing           │ (Phase 13) Classifies provider responses into terminal/retryable
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 9. Adaptive Recovery Loop       │ (Phase 13) Evaluates causal feedback; iterates or halts case
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 10. Audit & Reconstruction      │ (Phase 14) Appends immutable causal events; reconstructs Q1-Q7
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 11. Evaluation & Benchmarking   │ (Phase 15) Measures uplift, cost efficiency, and ECE vs baselines
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 12. Reviewer Dashboard          │ (Phase 16) Serves read-only truth via FastAPI + React/Vite
└─────────────────────────────────┘
```

---

## 3. Component Deep Dive (Phases 09–17)

### Phase 09: Economic Decision Engine
* **Location:** [`src/apro/decision/`](../src/apro/decision)
* **Authoritative Spec:** [`docs/PHASE_09_ECONOMIC_DECISION_ENGINE_SPECIFICATION.md`](PHASE_09_ECONOMIC_DECISION_ENGINE_SPECIFICATION.md)
* **Responsibility:** Evaluates candidate recovery actions (e.g., `RETRY_IMMEDIATE`, `RETRY_SCHEDULED`, `PAYMENT_LINK`, `CUSTOMER_PROMPT`, `ROUTE_ALTERNATIVE`) and selects the optimal action maximizing Expected Net Recovery Value (ENRV):
  $$\text{ENRV} = \hat{p} \cdot \text{Amount} - \text{Intervention Cost} - \text{Customer Goodwill Cost}$$
* **Boundary Invariant:** The decision engine **recommends** actions based purely on economic calculation; it **cannot** authorize execution or bypass policy.

### Phase 10: Policy & Safety Engine
* **Location:** [`src/apro/policy/`](../src/apro/policy)
* **Authoritative Spec:** [`docs/PHASE_10_POLICY_AND_SAFETY_ENGINE_SPECIFICATION.md`](PHASE_10_POLICY_AND_SAFETY_ENGINE_SPECIFICATION.md)
* **Responsibility:** Evaluates recommended actions against compliance rules, card scheme retry caps, cooling periods, and fraud signals. Produces an immutable `PolicyDecision` with `PolicyOutcome` (`ALLOW`, `DENY`, `ESCALATE`).
* **Boundary Invariant:** Policy decisions are cryptographically signed and version-bound. Execution cannot proceed without an `ALLOW` outcome.

### Phase 11: Execution Framework
* **Location:** [`src/apro/execution/`](../src/apro/execution)
* **Authoritative Spec:** [`docs/PHASE_11_EXECUTION_FRAMEWORK_SPECIFICATION.md`](PHASE_11_EXECUTION_FRAMEWORK_SPECIFICATION.md)
* **Responsibility:** Dispatches authorized recovery requests via an extensible `ExecutorRegistry`. Enforces transactional idempotency keys, execution circuit breakers, and state pre-conditions.
* **Boundary Invariant:** Reject duplicate execution requests atomically. Never dispatch without validating the `ApprovedExecutionRequest` schema.

### Phase 12: Provider Transport (Razorpay Test Mode)
* **Location:** [`src/apro/providers/`](../src/apro/providers)
* **Authoritative Spec:** [`docs/PHASE_12_RAZORPAY_TEST_MODE_PROVIDER_INTEGRATION_SPECIFICATION.md`](PHASE_12_RAZORPAY_TEST_MODE_PROVIDER_INTEGRATION_SPECIFICATION.md)
* **Responsibility:** Normalizes requests into provider formats (e.g. Razorpay Payment Links, Orders, Invoices). Restricts operations strictly to Test Mode (`rzp_test_...`).
* **Boundary Invariant:** Production keys (`rzp_live_...`) are rejected by configuration guards with `ProviderCredentialError`. No real financial movement occurs.

### Phase 13: Outcome & Adaptive Recovery Loop
* **Location:** [`src/apro/recovery_loop/`](../src/apro/recovery_loop)
* **Authoritative Spec:** [`docs/PHASE_13_OUTCOME_AND_ADAPTIVE_RECOVERY_LOOP_SPECIFICATION.md`](PHASE_13_OUTCOME_AND_ADAPTIVE_RECOVERY_LOOP_SPECIFICATION.md)
* **Responsibility:** Ingests execution results, records causal evidence, and governs the multi-cycle retry loop. Dynamically updates strategy based on observed outcomes or halts when stopping rules trigger.
* **Boundary Invariant:** Terminal states are permanent. Max retry count and timeout boundaries cannot be exceeded.

### Phase 14: Audit & Observability
* **Location:** [`src/apro/audit/`](../src/apro/audit)
* **Authoritative Spec:** [`docs/APRO_PHASE_14_SPECIFICATION.md`](APRO_PHASE_14_SPECIFICATION.md)
* **Responsibility:** Maintains an append-only sequence of `AuditEvent` records. Reconstructs complete case histories to answer the Seven Authoritative Reviewer Questions (Q1–Q7).
* **Boundary Invariant:** Audit logs cannot be modified or deleted. Protected by database-level PostgreSQL triggers.

### Phase 15: Benchmarking & Statistical Reporting
* **Location:** [`src/apro/evaluation/`](../src/apro/evaluation)
* **Authoritative Spec:** [`docs/PHASE_15_BENCHMARKING_KPI_STATISTICAL_REPORTING_SPECIFICATION.md`](PHASE_15_BENCHMARKING_KPI_STATISTICAL_REPORTING_SPECIFICATION.md)
* **Responsibility:** Evaluates recovery policies against standard baselines (Zero-Action, Blind Retry, Heuristic). Computes primary KPIs, bootstrap confidence intervals, p-values, and calibration curves.
* **Boundary Invariant:** Evaluation results are persisted immutably in PostgreSQL with SHA-256 report hashing.

### Phase 16: Live Reviewer Dashboard
* **Location:** Backend: [`src/apro/dashboard/`](../src/apro/dashboard), Frontend: [`frontend/`](../frontend)
* **Authoritative Spec:** [`docs/PHASE_16_LIVE_DASHBOARD_REVIEWER_UI_SPECIFICATION.md`](PHASE_16_LIVE_DASHBOARD_REVIEWER_UI_SPECIFICATION.md)
* **Responsibility:** Provides 8 dynamic reviewer views querying PostgreSQL truth. Features dynamic benchmark run selection, auto-refresh, and deep-linked case audits.
* **Boundary Invariant:** Zero static business metrics, zero mock datasets in production code, zero fabricated fallbacks. All endpoints are read-only.

### Phase 17: Adversarial Security Attack Harness
* **Location:** [`src/apro/adversarial/`](../src/apro/adversarial)
* **Authoritative Spec:** [`docs/APRO_PHASE_17_ADVERSARIAL_SECURITY_ATTACK_HARNESS_SPECIFICATION.md`](APRO_PHASE_17_ADVERSARIAL_SECURITY_ATTACK_HARNESS_SPECIFICATION.md)
* **Responsibility:** Automated security suite executing 10 attack scenarios (90 criteria) against system boundaries, replay storms, and trigger immutability.
* **Boundary Invariant:** Never mutates or contaminates the demo database (`apro_test_db`).

---

## 4. Database Topology & Truth Plane

APRO uses three distinct database environments to guarantee isolation:

```text
┌─────────────────────────────────┐
│          Developer / CI         │
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│         apro_attack_db          │
│ • Adversarial attack fixtures   │
│ • Sentinel injection tests      │
│ • Replay storms & stress tests  │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│          Judge / Demo           │
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│          apro_test_db           │
│ • Verified benchmark runs       │
│ • Production case audit trails  │
│ • Live Reviewer Dashboard       │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│      Clean-Room Acceptance      │
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   apro_phase18_acceptance_db    │
│ • Cold-start migration tests    │
│ • End-to-end acceptance runner  │
└─────────────────────────────────┘
```

---

## 5. Security & Invariant Enforcement

| Security Area | Mechanism | Invariant Guaranteed |
|---|---|---|
| **Audit Immutability** | PostgreSQL trigger `prevent_audit_events_mutation` | `UPDATE` and `DELETE` queries on `audit_events` raise an SQL exception. |
| **Benchmark Immutability** | PostgreSQL trigger `prevent_benchmark_reports_mutation` | Overwriting or altering persisted `evaluation_reports` is blocked. |
| **Idempotency** | Transactional unique constraints & lock coordination | Duplicate execution requests yield identical results with zero secondary effects. |
| **Stale Authority** | Case versioning and authorization window tokens | Decisions invalidated by intervening state changes are rejected. |
| **Secret Sanitization** | Boundary sanitizers & token masking | Sentinels and provider secrets never appear in logs, audit records, or UI responses. |
| **Read-Only API** | HTTP method gating on `/api/dashboard/*` | All mutations (`POST`, `PUT`, `PATCH`, `DELETE`) return HTTP 405 Method Not Allowed. |

---

## 6. Summary

APRO's architecture ensures complete technical credibility: every decision is economically driven, policy-governed, safely executed, causally auditable, statistically evaluated, and adversarially verified.
