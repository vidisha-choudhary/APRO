# APRO — Adaptive Payment Recovery Orchestrator

APRO (Adaptive Payment Recovery Orchestrator) is an intelligent, policy-guarded payment recovery orchestration platform. Rather than treating failed transactions as candidates for blind, static retries, APRO models recovery as an adaptive decision problem. It diagnoses failure root causes, predicts probabilistic recovery outcomes, optimizes net economic recovery value against provider costs and customer goodwill, enforces strict compliance and risk policies, executes bounded interventions, and continuously adapts subsequent recovery strategies based on causal execution feedback.

---

## What APRO Solves

In payment systems, transaction failures occur for diverse and evolving reasons:
- **Technical & Transient:** Gateway timeouts, upstream network partitions, provider degradations, switch timeouts.
- **Customer & Actionable:** Insufficient funds, incorrect CVV, expired card credentials, daily transaction limit exceeded.
- **Terminal & Compliance:** Fraud blocks, stolen or lost cards, invalid merchant routing, regulatory embargoes.

Conventional payment infrastructure addresses failures using primitive retry strategies—such as static exponential backoff or immediate repeated attempts. This approach causes significant operational issues:
1. **Unnecessary Operational Costs:** Repeated provider dispatches incur gateway fees, webhook delivery charges, and API throttling.
2. **Customer Friction & Fatigue:** Blasting cardholders with redundant SMS or payment prompts damages merchant brand perception and churns users.
3. **Regulatory & Risk Exposure:** Retrying cards flagged for suspected fraud or exceeding scheme retry limits risks card network fines, elevated chargeback ratios, and processor termination.
4. **Sub-optimal Recovery Timing:** Attempting recovery immediately on a Friday balance shortfall will fail, whereas waiting for scheduled payroll deposits or selecting a payment link alternative can recover revenue.

APRO solves this by decoupling diagnosis, economic optimization, and policy authorization from execution, ensuring every recovery action is economically justified, policy-authorized, safely dispatched, and causally audited.

---

## How APRO Works

APRO operates as an eleven-stage unidirectional authority pipeline where each component has strict, non-overlapping authority boundaries:

```text
[ Incoming Failure Webhook ]
             │
             ▼
┌───────────────────────────┐
│ 1. Failure Diagnosis      │ ──> Categorizes error codes into semantic archetypes
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 2. Outcome Prediction     │ ──> Computes calibrated success probabilities per action
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 3. Economic Decision      │ ──> Evaluates Net Recovery Value (Expected Value − Cost)
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 4. Policy & Safety Engine │ ──> AUTHORIZATION GATE: Enforces cooling periods, risk rules
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 5. Bounded Execution      │ ──> Dispatches approved requests with idempotency protection
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 6. Outcome Processing     │ ──> Ingests provider responses, classifies final states
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 7. Adaptive Recovery Loop │ ──> Ingests new evidence; re-evaluates next strategy or stops
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 8. Audit & Observability  │ ──> Reconstructs immutable causal timeline (Q1–Q7 questions)
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 9. Evaluation Engine      │ ──> Benchmarks counterfactual lift with statistical uncertainty
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 10. Live Reviewer UI      │ ──> Read-only dashboard querying PostgreSQL truth
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 11. Adversarial Security  │ ──> Proves system invariants under injection & replay attacks
└───────────────────────────┘
```

### Authority Ownership Matrix

