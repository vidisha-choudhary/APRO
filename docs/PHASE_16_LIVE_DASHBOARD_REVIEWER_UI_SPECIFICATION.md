# APRO Phase 16 — Live Dashboard & Reviewer UI Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery
**Phase:** 16 — Live Dashboard & Reviewer UI
**Architecture Leads:** Vidisha + GPT
**Implementation Lead:** Antigravity
**Baseline Commit:** `b2fedab` — Phase 15 Benchmarking, KPI Evaluation & Statistical Reporting
**Status:** Authoritative implementation specification — ready for implementation after user approval/download
**Primary Objective:** Turn APRO's existing Phase 14 audit truth and Phase 15 evaluation truth into a **live, interactive, reproducible reviewer dashboard** backed by the running APRO API/database rather than static demo data.

---

# 0. Executive Requirement — THE DASHBOARD MUST BE LIVE

This phase has one especially important requirement:

> **The dashboard must display real values produced by APRO and its persisted evaluation artifacts. It must not be a collection of hard-coded demo numbers.**

A reviewer should be able to:

```text
start APRO
    ↓
open dashboard
    ↓
dashboard queries APRO backend
    ↓
backend reads PostgreSQL / canonical Phase 14 + Phase 15 data
    ↓
dashboard renders current values
    ↓
refresh / trigger a new safe evaluation
    ↓
values change only when authoritative underlying data changes
```

The dashboard must therefore be **data-driven, interactive, and reproducible**.

Static placeholder arrays such as:

```javascript
const recoveryRate = 66.67;
const recoveredRevenue = 20000;
const cases = 30;
```

are explicitly prohibited except inside isolated UI tests.

The UI may display an empty state when no data exists. It may not silently replace missing backend data with fake values.

---

# 1. Phase Position

```text
PHASE 0–6
Core Domain / Simulation / Persistence
        ↓
PHASE 7
Diagnosis
        ↓
PHASE 8
Prediction
        ↓
PHASE 9
Economic Decision
        ↓
PHASE 10
Policy & Safety
        ↓
PHASE 11
Execution
        ↓
PHASE 12
Razorpay TEST / Provider Boundary
        ↓
PHASE 13
Outcome & Adaptive Recovery Loop
        ↓
PHASE 14
Audit & Observability
        ↓
PHASE 15
Benchmarking / KPI / Statistical Reporting
        ↓
PHASE 16
LIVE DASHBOARD / REVIEWER UI
        ↓
PHASE 17
Adversarial / Security Evaluation
        ↓
PHASE 18
Demo / Pitch / Submission
```

Phase 16 consumes Phase 14 and Phase 15 truth. It does not replace them.

---

# 2. Architectural Mandate

Phase 16 provides:

```text
Live reviewer dashboard
Case reconstruction UI
Benchmark/KPI visualization
Adaptive recovery visualization
Audit timeline visualization
Safety/integrity indicators
Reproducibility controls
```

Phase 16 does **not**:

```text
select recovery actions
authorize policies
execute payment recovery
call Razorpay directly
modify canonical business state
rewrite audit events
recompute Phase 9 decisions
recompute Phase 10 policy
duplicate Phase 13 orchestration
duplicate Phase 15 statistical methodology
implement adversarial testing
```

The dashboard is a **read/query/presentation layer**.

---

# 3. Live Data Contract

## 3.1 Backend Is the Source of Display Truth

Every production dashboard value MUST originate from a backend response.

Preferred flow:

```text
React UI
   ↓ HTTP/JSON
FastAPI dashboard/query endpoints
   ↓
Phase 14 / Phase 15 services
   ↓
PostgreSQL / canonical persisted artifacts
   ↓
JSON response
   ↓
React rendering
```

FastAPI provides an OpenAPI schema and interactive API documentation, which should be used as the authoritative contract for dashboard endpoints. citeturn818305search4turn818305search11

## 3.2 No Static Business Values

The following are prohibited in application runtime code:

```text
hard-coded recovery rate
hard-coded recovered revenue
hard-coded baseline deltas
hard-coded case count
hard-coded safety score
hard-coded benchmark sample size
hard-coded audit timeline
hard-coded reviewer answers
```

The only allowed constants are presentation/configuration constants such as:

```text
polling interval
page size
chart labels
formatting precision
display thresholds
```

## 3.3 Deterministic UI Rendering

