# APRO — Demo & Developer Runbook

This runbook describes how to launch, configure, and inspect the live APRO system and reviewer dashboard.

---

## 1. System Architecture

The live demo dashboard operates on a clean three-tier architecture backed by PostgreSQL truth:

```text
[ Reviewer Browser ]
         │
         │  http://localhost:5173 (React 18 / Vite 5)
         ▼
[ Frontend Web Server ]
         │
         │  /api/* proxies to http://127.0.0.1:8000
         ▼
[ FastAPI Backend Service ]
         │
         │  SQLAlchemy Async Engine + UnitOfWork
         ▼
[ PostgreSQL Truth Store ]
  ├── apro_test_db           (Judge / Demo database: canonical cases, audit events, benchmark runs)
  ├── apro_attack_db         (Adversarial attack harness database: Phase 17 tests)
  └── apro_phase18_acceptance_db (Isolated clean-room acceptance database)
```

---

## 2. Database Topology & Protection Rules

APRO enforces strict environment isolation across three database roles:

| Database Identifier | Environment Role | Intended Usage | Security Policy |
|---|---|---|---|
| `apro_test_db` | **Judge / Live Demo** | Holds persistent canonical benchmark evaluations, reconstructed cases, and immutable audit logs. Powers the Live Dashboard. | **CANONICAL & PROTECTED.** Destructive tests, table truncation, acceptance fixture injection, and attack mutations are strictly prohibited. |
| `apro_attack_db` | **Phase 17 Adversarial** | Dedicated sandbox for destructive security testing, replay floods, and sentinel injection. | **ISOLATED SANDBOX.** Mutated and re-created freely during security acceptance runs. |
| `apro_phase18_acceptance_db` | **Clean-Room Acceptance** | Clean-room target for validating automated setup, migrations, and cold-start reproducibility. | **EPHEMERAL ACCEPTANCE.** Must never share state with `apro_test_db`. |

### Critical Invariants for `apro_test_db`

1. **Never Run Acceptance Scripts Against `apro_test_db`:** `scripts/run_phase_16_acceptance.py` and other phase acceptance scripts are designed for automated verification and reset/truncate evaluation tables with temporary acceptance fixtures. Running them against `apro_test_db` corrupts the canonical judge-facing demonstration state.
2. **Never Run Attack Harnesses Against `apro_test_db`:** `scripts/run_phase_17_acceptance.py` must point `POSTGRES_TEST_URL` to `apro_attack_db`. The runner verifies that `apro_test_db` (`POSTGRES_DEMO_URL`) undergoes **zero mutations**.
3. **No Destructive Operations:** `DROP TABLE`, `TRUNCATE`, or manual row modifications against `apro_test_db` are strictly forbidden.
4. **Canonical State Requirement:** The repository does not currently bundle an automated demo seed script. The live demo requires `apro_test_db` to retain its persisted, canonical benchmark reports and recovery cases. If deploying to a completely fresh database without historical demo state, the dashboard will display clean, non-crashing empty states until canonical runs are executed or imported.

---

## 3. Prerequisites

Before starting, ensure the following are installed:

- **Python:** Version 3.11+
- **Node.js:** Version 18+ or 20+ (with `npm`)
- **PostgreSQL:** Version 15+ or 16+ running locally on port 5432

---

## 4. Step-by-Step Startup Guide

### Step 1: Initialize Python Environment

```powershell
# Navigate to repository root
cd V:\APRO

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows PowerShell
# source .venv/bin/activate      # Linux / macOS

# Install package and dependencies in editable mode
pip install -e ".[dev]"
```

### Step 2: Configure Environment Variables

Create a local `.env` file or export variables in your active shell:

```powershell
# Set backend database to point to the judge/demo database
$env:DATABASE_URL="postgresql+asyncpg://<username>:<password>@127.0.0.1:5432/apro_test_db"
$env:APP_ENV="development"
$env:LOG_LEVEL="INFO"
```

*(Note: Replace `<username>` and `<password>` with your local PostgreSQL credentials. Never commit real credentials to Git.)*

### Step 3: Run Database Migrations

Apply all Alembic schema migrations to ensure the database schema is up to date:

```powershell
alembic upgrade head
```

This applies migrations:
- `001_initial_phase_02_schema`: Core domain tables (`customers`, `payments`, `recovery_cases`, `recovery_actions`, `executions`, `outcomes`).
- `002_add_provider_payment_id`: Provider reconciliation metadata.
- `003_enforce_audit_events_immutability_trigger`: PostgreSQL trigger rejecting `UPDATE` or `DELETE` on `audit_events`.
- `004_add_evaluation_benchmark_reports`: Schema for persisted benchmark reports and report immutability triggers.

### Step 4: Start the FastAPI Backend (Terminal 1)

```powershell
uvicorn apro.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify service health:
```powershell
curl http://127.0.0.1:8000/health
# Expected response: {"status":"ok","service":"apro"}
```

Interactive OpenAPI documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Step 5: Start the React / Vite Frontend (Terminal 2)

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server will start at: [http://localhost:5173](http://localhost:5173).

---

## 5. Reviewing the Live Dashboard

Open your browser to: **[http://localhost:5173/dashboard](http://localhost:5173/dashboard)**

### Key Reviewer Views to Inspect

1. **Overview (`/dashboard`):** High-level operational recovery KPIs, net recovery lift, and recovery funnel progression.
2. **Benchmark Comparisons (`/dashboard/benchmarks`):** Evaluated performance against Zero-Action, Blind Retry, and Heuristic baselines with 95% bootstrap confidence intervals and p-values.
3. **Case Explorer (`/dashboard/cases`):** Paginated search and filtering across recovery cases. Click any case ID to open the deep-linked detail view.
4. **Case Detail (`/dashboard/cases/:caseId`):** Reconstructs the complete case lifecycle and answers the Seven Authoritative Reviewer Questions (Q1–Q7) with causal audit provenance.
5. **Safety Invariants (`/dashboard/safety`):** Real-time verification of safety guarantees (0 unsafe dispatches, 0 policy bypasses, 0 duplicate executions).
6. **Prediction Quality (`/dashboard/predictions`):** Reliability diagrams, Expected Calibration Error (ECE) curves, and ROC-AUC / PR-AUC metrics.
7. **Adaptive Recovery (`/dashboard/adaptive`):** Multi-cycle recovery distributions and re-evaluation lift curves.
8. **Cohort Breakdown (`/dashboard/cohorts`):** Disaggregated segment performance across payment methods, card tiers, banks, and failure categories.
9. **Provenance & Reproducibility (`/dashboard/reproducibility`):** Cryptographic manifest, dataset SHA-256 digests, seeds, and copyable JSON manifest.

---

## 6. Reviewer Features

- **Benchmark Run Selector:** Located in the top header. Allows switching between persisted benchmark runs (`GET /api/dashboard/runs`). Selecting a run updates the URL search param `?benchmark_run_id=...` and synchronizes across all tabs.
- **Auto-Refresh Toggle:** Displays last refresh timestamp and automatically polls the backend every 10 seconds. Can be paused or triggered manually via the header badge.
- **Deep Linking:** Case inspection URLs (e.g., `/dashboard/cases/<case_id>`) can be bookmarked or shared directly.

---

## 7. Troubleshooting

| Issue | Root Cause | Solution |
|---|---|---|
| Backend fails on startup with `TargetServerAttributeNotMatched` or `ConnectionRefusedError` | PostgreSQL is not running or credentials in `DATABASE_URL` are incorrect. | Verify PostgreSQL is running on `127.0.0.1:5432` and check credentials. |
| Dashboard displays "No benchmark run available" empty state | Database is fresh and does not contain pre-existing canonical benchmark runs. | Expected behavior on fresh databases. Do **NOT** run acceptance scripts against `apro_test_db` to populate data. Verify `DATABASE_URL` points to the canonical demo database containing verified evaluation runs. |
| Frontend displays "Backend API unreachable" | FastAPI backend is not running on port 8000 or proxy misconfigured. | Ensure `uvicorn apro.main:app` is active in Terminal 1. |
| `alembic upgrade head` fails with table already exists | Existing database has schema from manual SQL execution. | Ensure clean database or stamp Alembic version with `alembic stamp head`. |