| Pipeline Component | Authority Owned | Authority Strictly Forbidden |
|---|---|---|
| **Diagnosis** | Semantic categorization of raw error codes and failure telemetry. | Selecting recovery actions or executing calls. |
| **Recovery Prediction** | Computing calibrated probabilistic outcome distributions ($\hat{p}$). | Making financial choices or approving retries. |
| **Economic Decision** | Ranking candidate actions by Expected Net Recovery Value (ENRV). | Authorizing execution or bypassing policy limits. |
| **Policy & Safety** | Authorizing, vetoing, or requiring escalation for candidate actions. | Executing actions or inventing economic options. |
| **Execution Framework** | Idempotently executing authorized requests with circuit breakers. | Modifying policy constraints or initiating unapproved calls. |
| **Provider Transport** | Normalizing provider-specific payloads (e.g., Razorpay Test Mode). | Business authority or financial decision-making. |
| **Adaptive Recovery** | Governing multi-cycle case re-evaluation and stopping rules. | Reopening closed cases or exceeding max retry boundaries. |
| **Audit & Provenance** | Immutable append-only logging of causal lifecycle events. | Updating or deleting historical audit records. |
| **Evaluation Engine** | Statistical benchmarking against zero-action and heuristic baselines. | Modifying runtime operational state. |
| **Dashboard** | Read-only presentation of persisted PostgreSQL truth. | Writing business state, mocking data, or mutating runs. |
| **Adversarial Harness**| Stress testing invariants, boundaries, and immutability triggers. | Contaminating the judge/demo database. |

---

## Architecture

```text
                                 +---------------------------------------+
                                 |         External Payment Events       |
                                 |       (Webhooks / Failure Ingestion)  |
                                 +---------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                              APRO CORE                                                  |
|                                                                                                         |
|  ┌─────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐                  |
|  │  Failure Diagnosis  │ ────> │  Outcome Prediction  │ ────> │   Economic Decision  │                  |
|  │  (archetypes/tele)  │       │  (probabilistic ML)  │       │   (net recovery val) │                  |
|  └─────────────────────┘       └──────────────────────┘       └──────────────────────┘                  |
|                                                                          │                              |
|                                                                          ▼                              |
|  ┌─────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐                  |
|  │ Provider Transport  │ <──── │ Bounded Execution    │ <──── │   Policy & Safety    │                  |
|  │ (Razorpay/Simulated)│       │ (idempotent registry)│       │   (authorization)    │                  |
|  └─────────────────────┘       └──────────────────────┘       └──────────────────────┘                  |
|             │                                                                                           |
|             ▼                                                                                           |
|  ┌─────────────────────┐       ┌──────────────────────┐                                                 |
|  │ Outcome Classifier  │ ────> │ Adaptive Loop Engine │                                                 |
|  │ (recovered/failed)  │       │ (cycle re-eval/stop) │                                                 |
|  └─────────────────────┘       └──────────────────────┘                                                 |
|                                            │                                                            |
+--------------------------------------------┼------------------------------------------------------------+
                                             │
                                             ▼
+---------------------------------------------------------------------------------------------------------+
|                                    PERSISTENCE & AUDIT TRUTH                                            |
|                                                                                                         |
|  ┌─────────────────────────────────┐   ┌────────────────────────────────┐   ┌────────────────────────┐  |
|  │ PostgreSQL Truth Store          │   │ Immutable Audit Log            │   │ Evaluation Reports     │  |
|  │ (recovery_cases, payments, uow) │   │ (audit_events with PG trigger) │   │ (SHA-256 hash manifest)│  |
|  └─────────────────────────────────┘   └────────────────────────────────┘   └────────────────────────┘  |
+---------------------------------------------------------------------------------------------------------+
                                             │
                                             ▼
+---------------------------------------------------------------------------------------------------------+
|                                     OBSERVABILITY & VERIFICATION                                        |
|                                                                                                         |
|  ┌─────────────────────────────────────────────────────────┐  ┌──────────────────────────────────────┐  |
|  │ Reviewer Dashboard (FastAPI + React/Vite)               │  │ Adversarial Attack Harness (Phase 17)│  |
|  │ • 13 REST Endpoints (/api/dashboard/*)                  │  │ • 10 Attack Scenarios (AC-01..AC-90)  │  |
|  │ • 8 Dynamic Views: KPIs, Funnel, Safety, Provenance     │  │ • Trigger tampering & replay tests   │  |
|  └─────────────────────────────────────────────────────────┘  └──────────────────────────────────────┘  |
+---------------------------------------------------------------------------------------------------------+
```