React components should remain pure projections of received data. Side effects such as fetching should live outside render logic; React's guidance explicitly distinguishes rendering from external-system synchronization. citeturn818305search2turn818305search7

---

# 4. Dashboard Modes

The dashboard has three user-facing modes.

## 4.1 Operations Overview

Shows the current state of the evaluation/recovery system.

Must include:

```text
Eligible cases
Recovered cases
Recovery rate
Gross recovered revenue
Net recovered revenue
Intervention cost
Median time to recovery
Average cycles
Safety status
Latest benchmark run
```

## 4.2 Case Explorer

Allows reviewer to select a `case_id`.

The dashboard then retrieves the authoritative reconstructed case from Phase 14 and displays:

```text
Trigger
Diagnosis
Predictions
Candidate actions
Selected action
Policy decision
Execution
Provider evidence
Outcome
Adaptive cycles
Terminal state
```

The seven Phase 14 reviewer questions must be shown directly from backend reconstruction data.

## 4.3 Benchmark / Evaluation View

Displays Phase 15 results:

```text
APRO KPI set
baseline comparisons
confidence intervals
p-values where applicable
prediction quality
decision quality
adaptive recovery metrics
safety metrics
cohort breakdowns
limitations
reproducibility metadata
```

The dashboard must display the benchmark's actual `benchmark_run_id`, dataset version and report hash.

---

# 5. Required Dashboard Pages / Views

## 5.1 Overview

Route:

```text
/dashboard
```

Required widgets:

```text
Recovery Rate
Recovered Revenue
Net Revenue
Intervention Cost
Time to Recovery
Safety Status
Benchmark Sample
Adaptive Recovery
Latest Update
```

Each KPI card must expose:

```text
current value
unit
numerator
denominator where applicable
source
last updated timestamp
```

## 5.2 Recovery Funnel

Show the real case population through:

```text
Eligible
→ Attempted
→ Pending
→ Recovered
→ Stopped
→ Escalated
```

Do not fabricate funnel counts.

Counts must come from backend aggregate endpoints.

## 5.3 Baseline Comparison

Display:

```text
APRO
No Intervention
Fixed Retry
Payment Link
Fixed Escalation
```

For each:

```text
recovery rate
net recovery
absolute delta
95% CI
p-value when valid
comparison label
```

Clearly label:

```text
BENCHMARK ASSOCIATION
```

when the result is observational.

## 5.4 Adaptive Recovery View

Display:

```text
single-cycle recovery
multi-cycle recovery
recovery after re-evaluation
mean cycles
median cycles
same-action avoidance
bounded termination
```

Also render a cycle flow:

```text
Cycle 1
Action → Outcome
        ↓
Re-evaluation
        ↓
Cycle 2
Action → Outcome
        ↓
Terminal result
```

The flow must be driven by the selected case or aggregate API response.

## 5.5 Safety & Integrity View

Show:

```text
Unsafe dispatches
Policy bypasses
Stale policy reuse
Duplicate executions
Duplicate outcomes
StateGuard rejections
Terminal-case reopen attempts
Provider unknown rate
```

The dashboard should visibly distinguish:

```text
PASS / SAFE
WARNING
FAIL
NO DATA
```

Do not use a green safety indicator when the backend reports missing/unknown data.

## 5.6 Prediction Quality View

Display:

```text
Brier score
calibration curve
probability bins
empirical success rate
ROC-AUC where available
PR-AUC where available
F1
precision
recall
log loss
```

Label small-sample or unavailable metrics honestly.

## 5.7 Audit / Timeline View

For a selected case:

```text
case created
diagnosis
prediction
decision
policy
execution start
execution result
provider evidence
outcome
re-evaluation
next decision
next policy
next execution
terminal closure
```

Use the Phase 14 event ordering.

Do not reconstruct a fake UI timeline from client-side event ordering.

## 5.8 Reviewer Questions View

Provide an explicit panel for:

```text
Q1 What happened?
Q2 Why interpreted that way?
Q3 What was considered?
Q4 What was recommended?
Q5 What did policy allow?
Q6 What executed?
Q7 What happened afterward?
```

Answers must come from the Phase 14 reconstruction API.

## 5.9 Reproducibility View

Display:

```text
benchmark_run_id
dataset_id
dataset_version
snapshot_hash
evaluation_config_version
metric_schema_version
code_revision
bootstrap_seed
bootstrap_iterations
report_hash
created_at
```

Provide a visible:

```text
Refresh
Re-run evaluation
```

