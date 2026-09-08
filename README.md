# APRO — Adaptive Payment Recovery Orchestrator

APRO is an intelligent, policy-guarded payment recovery orchestration platform that models failed payment recovery as an adaptive decision problem—optimizing net economic recovery value under strict risk, safety, and compliance boundaries.

[![Tests](https://img.shields.io/badge/Tests-627_backend_%2B_19_frontend-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Status-Phase_17_Complete-blue.svg)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI_%7C_Python_3.11%2B-blue.svg)]()
[![Frontend](https://img.shields.io/badge/Frontend-React_%7C_TypeScript_%7C_Vite-blue.svg)]()
[![Provider](https://img.shields.io/badge/Provider-Razorpay_Test_Mode-orange.svg)]()

---

## The Problem: Why Blind Retries Fail

In payment systems, transaction failures occur for diverse and evolving reasons:
- **Technical & Transient:** Gateway timeouts, upstream network partitions, provider degradations, switch timeouts.
- **Customer & Actionable:** Insufficient funds, incorrect CVV, expired card credentials, daily transaction limits.
- **Terminal & Compliance:** Fraud blocks, stolen or lost cards, invalid merchant routing, regulatory embargoes.

Conventional payment infrastructure addresses failures using primitive retry strategies—such as static exponential backoff or immediate repeated attempts. This approach causes significant operational problems:
1. **Unnecessary Operational Costs:** Indiscriminate provider dispatches incur gateway fees, webhook delivery charges, and API throttling.
2. **Customer Friction & Fatigue:** Blasting cardholders with redundant SMS or prompts damages merchant customer relationships and churns users.
3. **Regulatory & Scheme Risk:** Retrying cards flagged for suspected fraud or exceeding scheme retry limits risks card network fines, elevated chargeback ratios, and processor termination.
4. **Sub-optimal Recovery Timing:** Attempting recovery immediately on a balance shortfall will fail, whereas scheduling recovery for payroll dates or offering a payment link alternative can recover revenue.

---

## The APRO Orchestration Pipeline

APRO decouples diagnosis, economic optimization, and safety authorization from execution through a unidirectional authority pipeline:

```text
[ Incoming Failure Webhook ]
             │
             ▼
┌───────────────────────────┐
│ 1. Failure Diagnosis      │ ──> Categorizes raw error codes into semantic archetypes
└───────────────────────────┘
             │
             ▼
┌───────────────────────────┐
│ 2. Outcome Prediction     │ ──> Computes calibrated success probabilities per action (p̂)
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
```

> **Strict Authority Boundary:** Economic optimizers *recommend* candidate recovery actions by expected value; the policy engine *authorizes* actions independently. No recovery action executes without an explicit policy authorization artifact.
>
> *For detailed component specifications and the complete authority ownership matrix, see the [Technical Architecture Guide](docs/ARCHITECTURE.md).*

---

## Key Differentiators

- **Economic Optimization vs. Blind Retries:** Rather than indiscriminate retrying, APRO ranks actions to maximize Expected Net Recovery Value:
  $$\text{ENRV} = \hat{p} \cdot \text{Amount} - \text{Intervention Cost} - \text{Customer Fatigue Penalty}$$
- **Independent Policy Authorization Gate:** Financial decision models cannot self-authorize. The policy engine independently enforces cooldown windows, maximum retry budgets, and scheme compliance rules before dispatch.
- **Adaptive Closed-Loop Feedback:** Recovery is modeled as a multi-cycle closed-loop control system. If an initial attempt fails, APRO incorporates observed feedback to adjust subsequent timing, switch channels (e.g. from automated retry to customer payment link), or halt deterministically.
- **Database-Enforced Immutability:** Audit events and benchmark reports are protected by PostgreSQL triggers (`prevent_audit_events_mutation`), preventing audit tampering or retrofitted metrics.
- **Zero-Mock PostgreSQL Truth:** Observability views and reviewer dashboards query actual database state, displaying verified evaluation metrics or clean empty states without synthetic mock data.

---

## Live Reviewer Dashboard

APRO includes an interactive, read-only reviewer dashboard backed by FastAPI and React 18 / Vite 5.

### Reviewer Views
- **`/dashboard` (Overview):** Real-time recovery KPIs (Recovery Rate, Net Revenue Recovered, Cost Efficiency, System Health) and full-funnel conversion analysis.
- **`/dashboard/benchmarks` (Benchmarks):** Statistical comparisons against Zero-Action, Blind Retry, and Heuristic baselines with 95% bootstrap confidence intervals.
- **`/dashboard/cases` (Case Explorer):** Paginated search, status filtering, and causal inspection of recovery cases.
- **`/dashboard/cases/:caseId` (Case Detail):** Deep-linked case audit provenance, chronological event timeline, and answers to the **Seven Authoritative Reviewer Questions (Q1–Q7)**:
  1. *Why did this payment fail?* (Failure archetype & gateway error telemetry)
  2. *What recovery action was chosen and why?* (Candidate action ranking & ENRV)
  3. *What was the predicted success probability?* (Calibrated $\hat{p}$)
  4. *What was the expected net economic value?* (Net economic calculation)
  5. *Did policy and safety authorize the action?* (Policy decision & rules evaluated)
  6. *What was the outcome of the intervention?* (Provider execution status)
  7. *What was the subsequent adaptive response?* (Loop progression or terminal halt)
- **`/dashboard/safety` (Safety Invariants):** Live evaluation of system safety invariants and violation counters.
- **`/dashboard/predictions` (Prediction Quality):** Reliability diagrams, ECE curves, and discrimination metrics.
- **`/dashboard/adaptive` (Adaptive Recovery):** Multi-cycle progression, cycle attempt distributions, and re-evaluation lift.
- **`/dashboard/cohorts` (Cohort Analysis):** Disaggregated segment performance across payment methods, card networks, and failure archetypes.
- **`/dashboard/reproducibility` (Provenance):** Full cryptographic run manifests, dataset SHA-256 digests, git commit hash, and random seeds.

### UI Integrity Invariants
- **No Static Business Metrics:** All cards, charts, and tables are populated by live API queries against PostgreSQL.
- **No Mock Datasets:** If the database contains no benchmark runs or cases, the UI displays clean empty-state components rather than falling back to dummy figures.
- **Auto-Refresh & Run Selector:** Context-wide 10-second polling interval with live badge control and a dynamic benchmark run dropdown selector.

*For complete operational instructions, see the [Demo & Developer Runbook](docs/DEMO_RUNBOOK.md).*

---

## Evaluation & Security Verification

### Benchmarking & Statistical Evaluation
APRO includes a comprehensive benchmarking engine ([`src/apro/evaluation/`](src/apro/evaluation)) that evaluates recovery strategies against standard industry baselines on deterministic datasets:
- **Baseline Models:** Zero Action (organic recovery), Blind Retry (indiscriminate retrying), and Rule-Based Heuristic.
- **Evaluated Metrics:** Net Revenue Recovered, Recovery Uplift with 95% bootstrap confidence intervals, Cost Efficiency Ratio, and Expected Calibration Error (ECE).
- **Persisted Truth:** Benchmark results are stored in PostgreSQL (`evaluation_benchmark_reports` table) alongside cryptographic report hashes and dataset digests.
- *Detailed methodology and figures:* [Benchmark Results & Methodology](docs/BENCHMARK_RESULTS.md).

### Adversarial Security Harness (Phase 17)
The security test harness ([`src/apro/adversarial/`](src/apro/adversarial)) executes 10 adversarial attack scenarios across 90 automated acceptance criteria (AC-01 through AC-90):
1. **Policy Bypass Attacks:** Injecting execution attempts with rejected, unapproved, or forged policy decisions.
2. **Stale Authority Replay:** Replaying expired policy tokens across state transitions and modified cases.
3. **Duplicate Replay Storms:** Flooding concurrent identical webhooks and execution requests.
4. **Capture Race Conditions:** Triggering rapid concurrent authorization and capture events.
5. **Illegal State Transitions:** Attempting to force transitions from terminal states back into active recovery.
6. **Truth-Plane Isolation:** Attempting to leak counterfactual or oracle dataset attributes into runtime pipelines.
7. **Audit Tampering:** Direct SQL injection executing `UPDATE` or `DELETE` queries on `audit_events`.
8. **Benchmark Tampering:** Attempting to overwrite existing evaluation records or alter historical reports.
9. **Dashboard Abuse:** Submitting HTTP mutations (`POST`, `PUT`, `DELETE`, `PATCH`) to read-only endpoints.
10. **Secret Exfiltration:** Persisting canonical sentinels to verify total redaction across logs, audit records, API endpoints, and exports.
- **Dual-Database Isolation:** The harness executes against `apro_attack_db` and verifies that the canonical demo/judge database (`apro_test_db`) undergoes **zero mutations**.
- *Detailed security invariants:* [Security Results & Invariants](docs/SECURITY_RESULTS.md).

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
Create a local development database (e.g. `apro_local_db`) in PostgreSQL, configure your connection string, and run migrations:

```powershell
# Set database environment variable (replace with your local credentials)
$env:DATABASE_URL="postgresql+asyncpg://<username>:<password>@127.0.0.1:5432/apro_local_db"

# Apply all schema migrations
alembic upgrade head
```

*Database Isolation Note:* The repository enforces strict database topology isolation. Canonical demonstration and benchmark evaluation state is maintained separately in `apro_test_db` (see [Demo Runbook](docs/DEMO_RUNBOOK.md)), while adversarial security test suites execute against `apro_attack_db`. Ordinary local development and new developer setups should use a dedicated database like `apro_local_db` rather than mutating or repurposing the canonical demo database.

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

For a complete operational guide and troubleshooting steps, see the [Demo & Developer Runbook](docs/DEMO_RUNBOOK.md).

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
├── tests/                       # Automated test suites (627 backend tests)
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

## Environment Variables

Configure application settings via environment variables or a local `.env` file:

| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | Primary PostgreSQL database URL for backend runtime and dashboard queries. | `postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/apro_local_db` |
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
npm test          # vitest run (19 passed)
npm run build     # tsc && vite build
cd ..
```

### Running Backend Tests

```powershell
# Run the complete backend test suite
pytest tests/ -q

# Run specific domain test suites
pytest tests/decision/ -v
pytest tests/policy/ -v
pytest tests/dashboard/ -v
```

*Note on PostgreSQL Integration Tests:* PostgreSQL-backed integration and acceptance tests require a running PostgreSQL instance configured through `POSTGRES_TEST_URL`.

---

## Reproducibility & Provider Boundaries

### Reproducibility
APRO emphasizes strict scientific and operational reproducibility:
- **Immutable Run Provenance:** Every benchmark evaluation generates a deterministic `benchmark_run_id`, a cryptographic `report_hash`, a dataset SHA-256 digest, code revision, random seeds, and hyperparameter snapshots.
- **Audit Reconstruction:** Any historical recovery case can be deterministically reconstructed from its causal sequence of immutable audit events via `CaseReconstructionService`.
- **Reproducibility Dashboard:** Inspect full cryptographic provenance at `/dashboard/reproducibility` or via `GET /api/dashboard/reproducibility/{benchmark_run_id}`.
- See [Reproducibility Documentation](docs/REPRODUCIBILITY.md) for full specifications.

### Test Mode / Provider Boundary
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

APRO is a standalone, fully tested payment recovery orchestration system designed for technical evaluation and reproducible experimentation.