For detailed component documentation, consult:
- [Domain Model & Data Architecture](docs/DOMAIN_AND_DATA_MODEL.md)
- [Technical Architecture Specification](docs/TECHNICAL_ARCHITECTURE.md)
- [Detailed Architecture Guide](docs/ARCHITECTURE.md)

---

## Why The Architecture Is Safe

APRO was engineered with defense-in-depth principles, enforcing invariants in code and at the database schema level:

1. **Policy Separation:** No execution request can dispatch without an explicit cryptographic policy authorization artifact (`PolicyOutcome.ALLOW`). Economic optimizers cannot bypass policy constraints.
2. **Terminal State Integrity:** State machines enforce that once a case reaches a terminal status (`CLOSED_RECOVERED`, `CLOSED_UNRECOVERED`), it cannot be reopened, mutated, or re-executed.
3. **Idempotency & Concurrency Guards:** Replay storms and concurrent duplicate webhooks are handled by transactional idempotency keys and database-level unique constraints. Duplicate requests yield the existing execution result without second provider side-effects.
4. **Stale Authority Rejection:** Authorizations are cryptographically bound to specific case versions and expiration windows. If case state evolves between authorization and execution, the stale token is rejected.
5. **Database-Enforced Audit Immutability:** PostgreSQL triggers (`prevent_audit_events_mutation`) reject any SQL `UPDATE` or `DELETE` on the `audit_events` table, preventing audit log tampering.
6. **Benchmark Report Immutability:** Persisted evaluation reports in the database are protected by PostgreSQL triggers (`prevent_benchmark_reports_mutation`), ensuring historical evaluation runs cannot be modified.
7. **Truth-Plane Separation:** Ground truth (latent customer payment intentions and synthetic oracle attributes) is strictly partitioned from runtime modules; runtime decisions only observe observable case history and production telemetry.
8. **Dashboard Read-Only Isolation:** The reviewer UI interacts exclusively through read-only GET endpoints (`/api/dashboard/*`). State mutations via HTTP POST/PUT/PATCH/DELETE are rejected with HTTP 405.
9. **Secret Non-Leakage:** Sensitive payment data (PANs, CVVs, provider API secrets, internal tokens) is redacted at the ingress boundary and masked across all audit records, dashboard responses, and exports.

---

## Adaptive Recovery

Adaptive recovery in APRO operates as a closed-loop control system:

$$\text{Failure Ingestion} \longrightarrow \text{Intervention} \longrightarrow \text{Outcome Observation} \longrightarrow \text{Evidence Assimilation} \longrightarrow \text{Strategy Revision}$$

### How Adaptation Differs from Static Retries

1. **Information Assimilation:** When an initial attempt fails, APRO captures granular outcome evidence (e.g., error code shifted from "insufficient funds" to "gateway timeout", or customer opened a payment link).
2. **Dynamic Strategy Selection:** If a customer repeatedly ignores WhatsApp recovery messages, APRO shifts strategy (e.g., automated mandate retry or card re-auth) or safely stops to prevent customer irritation.
3. **Policy-Bounded Iteration:** Every iteration loop is governed by strict global guardrails:
   - Maximum allowable retry count (e.g., 3 cycles).
   - Maximum elapsed recovery window (e.g., 72 hours).
   - Cooling-off periods between identical interventions.
   - Cumulative cost bounds ensuring recovery expense never exceeds transaction margin.
4. **Deterministic Stopping Conditions:** When policy boundaries are breached, or Expected Net Recovery Value turns negative, APRO transitions the case to `CLOSED_UNRECOVERED` or escalates to manual merchant review.

---

## Evaluation

APRO includes a comprehensive benchmarking engine ([`src/apro/evaluation/`](src/apro/evaluation)) that evaluates recovery strategies against standard industry baselines on deterministic datasets:

- **Baseline Comparison Models:**
  - *Zero Action Baseline:* Evaluates organic customer-driven recovery without merchant intervention.
  - *Blind Retry Baseline:* Simulates indiscriminate retry on all failures.
  - *Immediate Retry Baseline:* Evaluates instant single-retry performance.
  - *Rule-Based Heuristic:* Simulates hardcoded error-code lookup tables.
- **Evaluated Metrics:**
  - Net Revenue Recovered ($\text{Recovered Amount} - \text{Intervention Costs}$).
  - Recovery Uplift over baselines with 95% bootstrap confidence intervals and p-values.
  - Cost Efficiency Ratio and Average Cost per Recovered Case.
  - Model Calibration: Brier Score, Expected Calibration Error (ECE), ROC-AUC, PR-AUC.
  - Safety Violations (unsafe dispatches, policy bypasses, duplicate executions).
- **Authoritative Persisted Truth:**
  - Benchmark results are stored in PostgreSQL (`evaluation_reports` table) along with full configuration snapshots, dataset SHA-256 digests, and cryptographic report hashes.
  - The Live Dashboard reads directly from this persisted truth; benchmark metrics in APRO are never fabricated, mocked, or hardcoded.
  - See [Benchmark Results Documentation](docs/BENCHMARK_RESULTS.md) for benchmark schema and methodology.

---

## Live Reviewer Dashboard

Phase 16 provides an interactive, production-grade reviewer interface backed by FastAPI and React/Vite.

### Reviewer Views

- **`/dashboard` (Overview):** Real-time recovery KPIs (Recovery Rate, Net Revenue Recovered, Cost Efficiency, System Health) and full-funnel conversion analysis.
- **`/dashboard/benchmarks` (Benchmarks):** Statistical comparisons against baselines with 95% confidence intervals and p-values.
- **`/dashboard/cases` (Case Explorer):** Paginated search, status filtering, and causal inspection of recovery cases.
- **`/dashboard/cases/:caseId` (Case Detail):** Deep-linked case audit provenance, chronological event timeline, and answers to the **Seven Authoritative Reviewer Questions (Q1–Q7)**:
  1. *Why did this payment fail?*
  2. *What recovery action was chosen and why?*
  3. *What was the predicted success probability?*
  4. *What was the expected net economic value?*
  5. *Did policy and safety authorize the action?*
  6. *What was the outcome of the intervention?*
  7. *What was the subsequent adaptive response?*
- **`/dashboard/safety` (Safety Invariants):** Live evaluation of system safety guarantees and violation counters.
- **`/dashboard/predictions` (Prediction Quality):** Reliability diagrams, ECE curves, and discrimination metrics.
- **`/dashboard/adaptive` (Adaptive Recovery):** Multi-cycle progression, cycle attempt distributions, and re-evaluation lift.
- **`/dashboard/cohorts` (Cohort Analysis):** Disaggregated segment performance across card networks, banks, failure archetypes, and ticket sizes.
- **`/dashboard/reproducibility` (Provenance):** Full cryptographic run manifest, dataset SHA-256 hashes, git commit hash, seeds, and environment metadata.

### UI Integrity Guarantees

- **No Static Business Metrics:** All cards, charts, and tables are populated by live API queries against PostgreSQL.
- **No Production Mock Datasets:** If the database contains no benchmark runs or cases, the UI displays clean empty-state components rather than falling back to dummy figures.
- **Auto-Refresh & Run Selector:** Context-wide 10-second polling interval with live badge control and a dynamic benchmark run dropdown selector.

---

## Security & Adversarial Verification

Phase 17 implements an authoritative adversarial security attack harness ([`src/apro/adversarial/`](src/apro/adversarial)) executing 10 attack scenarios across 90 automated acceptance criteria (AC-01 through AC-90):