control only where the backend supports safe evaluation without mutating canonical business state.

---

# 6. API CONTRACT

Before implementing UI components, inspect existing FastAPI routes.

Reuse existing routes where appropriate.

If no canonical dashboard API exists, create a dedicated read-only API package such as:

```text
src/apro/api/
    dashboard.py
    schemas.py
```

or an equivalent repository-compatible location.

## 6.1 Required Endpoints

Preferred endpoints:

```http
GET /api/dashboard/overview
GET /api/dashboard/funnel
GET /api/dashboard/benchmarks
GET /api/dashboard/prediction-quality
GET /api/dashboard/adaptive
GET /api/dashboard/safety
GET /api/dashboard/cohorts
GET /api/dashboard/cases
GET /api/dashboard/cases/{case_id}
GET /api/dashboard/cases/{case_id}/timeline
GET /api/dashboard/cases/{case_id}/reviewer-questions
GET /api/dashboard/reproducibility/{benchmark_run_id}
```

Exact routing may follow existing project conventions.

## 6.2 Common Response Metadata

Every dashboard response should carry:

```text
generated_at
source_revision
data_version
query_scope
```

Where useful:

```text
last_updated_at
benchmark_run_id
report_hash
```

## 6.3 API Must Be Read-Only

Dashboard endpoints must not:

```text
POST live recovery action
POST provider execution
PUT payment
PATCH recovery case
DELETE audit event
```

A benchmark refresh may invoke Phase 15's evaluation service only when it is explicitly a read/evaluation operation and never mutates canonical business state.

---

# 7. LIVE UPDATE / REFRESH MODEL

The dashboard must remain useful without requiring a page reload.

## 7.1 Minimum Requirement

Implement polling or an equivalent lightweight refresh mechanism.

Recommended default:

```text
overview / KPI refresh: every 10 seconds
case timeline refresh: every 5 seconds while viewing an active case
```

These are UI configuration values, not business logic.

## 7.2 Optional Enhancement

WebSocket or Server-Sent Events may be used if a simple existing infrastructure exists.

Do NOT introduce:

```text
Kafka
Redis pub/sub
Celery
Kubernetes
microservices
```

just for dashboard updates.

## 7.3 Staleness Indicator

Display:

```text
Updated 3s ago
```

or:

```text
Data delayed
```

when the query is stale.

Never present stale data as live.

---

# 8. REPRODUCIBLE VALUE REQUIREMENT

This is a critical Phase 16 acceptance rule.

The dashboard must support:

```text
same backend state
→ same API response
→ same displayed KPI values
```

apart from explicitly dynamic metadata such as timestamps.

## 8.1 UI Reproducibility Test

For the same immutable benchmark run:

```text
GET benchmark data
GET benchmark data again
```

must yield identical business values.

The test should ignore only:

```text
request latency
client render timestamp
```

where applicable.

## 8.2 Report Hash

The dashboard must display the Phase 15 `report_hash`.

It must not calculate a new business result in the browser.

The backend owns report hashing.

## 8.3 Refresh Behavior

Refreshing the same page against the same benchmark snapshot must not cause the values to drift.

---

# 9. CASE EXPLORER DATA CONTRACT

For:

```text
GET /api/dashboard/cases/{case_id}
```

return a structured representation such as:

```text
case
payment
diagnosis
predictions
decisions[]
policies[]
executions[]
outcomes[]
cycles[]
reviewer_questions
audit_completeness
integrity_status
```

The UI must not infer missing lifecycle stages.

If Phase 14 reports:

```text
INCOMPLETE
```

show that explicitly.

If integrity reports corruption:

```text
CORRUPT
```

show that prominently.

---

# 10. UI FILTERING & INTERACTIVITY

The dashboard must be genuinely interactive.

At minimum:

```text
date/observation window
benchmark run
failure category
selected action
payment method
final disposition
cycle count
```

Case Explorer must support:

```text
case_id search
status filter
sort by time
sort by recovered amount
```

Filtering should produce backend-driven or correctly scoped in-memory presentation data from the API response.

Never ship static filter datasets.

---

# 11. CHARTS & VISUALIZATIONS

Use charts only where they communicate evidence clearly.

Required charts:

### Chart 1 — Recovery Rate by Baseline

```text
APRO
No Intervention
Fixed Retry
Payment Link
Fixed Escalation
```

Include confidence intervals when available.

### Chart 2 — Recovery by Failure Category

Backend-generated cohort data.