1. **Policy Bypass Attacks:** Injecting execution attempts with rejected, unapproved, or forged policy decisions.
2. **Stale Authority Replay:** Replaying expired policy tokens across state transitions and modified cases.
3. **Duplicate Replay Storms:** Flooding concurrent identical webhooks and execution requests.
4. **Capture Race Conditions:** Triggering rapid concurrent authorization and capture events.
5. **Illegal State Transitions:** Attempting to force transitions from terminal states back into active recovery.
6. **Truth-Plane Isolation:** Attempting to leak counterfactual or oracle dataset attributes into runtime pipelines.
7. **Audit Tampering:** Direct SQL injection executing `UPDATE` or `DELETE` queries on `audit_events`.
8. **Benchmark Tampering:** Attempting to overwrite existing evaluation records or alter historical reports.
9. **Dashboard Abuse:** Submitting HTTP mutations (`POST`, `PUT`, `DELETE`, `PATCH`) and malformed payloads to read-only endpoints.
10. **Secret Exfiltration:** Persisting canonical sentinels (`sentinel_phase17_secret_...`) to verify total redaction across logs, audit records, API endpoints, and export manifests.

### Dual-Database Topology & Protection

The test suite enforces complete separation between testing environments:
- `apro_attack_db`: Dedicated scratch database for destructive attack scenarios.
- `apro_test_db`: Judge / Demo database. The runner takes a cryptographic table-by-table snapshot before attack execution and verifies post-attack that `apro_test_db` suffered **zero mutations**.

See [Security & Adversarial Results](docs/SECURITY_RESULTS.md) for detailed scenario breakdowns.

---

## Repository Structure

```text
APRO/
├── src/apro/                    # Core Python application package
│   ├── domain/                  # Core domain models, state machines, and enums
│   ├── persistence/             # SQLAlchemy async engine, Unit of Work, schema models
│   ├── events/                  # Canonical event pipeline and webhook ingestion
│   ├── diagnosis/               # Failure classification and telemetry extraction
│   ├── recovery_prediction/     # Probabilistic outcome prediction models
│   ├── decision/                # Economic decision engine and value optimization
│   ├── policy/                  # Policy and safety authorization engine
│   ├── execution/               # Bounded execution orchestrator and circuit breakers
│   ├── providers/               # Provider transport layers (Razorpay Test Mode / Simulation)
│   ├── recovery_loop/           # Adaptive recovery loop and outcome classifiers
│   ├── audit/                   # Causal audit logging, reconstruction, and sanitization
│   ├── evaluation/              # Statistical benchmarking, KPI reporting, and artifacts
│   ├── dashboard/               # Read-only FastAPI dashboard API (router, schemas, service)
│   └── adversarial/             # Phase 17 adversarial security harness and assertions
│
├── frontend/                    # Phase 16 React/Vite Reviewer Dashboard
│   ├── src/
│   │   ├── api/                 # Strongly-typed HTTP API client
│   │   ├── components/          # Reusable UI components (KPICard, Funnel, CalibrationChart)
│   │   ├── context/             # Dashboard state provider (auto-refresh, run selection)
│   │   ├── pages/               # 8 full-page views for reviewer inspection
│   │   └── types/               # TypeScript data transfer object definitions
│   ├── package.json
│   └── vite.config.ts           # Development server proxy configuration
│
├── tests/                       # Automated test suites covering unit, integration, dashboard, evaluation, and adversarial security behavior
│   ├── domain/, events/, persistence/
│   ├── diagnosis/, decision/, policy/
│   ├── execution/, providers/, recovery_loop/
│   ├── audit/, evaluation/
│   ├── dashboard/               # Dashboard API contract and durability tests
│   └── adversarial/             # Phase 17 security test suites
│
├── scripts/                     # Authoritative acceptance runners (Phases 07 through 17)
│   ├── run_phase_16_acceptance.py
│   ├── run_phase_17_acceptance.py
│   └── setup_postgres_acceptance.py
│
├── migrations/                  # Alembic database migrations (versions 001 through 004)
├── docs/                        # Specifications, architecture guides, and runbooks
├── pyproject.toml               # Python project configuration (dependencies, ruff, mypy)
└── README.md                    # System documentation
```

---

## Quick Start