### Chart 3 — Adaptive Cycle Distribution

```text
1 cycle
2 cycles
3+ cycles
```

### Chart 4 — Time to Recovery

Use the actual returned distribution or quantile data.

### Chart 5 — Calibration

Probability bin vs observed recovery frequency.

### Chart 6 — Safety Outcomes

Counts/rates for:

```text
blocked
guarded
unknown
unsafe
```

Never generate random chart data for visual polish.

---

# 12. DESIGN / UX REQUIREMENTS

The dashboard should look like a serious reviewer/product demo rather than a generic admin template.

Desired characteristics:

```text
clean
high information density
clear hierarchy
excellent typography
strong spacing
restrained color usage
obvious safety status
easy case navigation
```

The visual language must communicate:

```text
AI-assisted
evidence-backed
safety-constrained
economically evaluated
auditable
```

Do not clutter the interface with decorative animations.

Use color semantically:

```text
green = success/safe
amber = warning/incomplete
red = failure/unsafe
neutral = normal data
```

Do not use color as the only encoding.

---

# 13. EMPTY / ERROR / LOADING STATES

Every view must support:

```text
loading
no data
backend unavailable
invalid case
incomplete audit
corrupt audit
benchmark unavailable
metric unavailable
permission/error state
```

Examples:

```text
No benchmark run available.
Run or load a benchmark evaluation to populate this view.
```

not:

```text
Recovery rate: 66.67%
```

when no data exists.

---

# 14. SECURITY

The dashboard must inherit Phase 14 sanitization guarantees.

Never display:

```text
API credentials
database URLs
database passwords
Authorization headers
raw provider payloads
PAN/CVV/PIN
secret tokens
```

Provider references must remain sanitized.

Do not expose internal exception stack traces to normal reviewers.

Avoid exposing unnecessary customer PII.

---

# 15. FRONTEND TECHNOLOGY

Before creating a frontend app, inspect the repository for an existing frontend.

If one exists:

```text
reuse it
inspect its conventions
extend it
```

If none exists, use a lightweight modern React application compatible with the existing APRO backend.

React's current guidance favors function components and predictable state-driven rendering. citeturn818305search0turn818305search1

A standard Vite + React + TypeScript structure is acceptable if the repository has no frontend conventions.

Recommended:

```text
frontend/
├── src/
│   ├── app/
│   ├── components/
│   ├── pages/
│   ├── api/
│   ├── hooks/
│   ├── charts/
│   ├── types/
│   └── styles/
├── package.json
└── ...
```

Do not add unnecessary framework complexity.

---

# 16. FRONTEND DATA ACCESS CONTRACT

All network access should be centralized.

Preferred:

```text
frontend/src/api/
```

containing typed query clients.

Components should not scatter raw `fetch()` calls throughout JSX.

Every query should expose:

```text
data
loading
error
lastUpdated
```

Use explicit request cancellation/cleanup where needed.

---

# 17. BACKEND AGGREGATION CONTRACT

Dashboard endpoints should aggregate from canonical services instead of copying business logic.

Prefer:

```text
Phase 14 reconstruction service
Phase 15 evaluation/report services
existing repositories
```

Do NOT duplicate:

```text
recovery formulas
baseline formulas
statistical formulas
audit reconstruction
policy evaluation
decision selection
```

The browser should not independently recompute benchmark KPIs.

---

# 18. NO SECOND METRIC ENGINE

Phase 15 remains the only KPI/statistical authority.

Phase 16 can:

```text
format
filter
sort
plot
paginate
```

It must NOT independently recalculate:

```text
recovery rate
incremental recovery
confidence intervals
p-values
Brier score
bootstrap results
```

The browser displays the values returned by Phase 15.

---

# 19. NO BUSINESS MUTATION

The dashboard must not write to:

```text
RecoveryCase
Payment
RecoveryAction
Decision
PolicyDecision
Execution
Outcome
AuditEvent
```

Dashboard interactions are:

```text
GET
filter
search
select
refresh
visualize
export
```

only.

If an export is provided, it must export already-computed read-only backend results.

---

# 20. REPRODUCIBLE DEMO DATA

To make the dashboard demonstrable from a clean checkout, provide a **deterministic demo dataset fixture** only if no persisted evaluation dataset is guaranteed to exist.

The fixture must be clearly labeled:

```text
DEMO / SYNTHETIC DATASET
```

and must be generated deterministically from a fixed seed.

It must NOT be silently substituted for real data.