### 1. Prerequisites
- **Python:** Version 3.11+
- **Node.js:** Version 18+ or 20+ (with `npm`)
- **PostgreSQL:** Version 15+ or 16+ running locally on port 5432

### 2. Python Environment Setup
```powershell
# Clone or navigate to repository root
cd <repository-root>

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows PowerShell
# source .venv/bin/activate      # Linux / macOS

# Install package with all developer and test dependencies
pip install -e ".[dev]"
```

### 3. Frontend Setup
```powershell
cd frontend
npm install
cd ..
```

### 4. Database Setup & Migrations
Create the target database (e.g. `apro_test_db`) in PostgreSQL, configure your connection string, and run migrations:

```powershell
# Set database environment variable (replace with your local credentials)
$env:DATABASE_URL="postgresql+asyncpg://<username>:<password>@127.0.0.1:5432/apro_test_db"

# Apply all schema migrations
alembic upgrade head
```

### 5. Running the Backend Service
```powershell
# Start FastAPI backend (Terminal 1)
uvicorn apro.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health verification:* Check `http://127.0.0.1:8000/health` (returns `{"status":"ok","service":"apro"}`).

### 6. Running the Frontend Dashboard
```powershell
# Start Vite development server (Terminal 2)
cd frontend
npm run dev
```