Preferred hierarchy:

```text
1. Real persisted Phase 15 benchmark run
2. Explicitly selected deterministic demo dataset
3. Empty state
```

Never:

```text
no data
→ silently show fake success numbers
```

---

# 21. DEMO SEED / REPRODUCIBILITY

If a demo fixture is implemented:

```text
demo_dataset_id
demo_dataset_version
demo_seed
snapshot_hash
```

must be visible in the UI.

Running the demo fixture generation twice must produce identical:

```text
case IDs
KPI values
baseline values
chart data
report hash
```

excluding generated timestamps where explicitly allowed.

---

# 22. DASHBOARD API TESTS

Backend tests must verify:

```text
overview returns real persisted KPI values
benchmark endpoint returns real Phase 15 values
case endpoint reconstructs from case_id
timeline follows Phase 14 ordering
reviewer questions come from reconstruction
safety metrics match Phase 15
report hash matches persisted report
unknown/incomplete state is preserved
```

No fixture-self-comparison.

At least one integration test must:

```text
insert/use real evaluation artifacts
→ call dashboard API
→ assert response against actual persisted values
```

---

# 23. FRONTEND TESTS

Include:

```text
KPI rendering from API response
loading state
empty state
API failure state
case explorer
timeline rendering
benchmark comparison
safety status
filters
refresh
reproducibility
no static business values
```

A static-source test should inspect production frontend code and reject obvious hard-coded KPI numbers or fallback datasets.

---

# 24. LIVE VALUE TEST

This is mandatory.

Create an executable test that proves:

```text
1. Query dashboard.
2. Record KPI value V1.
3. Change the underlying evaluation artifact through the legitimate test fixture/persistence path.
4. Query dashboard again.
5. Receive KPI value V2.
6. Assert V2 reflects the changed persisted truth.
7. Restore/isolate test state.
```

This proves the dashboard is actually connected to backend truth rather than rendering a static dataset.

Do not mutate production data.

Use an isolated test database/fixture.

---

# 25. REFRESH REPRODUCIBILITY TEST

For an immutable benchmark run:

```text
request A
request B
```

must produce identical business data.

The test should compare normalized JSON responses after excluding permitted volatile metadata.

---

# 26. SECURITY / LEAKAGE TESTS

Inject sentinels into backend payload fixtures:

```text
sentinel_dashboard_secret_87654321
sentinel_card_number
sentinel_auth_header
sentinel_database_url
sentinel_provider_payload
```

Then prove they are absent from:

```text
dashboard API responses
serialized report payload
frontend-rendered text
export output
logs where relevant
```

---

# 27. PHASE BOUNDARY TESTS

Prove Phase 16 contains:

```text
0 action-selection engine
0 policy engine
0 execution engine
0 provider transport
0 recovery loop
0 statistical engine duplicate
0 audit truth writer
0 adversarial harness
```

Allowed:

```text
read/query clients
API aggregation
formatting
visualization
```

---

# 28. ACCESSIBILITY

The dashboard should provide:

```text
semantic headings
keyboard navigation
visible focus states
accessible labels
chart summaries / tabular equivalents
non-color status encoding
```

Do not hide important metrics exclusively inside charts.

---

# 29. PERFORMANCE

The dashboard should avoid querying the entire audit database for every render.

Preferred:

```text
aggregated backend endpoint for overview
case-specific endpoint for Case Explorer
benchmark-specific endpoint for benchmark view
```

Pagination required for large case lists.

Do not send raw entire audit history to the browser when a summary endpoint is sufficient.

---

# 30. REPORT EXPORT

Provide read-only export of the currently selected benchmark/case view where useful.

Allowed:

```text
JSON
Markdown
CSV for tabular evaluation data
```

Exports must use backend-provided truth.

Do not create a browser-side alternate benchmark calculation.

---

# 31. OBSERVABILITY OF THE DASHBOARD

Dashboard requests should be identifiable operationally without leaking sensitive data.

Where Phase 14 structured logging is reused:

```text
dashboard route
request ID / trace ID where available
response status
duration
```

No secrets or raw customer payloads.

---

# 32. ACCEPTANCE SCENARIOS

Phase 16 must include at least 10 executable scenarios.

### Scenario 1 — Live Overview

Start the APRO backend with persisted benchmark data and verify the dashboard displays the actual database KPI values.

### Scenario 2 — Dynamic Value Change

Change an isolated evaluation fixture legitimately and verify the dashboard value changes after refresh.