### 7. Accessing the Dashboard
Open your browser and navigate to:
**[http://localhost:5173/dashboard](http://localhost:5173/dashboard)**

For a complete operational guide and troubleshooting steps, see the [Demo Runbook](docs/DEMO_RUNBOOK.md).

---

## Environment Variables

Configure application settings via environment variables or a local `.env` file:

| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | Primary PostgreSQL database URL for backend runtime and dashboard queries. | `postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/apro_test_db` |
| `POSTGRES_TEST_URL` | Database URL used by test runners, integration tests, and acceptance suites. | `postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/apro_attack_db` |
| `POSTGRES_DEMO_URL` | Target demo database URL inspected by Phase 17 to prove non-mutation. | `postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/apro_test_db` |
| `RAZORPAY_WEBHOOK_SECRET` | Secret key used to verify HMAC SHA-256 signatures on inbound webhooks. | `<webhook_signing_secret>` |
| `APP_ENV` | Runtime environment name (`development`, `staging`, `production`). | `development` |
| `APP_HOST` | Host address for FastAPI server binding. | `127.0.0.1` |
| `APP_PORT` | Port for FastAPI server binding. | `8000` |
| `LOG_LEVEL` | Minimum logging severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |

---

## Verification

### Automated Code Quality Checks

Execute all code quality verification tools from the repository root:

```powershell
# 1. Check Python linting and imports with Ruff
ruff check .

# 2. Check Python code formatting with Ruff
ruff format --check .

# 3. Perform static type checking with Mypy
mypy src

# 4. Run frontend typecheck and tests
cd frontend
npm run lint      # tsc --noEmit
npm test          # vitest run
npm run build     # tsc && vite build
cd ..
```

### Running Backend Tests

```powershell
# Run the complete test suite (unit and in-memory tests pass without external services)
pytest tests/ -q

# Run specific domain test suites
pytest tests/decision/ -v
pytest tests/policy/ -v
pytest tests/dashboard/ -v
```

*Note on PostgreSQL Integration Tests:* Tests that explicitly target PostgreSQL require a live PostgreSQL server configured via `POSTGRES_TEST_URL`. In the absence of an active PostgreSQL instance, PostgreSQL-specific tests gracefully report connection errors while all unit and in-memory tests pass cleanly.

---

## Reproducibility

APRO emphasizes strict scientific and operational reproducibility:
- **Immutable Run Provenance:** Every benchmark evaluation generates a deterministic `benchmark_run_id`, a cryptographic `report_hash`, a dataset SHA-256 digest, code revision, random seeds, and hyperparameter snapshots.
- **Audit Reconstruction:** Any historical recovery case can be deterministically reconstructed from its causal sequence of immutable audit events via `CaseReconstructionService`.
- **Reproducibility Dashboard:** Inspect full cryptographic provenance at `/dashboard/reproducibility` or via `GET /api/dashboard/reproducibility/{benchmark_run_id}`.
- See [Reproducibility Documentation](docs/REPRODUCIBILITY.md) for full specifications.

---

## Test Mode / Provider Boundary

APRO is designed to run in **Test Mode and Simulation Environments**:
- **Simulated Provider:** By default, recovery interventions are dispatched to local simulation harnesses and sandbox executors.
- **Razorpay Test Mode:** Provider integrations operate strictly in Razorpay Test Mode with test keys (`rzp_test_...`). Production keys (`rzp_live_...`) are strictly blocked by validation guards with `ProviderCredentialError`.
- **Zero Real-Money Movement:** No real-money fund movement or actual financial debiting occurs during demonstrations, tests, or evaluation benchmarks.

---

## Documentation

For comprehensive technical specifications, refer to the project documentation:

- **Operational Runbooks:**
  - [Demo & Developer Runbook](docs/DEMO_RUNBOOK.md) — Comprehensive guide to starting and operating the live dashboard.
- **Architectural & Security Documents:**
  - [Technical Architecture Guide](docs/ARCHITECTURE.md) — Detailed overview of APRO authority and module separation.
  - [Benchmark Results & Methodology](docs/BENCHMARK_RESULTS.md) — Evaluation framework, primary KPIs, and baseline comparisons.
  - [Security Results & Invariants](docs/SECURITY_RESULTS.md) — Phase 17 adversarial attack scenarios and criteria.
  - [Reproducibility Specification](docs/REPRODUCIBILITY.md) — Cryptographic provenance and audit verification guide.
- **Authoritative Phase Specifications:**
  - [Phase 09: Economic Decision Engine](docs/PHASE_09_ECONOMIC_DECISION_ENGINE_SPECIFICATION.md)
  - [Phase 10: Policy & Safety Engine](docs/PHASE_10_POLICY_AND_SAFETY_ENGINE_SPECIFICATION.md)
  - [Phase 11: Execution Framework](docs/PHASE_11_EXECUTION_FRAMEWORK_SPECIFICATION.md)
  - [Phase 12: Razorpay Test Mode Provider Integration](docs/PHASE_12_RAZORPAY_TEST_MODE_PROVIDER_INTEGRATION_SPECIFICATION.md)
  - [Phase 13: Outcome & Adaptive Recovery Loop](docs/PHASE_13_OUTCOME_AND_ADAPTIVE_RECOVERY_LOOP_SPECIFICATION.md)
  - [Phase 14: Audit & Observability Specification](docs/APRO_PHASE_14_SPECIFICATION.md)
  - [Phase 15: Benchmarking & KPI Statistical Reporting](docs/PHASE_15_BENCHMARKING_KPI_STATISTICAL_REPORTING_SPECIFICATION.md)
  - [Phase 16: Live Dashboard & Reviewer UI Specification](docs/PHASE_16_LIVE_DASHBOARD_REVIEWER_UI_SPECIFICATION.md)
  - [Phase 17: Adversarial Security Attack Harness Specification](docs/APRO_PHASE_17_ADVERSARIAL_SECURITY_ATTACK_HARNESS_SPECIFICATION.md)

---

## Status

APRO has completed engineering development through **Phase 17**:
- **Phases 00–15:** Core engineering foundation, webhook validation, persistence, domain state machines, failure diagnosis, probabilistic outcome prediction, economic decision modeling, policy authorization gates, bounded execution, Razorpay test mode integration, adaptive recovery feedback loops, immutable audit trails, and statistical benchmarking.
- **Phase 16:** Complete live reviewer dashboard (FastAPI + React/Vite) backed by PostgreSQL truth with zero static metrics or mock datasets.
- **Phase 17:** Automated adversarial attack harness verifying 10 attack scenarios, 90 acceptance criteria, and database immutability triggers.

APRO is a standalone, production-grade payment recovery intelligence system ready for technical evaluation.