### Scenario 3 — Case Explorer

Enter a real `case_id` and reconstruct the case from backend truth.

### Scenario 4 — Reviewer Questions

Display all 7 reviewer questions from Phase 14 reconstruction.

### Scenario 5 — Adaptive Cycle Visualization

Display a real multi-cycle Phase 13 case with Cycle 1 → re-evaluation → Cycle 2.

### Scenario 6 — Benchmark Comparison

Display APRO vs all required baselines using Phase 15 results.

### Scenario 7 — Safety View

Display real safety metrics and correctly reflect PASS/WARNING/FAIL.

### Scenario 8 — Empty / Failure State

Stop or isolate the backend and verify the UI shows an explicit unavailable/error state rather than fake values.

### Scenario 9 — Reproducibility

Load the same immutable benchmark twice and prove identical business values/report hash.

### Scenario 10 — Security / Boundary

Inject sentinel secrets and verify they cannot appear in dashboard responses or rendered reviewer content.

---

# 33. ACCEPTANCE RUNNER

Create:

```text
scripts/run_phase_16_acceptance.py
```

It must verify the 10 scenarios plus **82 acceptance criteria**.

The runner must contain:

```text
0 unconditional PASS assignments
0 hard-coded KPI answers
0 static demo data silently substituted for missing backend data
0 broad exception swallowing
0 fixture-self-comparison used as evidence
0 browser-side duplicate metric calculations
```

The runner must fail non-zero when a mandatory criterion fails.

It must include an isolated failure-detection self-test.

---

# 34. ACCEPTANCE CRITERIA — AC-01 TO AC-82

## Live Data & API — AC-01 to AC-12

- **AC-01**: Dashboard reads KPI values from backend APIs.
- **AC-02**: Overview values match persisted Phase 15 values.
- **AC-03**: No hard-coded business KPI values exist in production UI code.
- **AC-04**: Missing data produces explicit empty state.
- **AC-05**: Backend unavailable produces explicit error state.
- **AC-06**: Dashboard API is read-only.
- **AC-07**: API contracts are typed/documented.
- **AC-08**: Case Explorer retrieves by `case_id`.
- **AC-09**: Audit timeline comes from Phase 14.
- **AC-10**: Reviewer questions come from Phase 14 reconstruction.
- **AC-11**: Benchmark data comes from Phase 15.
- **AC-12**: Dashboard does not mutate canonical business truth.

## KPI / Benchmark Visualization — AC-13 to AC-24

- **AC-13**: Recovery rate is displayed from authoritative KPI output.
- **AC-14**: Gross recovered revenue is displayed accurately.
- **AC-15**: Net recovered revenue is displayed accurately.
- **AC-16**: Intervention cost is displayed accurately.
- **AC-17**: Time-to-recovery is displayed accurately.
- **AC-18**: Baseline comparison values match Phase 15.
- **AC-19**: Confidence intervals are displayed when available.
- **AC-20**: p-values are displayed only when actually present/valid.
- **AC-21**: Observational comparisons are labeled correctly.
- **AC-22**: Prediction quality values match Phase 15.
- **AC-23**: Adaptive-loop values match Phase 15.
- **AC-24**: Safety metrics match Phase 15.

## Case Reconstruction — AC-25 to AC-34

- **AC-25**: Real `case_id` lookup works.
- **AC-26**: Case timeline follows authoritative ordering.
- **AC-27**: Diagnosis is displayed from persisted truth.
- **AC-28**: Prediction is displayed from persisted truth.
- **AC-29**: Candidate actions are displayed from persisted decision trace.
- **AC-30**: Selected action is displayed from Phase 9 evidence.
- **AC-31**: Policy result is displayed from Phase 10 evidence.
- **AC-32**: Execution result is displayed from Phase 11/12 evidence.
- **AC-33**: Outcome is displayed from Phase 13 evidence.
- **AC-34**: Incomplete/corrupt audit states are preserved visibly.

## Live / Refresh / Reproducibility — AC-35 to AC-44

- **AC-35**: Dashboard refreshes without full page reload.
- **AC-36**: Active case views refresh while useful.
- **AC-37**: Last-updated timestamp is displayed.
- **AC-38**: Stale data is visually identified.
- **AC-39**: Same immutable benchmark yields identical business values.
- **AC-40**: Report hash is displayed.
- **AC-41**: Refresh does not introduce metric drift.
- **AC-42**: Legitimate test-data change propagates to dashboard.
- **AC-43**: Dynamic value test is executable.
- **AC-44**: Reproducibility test is executable.

## Interactivity & Cohorts — AC-45 to AC-53

- **AC-45**: Benchmark run can be selected.
- **AC-46**: Failure-category filtering works.
- **AC-47**: Action filtering works.
- **AC-48**: Payment-method filtering works where available.
- **AC-49**: Disposition filtering works.
- **AC-50**: Cycle filtering works.
- **AC-51**: Case search works.
- **AC-52**: Case list pagination works.
- **AC-53**: Charts reflect the selected/filterable backend data.

## Security — AC-54 to AC-61

- **AC-54**: API credentials never appear in UI.
- **AC-55**: Database credentials never appear in UI.
- **AC-56**: Authorization headers never appear in UI.
- **AC-57**: Raw provider payloads never appear in UI.
- **AC-58**: Sensitive payment data is minimized.
- **AC-59**: Sentinel leakage test passes.
- **AC-60**: Normal reviewer error views do not expose stack traces.
- **AC-61**: Demo fixtures are explicitly labeled synthetic when used.

## Boundaries — AC-62 to AC-70

- **AC-62**: No runtime action-selection engine exists in Phase 16.
- **AC-63**: No policy engine exists in Phase 16.
- **AC-64**: No execution/provider dispatch exists in Phase 16.
- **AC-65**: No duplicate Phase 15 metric engine exists in frontend code.
- **AC-66**: No audit-event mutation exists in Phase 16.
- **AC-67**: No Phase 13 recovery orchestration exists in Phase 16.
- **AC-68**: No Phase 17 adversarial harness exists in Phase 16.
- **AC-69**: Dashboard endpoints are read/evaluation-only.
- **AC-70**: Phase 0–15 business semantics remain unchanged.

## UX / Accessibility / Quality — AC-71 to AC-82

- **AC-71**: Loading states exist for all primary views.
- **AC-72**: Empty states exist for all primary views.
- **AC-73**: Error states exist for all primary views.
- **AC-74**: Keyboard navigation works for primary interactions.
- **AC-75**: Semantic headings and accessible labels exist.
- **AC-76**: Important chart information has non-chart/tabular equivalents.
- **AC-77**: Color is not the sole status encoding.
- **AC-78**: Dashboard performance remains acceptable for paginated datasets.
- **AC-79**: Frontend tests pass.
- **AC-80**: Backend dashboard API tests pass.
- **AC-81**: Acceptance runner has genuine failure detection.
- **AC-82**: Full regression and quality gates remain green.

---

# 35. REQUIRED TEST STRUCTURE

Preferred backend tests:

```text
tests/dashboard/
├── test_api_overview.py
├── test_api_case_reconstruction.py
├── test_api_benchmark.py
├── test_api_safety.py
├── test_api_reproducibility.py
├── test_api_security.py
├── test_api_boundaries.py
└── test_live_value_propagation.py
```

Preferred frontend tests:

```text
frontend/src/**/*.test.*
```

or existing repository convention.

Tests must use deterministic fixtures.

---

# 36. REQUIRED VERIFICATION COMMANDS

First inspect the existing frontend/tooling.

Then use the repository's actual commands.

If the backend remains:

```text
FastAPI + uvicorn
```

verify the API is live.

Recommended backend checks:

```powershell
$env:POSTGRES_TEST_URL="postgresql+asyncpg://postgres:postgres_local_dev_2026@127.0.0.1:5432/apro_test_db"

pytest tests/dashboard/ -v
pytest tests/ -q

ruff check .
ruff format --check .
mypy src

python scripts/run_phase_16_acceptance.py
```

Frontend commands should follow the detected package manager, for example:

```text
npm test
npm run build
npm run lint
```

Do not blindly run commands that do not exist in the repository.

---

# 37. GIT / PROVENANCE RULES

Vidisha remains the only commit/push authority.

Antigravity must:

```text
implement
test
verify
report
STOP
```

Do not:

```text
git commit
git push
```

Before sign-off:

```powershell
git status --short --untracked-files=all
git diff --name-only
git diff --stat
git log -3 --oneline
```

Phase 0–15 semantics must remain unchanged.

---

# 38. FINAL WALKTHROUGH REQUIREMENTS

Antigravity's final report must contain:

```text
Phase 16 implementation: COMPLETE / INCOMPLETE

Frontend:
framework:
routes:
build status:

Live-data proof:
overview source:
benchmark source:
case reconstruction source:
dynamic value propagation: PASS/FAIL

Dashboard values:
eligible cases:
recovery rate:
gross recovered revenue:
net recovered revenue:
intervention cost:
median time to recovery:

Benchmark:
APRO:
No Intervention:
Fixed Retry:
Payment Link:
Fixed Escalation:
95% CI:
p-values:
comparison label:

Adaptive:
single-cycle recovery:
multi-cycle recovery:
mean cycles:
bounded termination:

Safety:
unsafe dispatches:
policy bypasses:
stale policy:
duplicate executions:
duplicate outcomes:

Reproducibility:
benchmark run ID:
dataset snapshot:
evaluation config:
report hash:
same snapshot twice: PASS/FAIL
report hash stable: PASS/FAIL

Case reconstruction:
case_id:
Q1-Q7 answered from backend: PASS/FAIL
audit completeness:
integrity status:

Security:
sentinel leakage: PASS/FAIL

Scenarios:
10/10

Acceptance:
82/82

Backend tests:
Frontend tests:
Full regression:
Ruff:
Format:
Mypy:
Frontend build/lint:

Git:
commits:
pushes:
Phase 0–15 semantic modifications:
```

---

# 39. DEFINITION OF DONE

Phase 16 is closed only when:

```text
[ ] Existing frontend infrastructure inspected/reused where appropriate
[ ] Live FastAPI/dashboard API implemented
[ ] Overview page displays real persisted Phase 15 values
[ ] Benchmark view displays real benchmark values
[ ] Case Explorer uses real Phase 14 reconstruction
[ ] Seven reviewer questions displayed from backend truth
[ ] Adaptive cycle visualization uses real Phase 13 history
[ ] Safety view uses real safety metrics
[ ] Prediction quality view uses real Phase 15 results
[ ] Refresh/polling works
[ ] Dynamic value propagation test passes
[ ] Same-snapshot reproducibility test passes
[ ] Report hash displayed
[ ] No static fallback business numbers
[ ] Empty/error/loading states implemented
[ ] Security leakage tests pass
[ ] Dashboard boundary tests pass
[ ] Frontend tests pass
[ ] Backend dashboard tests pass
[ ] 10/10 scenarios pass
[ ] 82/82 acceptance criteria pass
[ ] Full regression passes
[ ] Ruff passes
[ ] Formatting passes
[ ] Mypy passes
[ ] Frontend build/lint passes
[ ] Git scope verified
[ ] Antigravity has not committed/pushed
```

---

# 40. Critical Reviewer-Demo Requirement

The final dashboard should make this reviewer interaction possible:

```text
Reviewer opens dashboard
        ↓
sees live APRO KPI values
        ↓
selects a benchmark run
        ↓
sees APRO vs baselines
        ↓
opens a real case
        ↓
sees:
  what happened
  why it was interpreted that way
  what actions were considered
  what APRO recommended
  what policy allowed
  what executed
  what happened afterward
        ↓
opens adaptive-cycle view
        ↓
sees Cycle 1 failure
        ↓
sees re-evaluation
        ↓
sees Cycle 2 recovery
        ↓
checks safety
        ↓
checks reproducibility metadata
        ↓
can verify that displayed values came from APRO's persisted backend truth
```

That is the intended Phase 16 reviewer experience.

---

# 41. Phase Boundary With Phase 17

Phase 17 will test APRO under adversarial conditions.

Phase 16 must not contain:

```text
red-team harness
fuzzing
prompt injection tests
credential attack tests
tamper simulations
adversarial case generator
```

The dashboard may **display Phase 17 results later**, but Phase 17 execution belongs to Phase 17.

---

# 42. Phase Boundary With Phase 18

Phase 18 will package the project into the final demo/pitch/submission.

Phase 16 must not implement:

```text
final pitch
submission website
video generation
presentation automation
```

It should merely provide the live, reviewer-friendly evidence that Phase 18 can present.

---

# 43. Research / Design Notes

1. FastAPI's official documentation describes automatic OpenAPI schema generation and interactive API documentation, supporting typed/documented dashboard API contracts. citeturn818305search4turn818305search11
2. React's documentation recommends function-based components and predictable state-driven rendering; it also recommends keeping side effects outside render and using Effects when synchronizing with external systems. citeturn818305search1turn818305search2turn818305search7

---

**END OF PHASE 16 SPECIFICATION**
