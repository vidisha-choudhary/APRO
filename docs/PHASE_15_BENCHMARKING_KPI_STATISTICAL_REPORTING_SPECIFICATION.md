# APRO Phase 15 — Benchmarking, KPI Evaluation & Statistical Reporting Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery
**Phase:** 15 — Benchmarking, KPI Evaluation & Statistical Reporting
**Architecture Leads:** Vidisha + GPT
**Implementation Lead:** Antigravity
**Baseline Commit:** `34fb73a` — Phase 14 Audit & Observability
**Status:** Authoritative implementation specification
**Primary Objective:** Measure whether APRO recovers more legitimate revenue, at acceptable cost and safety, than clearly defined baselines, with reproducible and statistically honest evidence.

---

## 0. Phase Position

```text
PHASE 0–6  Domain / Persistence / Events / Recovery Foundations
    ↓
PHASE 7    Diagnosis
    ↓
PHASE 8    Outcome Prediction
    ↓
PHASE 9    Economic Decision
    ↓
PHASE 10   Policy & Safety
    ↓
PHASE 11   Execution
    ↓
PHASE 12   Razorpay TEST / Provider Boundary
    ↓
PHASE 13   Outcome & Adaptive Recovery Loop
    ↓
PHASE 14   Audit & Observability
    ↓
PHASE 15   BENCHMARKING / KPI EVALUATION / STATISTICAL REPORTING
    ↓
PHASE 16   Dashboard / Reviewer UI
    ↓
PHASE 17   Adversarial / Security Evaluation
    ↓
PHASE 18   Demo / Pitch / Submission
```

Phase 15 is offline/evaluative. It explains how APRO performed; it does not change how APRO makes decisions.

---

# 1. Executive Mandate

Phase 15 answers:

> **Does APRO create measurable incremental legitimate revenue recovery, at what cost, with what level of confidence, and without violating its safety constraints?**

The phase produces a reproducible evaluation package from:

```text
dataset snapshot
+ persisted APRO outcomes
+ Phase 14 audit history
+ clearly defined evaluation baselines
+ deterministic metric calculations
+ statistical uncertainty
= benchmark report
```

The output is evidence, not marketing copy.

Minimum reviewer questions:

1. How many cases were evaluated?
2. What fraction recovered?
3. How much revenue was recovered?
4. How much additional revenue did APRO recover versus each baseline?
5. What did interventions cost?
6. What was net recovery after intervention cost?
7. How long did recovery take?
8. How often did APRO require multiple interventions?
9. How often did APRO stop or escalate?
10. How often were outcomes pending/unknown?
11. Did APRO violate safety invariants?
12. Are prediction probabilities calibrated?
13. How uncertain are the metrics?
14. Are improvements statistically distinguishable from zero?
15. Which cohorts benefit most or least?
16. Are conclusions causal or only benchmark associations?

---

# 2. Non-Negotiable Architectural Rules

## 2.1 Phase 15 Is Evaluative Only

Phase 15 MUST NOT:

- select a recovery action for a live case;
- authorize a recovery action;
- execute a provider;
- mutate `RecoveryCase`, `Payment`, `Decision`, `PolicyDecision`, `Execution`, or `Outcome` business state;
- call Phase 9 to alter a case;
- call Phase 10 to authorize an action;
- call Phase 11/12 for live/customer dispatch;
- introduce a competing decision engine;
- introduce adaptive recovery behavior;
- modify Phase 13 loop limits;
- alter Phase 14 audit truth.

Replay of immutable records or isolated benchmark fixtures is permitted solely for measurement.

## 2.2 Phase 9 Remains the Action Selector

The evaluator may report Phase 9 choices. Baseline policies are evaluation-only and never become APRO runtime selection logic.

## 2.3 Phase 10 Remains the Safety Authority

Policy outcomes may be measured. Policy bypasses are safety failures, not optimization opportunities.

## 2.4 No Live Provider Dispatch

Provider execution evidence must come from persisted records, deterministic Simulation fixtures, or deterministic provider stubs. Real Razorpay TEST calls are optional and never required for CI. Razorpay documents Payment Links as a create/share/receive/track flow and Test Mode as a testing environment. citeturn448935search1turn448935search2

---

# 3. Two-Plane Evaluation Model

## 3.1 Runtime Observable Plane

```text
Payment
PaymentEvent
RecoveryCase
Diagnosis
OutcomePrediction
Decision
PolicyDecision
Execution
Outcome
AuditEvent
Action History
```

This is the information APRO was permitted to use during operation.

## 3.2 Offline Evaluation Plane

Offline benchmark datasets MAY contain evaluation-only labels:

```text
ground_truth_recovered
ground_truth_recovered_amount
ground_truth_best_action
ground_truth_failure_class
ground_truth_time_to_recovery
counterfactual_outcome_labels
```

These labels must never enter `ModelInputRecord`, `DiagnosisResult`, `OutcomePrediction`, `EconomicDecisionEngine`, `PolicyEngine`, `ExecutionOrchestrator`, or `RecoveryLoopController`.

## 3.3 Anti-Cheating Rule

```text
evaluation truth → metric calculation only
evaluation truth ↛ runtime decision input
```

A score obtained by feeding oracle information into APRO is invalid.

---

# 4. Benchmark Dataset Contract

## 4.1 Run Identity

Every benchmark run records:

```text
benchmark_run_id
dataset_id
dataset_version
dataset_snapshot_hash
evaluation_config_version
metric_schema_version
code_revision
created_at
```

The dataset snapshot hash must be deterministic.

## 4.2 Case-Level Unit

The canonical evaluation unit is a unique `case_id`. A case may contain multiple cycles, decisions, executions and outcomes.

Metrics must distinguish:

```text
case_count        = unique cases
action_count      = authoritative recovery actions/executions
outcome_count     = authoritative outcomes
```

## 4.3 Eligibility

Explicitly classify:

```text
eligible
excluded
missing_required_artifact
invalid_case
duplicate_case
pending
unknown
censored
```

Every excluded case must have an exclusion reason.

---

# 5. Primary KPI Definitions

All formulas are centralized and versioned.

## 5.1 Recovery Rate

```text
recovery_rate = recovered_cases / eligible_cases
```

Only authoritative `RECOVERED` outcomes count.

An execution with `SUCCEEDED` status but without recovery evidence does not count as recovered.

## 5.2 Gross Recovered Revenue

```text
gross_recovered_amount = Σ authoritative recovered amount
```

Duplicate outcomes must not double-count revenue.

## 5.3 Revenue Recovery Rate

```text
recovered_revenue_rate = gross_recovered_amount / eligible_at_risk_amount
```

The denominator is an explicit versioned evaluation configuration field.

## 5.4 Incremental Recovery

For APRO versus baseline B:

```text
incremental_recovery_rate = APRO recovery rate - B recovery rate
incremental_recovered_amount = APRO recovered amount - B recovered amount
```

Paired evaluations calculate case-level differences before aggregation.

## 5.5 Intervention Cost

Action costs come from versioned evaluation configuration, for example:

```text
retry_cost
payment_link_cost
outreach_cost
escalation_cost
stop_cost = 0
```

These are evaluation assumptions, not hidden production policy rules.

## 5.6 Net Recovered Revenue

```text
net_recovered_revenue = gross_recovered_amount - total_intervention_cost
```

## 5.7 Cost per Recovered Rupee

```text
cost_per_recovered_rupee = total_intervention_cost / gross_recovered_amount
```

If recovered revenue is zero, return an explicit `UNDEFINED` state rather than infinity or fabricated zero.

## 5.8 Recovery Efficiency

```text
net_recovery_efficiency = net_recovered_revenue / eligible_at_risk_amount
```

---

# 6. Operational KPIs

Report:

```text
time_to_recovery: mean, median, p25, p75, p90
attempts_per_case: mean, median, p90
cycle_count
re_evaluation_count
same_action_repetition_count
terminal_disposition_mix
```

Terminal mix:

```text
RECOVERED
STOPPED
ESCALATED
PENDING / WAITING
UNKNOWN
```

Safety KPIs:

```text
policy_block_rate
state_guard_rejection_rate
stale_policy_rejection_rate
provider_transport_unknown_rate
duplicate_execution_attempt_rate
duplicate_outcome_rate
terminal_case_reopen_attempt_rate
unsafe_dispatch_rate
```

Required invariant:

```text
unsafe_dispatch_rate == 0
```

---

# 7. Baseline Benchmark Contract

Baselines are measurement constructs only.

## 7.1 Required Baselines

### Baseline A — No Intervention

```text
STOP
```

### Baseline B — Single Retry

Always attempt one bounded retry where benchmark-eligible.

### Baseline C — Payment Link

Always use the benchmark payment-link intervention where eligible.

### Baseline D — Fixed Escalation

Escalate rather than attempt adaptive recovery.

## 7.2 Optional Baselines

Where supported:

```text
historical human policy
random eligible action
cost-minimizing non-adaptive policy
oracle upper bound
```

An oracle upper bound is evaluation-only and must never be presented as an APRO runtime policy.

## 7.3 Fairness

Every comparison uses:

```text
same eligible cohort
same observation window
same revenue denominator
same cost model
same exclusion rules
```

---

# 8. Benchmark Methodology

## 8.1 Paired Evaluation

When APRO and a baseline can be evaluated on the same cases:

```text
delta_i = metric_APRO_i - metric_BASELINE_i
```

Report mean/median/quantiles of case-level differences.

## 8.2 Randomized Evaluation

When randomized assignment exists, report treatment/control counts, primary endpoint, effect estimate and 95% CI.

## 8.3 Observational Evaluation

Without valid randomization, label differences as:

```text
BENCHMARK ASSOCIATION
```

and do not call them causal incremental impact.

---

# 9. Statistical Methodology

## 9.1 Confidence Intervals

Primary metrics must report 95% confidence intervals by default. NIST describes confidence intervals as interval estimates used to quantify uncertainty around population parameters. citeturn448935search7

## 9.2 Bootstrap

For metrics where analytic assumptions are awkward:

```text
bootstrap_seed
bootstrap_iterations
resampling_unit = CASE
confidence_level = 0.95
```

The case is the independent resampling unit.

## 9.3 Binary Outcomes

For proportions, use a documented case-level interval method.

## 9.4 Continuous Outcomes

Report:

```text
mean
median
dispersion
95% CI
```

Bootstrap intervals are preferred when distributional assumptions are weak.

## 9.5 Paired Differences

Confidence intervals for paired comparisons operate on case-level differences.

## 9.6 Multiple Comparisons

When several formal hypotheses are tested, use an explicit correction policy. Default:

```text
Holm correction
```

Report number of tests, method and adjusted p-values.

## 9.7 Practical Significance

Every formal comparison reports:

```text
effect size
absolute difference
relative difference where meaningful
confidence interval
sample size
practical interpretation
```

Statistical significance alone is insufficient.

---

# 10. Prediction Quality Evaluation

Phase 8 predictions may be evaluated from persisted predictions plus offline labels.

## 10.1 Calibration

Where sample size allows:

```text
Brier score
calibration bins
predicted probability
empirical success frequency
```

## 10.2 Classification Metrics

When labels support them:

```text
ROC-AUC
PR-AUC
log loss
precision
recall
F1
```

Every classification metric specifies the positive class and missing-label treatment.

## 10.3 Per-Action Analysis

Action-level evaluation may be reported for:

```text
RETRY
PAYMENT_LINK
OUTREACH
ESCALATE
STOP
```

Shared-case dependency must be handled explicitly.

---

# 11. Decision Quality Evaluation

Evaluate Phase 9 outputs without creating an alternate selector.

Required fields:

```text
selected_action_distribution
candidate_action_count
selected_action_ERV
selected_action_cost
selected_action_outcome
```

Where offline labels exist, evaluation-only metrics MAY include:

```text
action_regret
oracle_gap
best_action_selection_rate
```

These never feed back into runtime decisions.

---

# 12. Adaptive Recovery Loop Evaluation

Phase 13 metrics:

```text
single_cycle_recovery_rate
multi_cycle_recovery_rate
recovery_after_re_evaluation_rate
mean_cycles_to_recovery
median_cycles_to_recovery
incremental_recovery_after_first_failure
same_action_avoidance_rate
bounded_termination_rate
```

Adaptive evidence must be reconstructed from persisted canonical history:

```text
Action 1 outcome
→ re-evaluation
→ Action 2
→ outcome
```

A second execution by itself is not sufficient evidence of adaptation.

---

# 13. Cohort / Segment Analysis

Major KPIs support deterministic segmentation by observable fields such as:

```text
payment_method
amount_bucket
failure_category
initial_attempt_count
customer_history_bucket
selected_action
final_disposition
execution_mode
```

Never use simulator oracle fields as runtime-facing cohort inputs:

```text
oracle_action
hidden_recoverability
potential_outcomes
future latent state
```

Minimum report breakdowns:

```text
overall
by failure category
by action
by payment method where available
```

Small cohorts must be flagged.

---

# 14. Missing / Pending / Unknown / Censored Cases

Never silently coerce uncertain data.

Use explicit states:

```text
RECOVERED
FAILED
PENDING
UNKNOWN
ESCALATED
STOPPED
EXCLUDED
CENSORED
```

Rules include:

- `UNKNOWN` execution must not become `FAILED`.
- `SUCCEEDED` execution without recovery evidence must not become `RECOVERED`.
- Pending cases outside the observation window follow the configured censoring policy.
- Missing audit artifacts create an explicit incomplete-evaluation state.

Every metric declares inclusion, exclusion or censoring treatment.

---

# 15. Statistical Reproducibility

Every result records:

```text
benchmark_run_id
dataset_snapshot_hash
evaluation_config_hash
bootstrap_seed
bootstrap_iterations
software_revision
metric_schema_version
```

Two runs against the same immutable snapshot and configuration must produce identical:

```text
point estimates
confidence intervals
cohort counts
report hash
```

unless an explicitly declared nondeterministic external dependency is used.

---

# 16. Evaluation Configuration

Required fields:

```text
metric_schema_version
evaluation_config_version
benchmark_dataset_id
observation_window
recovery_definition
cost_model
baseline_definitions
confidence_level
bootstrap_iterations
bootstrap_seed
minimum_cohort_size
multiple_comparison_policy
censoring_policy
missing_data_policy
```

No hidden defaults. The exact configuration used for a report must be serialized with it.

---

# 17. Report Contract

Primary artifact:

```text
BenchmarkReport
```

with:

```text
report_id
benchmark_run_id
dataset_id
dataset_version
snapshot_hash
created_at
code_revision
evaluation_config_version
case_counts
primary_kpis
baseline_comparisons
statistical_results
prediction_quality
decision_quality
adaptive_loop_metrics
safety_metrics
cohort_breakdowns
limitations
reproducibility_metadata
```

## 17.1 Executive Summary

Must show:

```text
APRO recovery rate
baseline recovery rates
incremental recovery
net recovered revenue
intervention cost
safety status
sample size
95% CI
```

## 17.2 Primary KPI Table

Each KPI includes:

```text
value
unit
numerator
denominator
95% CI
comparison baseline where applicable
delta where applicable
```

## 17.3 Baseline Comparison Table

For every baseline:

```text
APRO
baseline
absolute delta
relative delta where meaningful
95% CI for delta
p-value where formally applicable
adjusted p-value where applicable
```

## 17.4 Safety Table

Include:

```text
unsafe dispatches
state guard violations
stale policy usage
duplicate executions
duplicate outcomes
policy bypasses
credential leakage findings
```

## 17.5 Limitations

Every final report must state:

```text
dataset limitations
sample-size limitations
censoring
non-randomized comparison limitations
provider-test limitations
simulation limitations
ground-truth availability
```

---

# 18. Evaluation Artifact Storage

Phase 15 may add evaluation-only persistence using existing project conventions. If needed, preferred categories are:

```text
BenchmarkRun
BenchmarkCaseResult
MetricResult
StatisticalResult
BenchmarkReport
```

These are evaluation artifacts, never business-domain sources of truth.

The evaluator must never update canonical `Decision`, `PolicyDecision`, `Execution`, or `Outcome` records.

---

# 19. Package Structure

Before adding code, inspect the repository for existing benchmark/evaluation infrastructure and reuse canonical components where present.

If no suitable infrastructure exists:

```text
src/apro/evaluation/
├── __init__.py
├── enums.py
├── exceptions.py
├── models.py
├── config.py
├── dataset.py
├── metrics.py
├── baselines.py
├── statistics.py
├── calibration.py
├── segmentation.py
├── report.py
├── persistence.py
└── evaluator.py
```

Responsibilities:

- `metrics.py`: pure deterministic KPI functions.
- `baselines.py`: evaluation-only baseline definitions.
- `statistics.py`: CIs, bootstrap, paired comparisons, multiplicity correction.
- `calibration.py`: prediction quality.
- `segmentation.py`: deterministic cohorts.
- `report.py`: machine-readable and human-readable report generation.
- `dataset.py`: snapshot loading, eligibility, truth-plane separation, deterministic hashing.
- `evaluator.py`: read-only evaluation orchestration; never another APRO decision/execution engine.

---

# 20. Database / Transaction Boundary

Preferred flow:

```text
read canonical persisted truth
        ↓
construct immutable evaluation snapshot
        ↓
compute pure metrics
        ↓
persist evaluation artifact
```

No evaluator transaction may mutate canonical business state.

---

# 21. Security & Privacy

Inherit Phase 14 telemetry safety:

- no API credentials;
- no database credentials;
- no authorization headers;
- no card numbers, CVV/PIN/PAN;
- no raw provider payloads;
- no secrets;
- minimize email/phone PII;
- no simulator oracle truth in runtime-facing fields.

Reports should prefer aggregate case counts and bucketed cohorts over individual customer data.

Sentinel secrets must never appear in:

```text
BenchmarkReport
MetricResult
StatisticalResult
evaluation config
logs
exceptions
DB evaluation artifacts
```

---

# 22. Failure Policy

No:

```python
except Exception:
    pass
```

Explicit failure categories:

```text
DATASET_INVALID
INSUFFICIENT_SAMPLE
MISSING_ARTIFACT
STATISTICAL_COMPUTATION_ERROR
REPORT_GENERATION_ERROR
PERSISTENCE_ERROR
```

An invalid/incomplete benchmark must never be displayed as a valid green result.

---

# 23. Manual Acceptance Scenarios

Phase 15 must provide these 10 executable scenarios:

1. **Clean Benchmark Run** — immutable dataset → KPI computation → report.
2. **APRO vs No-Intervention** — same cohort, fair recovery/net-revenue comparison.
3. **APRO vs Fixed Retry** — recovery and cost comparison.
4. **APRO vs Payment Link** — recovery, cost and time comparison.
5. **Statistical Uncertainty** — deterministic bootstrap/CI repeatability.
6. **Adaptive Loop Measurement** — persisted Cycle 1 failure → re-evaluation → Cycle 2 recovery.
7. **Unknown / Pending Handling** — explicit uncertain/censored treatment.
8. **Prediction Calibration** — persisted predictions + offline labels.
9. **Leakage / Oracle Isolation** — offline-only truth cannot enter runtime-facing evaluation inputs.
10. **Reproducibility** — identical snapshot/config yields identical metric and report hashes.

---

# 24. Acceptance Runner

Create:

```text
scripts/run_phase_15_acceptance.py
```

The runner executes all 10 manual scenarios and **84 acceptance criteria (AC-01 to AC-84)**.

Hardened rules:

- no unconditional PASS assignments;
- no `hasattr()`-only mandatory checks;
- no broad exception swallowing to generate PASS;
- no fixture-self-comparison in place of evaluation;
- no hard-coded KPI answers;
- no hard-coded statistical answers;
- explicit failure exit code;
- deterministic evaluation configuration;
- isolated failure-detection self-test.

Return code:

```text
0      all mandatory scenarios and criteria pass
nonzero any required criterion fails
```

---

# 25. Acceptance Criteria — AC-01 to AC-84

## Dataset & Reproducibility — AC-01 to AC-08

- **AC-01**: Benchmark run receives deterministic identity.
- **AC-02**: Dataset snapshot hash is deterministic.
- **AC-03**: Evaluation configuration is versioned.
- **AC-04**: Code revision is recorded.
- **AC-05**: Eligible/excluded cases are explicitly counted.
- **AC-06**: Duplicate case handling is deterministic.
- **AC-07**: Repeated evaluation of identical snapshot is reproducible.
- **AC-08**: Evaluation truth is structurally separated from runtime decision inputs.

## Primary KPI Correctness — AC-09 to AC-20

- **AC-09**: Recovery rate uses authoritative `RECOVERED` outcomes only.
- **AC-10**: Successful execution without recovery evidence is not counted as recovered.
- **AC-11**: Gross recovered amount is duplicate-safe.
- **AC-12**: Revenue denominator is versioned.
- **AC-13**: Intervention cost is configuration-driven.
- **AC-14**: Net recovered revenue is deterministic.
- **AC-15**: Cost-per-recovered-rupee handles zero revenue safely.
- **AC-16**: Time-to-recovery is deterministic.
- **AC-17**: Attempts per case come from authoritative executions.
- **AC-18**: Cycle counts are reconstructable from persisted history.
- **AC-19**: Terminal dispositions do not double-count cases.
- **AC-20**: Primary KPI formulas are unit-tested.

## Baseline Comparison — AC-21 to AC-30

- **AC-21**: No-intervention baseline exists.
- **AC-22**: Fixed-retry baseline exists.
- **AC-23**: Payment-link baseline exists.
- **AC-24**: Fixed-escalation baseline exists.
- **AC-25**: Baselines cannot dispatch live providers.
- **AC-26**: APRO and baselines use identical eligible cohorts.
- **AC-27**: Baseline cost model is explicit.
- **AC-28**: Absolute recovery delta is deterministic.
- **AC-29**: Incremental recovered amount is deterministic.
- **AC-30**: Baseline limitations are reported honestly.

## Statistics — AC-31 to AC-42

- **AC-31**: Primary metrics expose sample size.
- **AC-32**: Binary proportion uncertainty method is documented.
- **AC-33**: Continuous metric uncertainty method is documented.
- **AC-34**: Bootstrap uses case-level resampling.
- **AC-35**: Bootstrap seed is recorded.
- **AC-36**: Bootstrap iteration count is recorded.
- **AC-37**: Bootstrap results are reproducible.
- **AC-38**: Paired comparisons use case-level differences.
- **AC-39**: Confidence intervals are deterministic.
- **AC-40**: Multiple-comparison correction is explicit where needed.
- **AC-41**: Effect sizes accompany significance tests.
- **AC-42**: Non-randomized comparisons are not mislabeled as causal effects.

## Prediction / Decision / Adaptive Evaluation — AC-43 to AC-54

- **AC-43**: Prediction metrics use persisted Phase 8 artifacts.
- **AC-44**: Brier score is deterministic.
- **AC-45**: Calibration output identifies prediction/action scope.
- **AC-46**: Classification metrics define the positive class.
- **AC-47**: Action-level prediction dependency is handled explicitly.
- **AC-48**: Decision quality uses Phase 9 outputs only.
- **AC-49**: No alternate runtime decision engine exists.
- **AC-50**: Oracle-gap metrics are evaluation-only.
- **AC-51**: Adaptive-loop metrics use canonical history.
- **AC-52**: Cycle 1 and Cycle 2 are correctly distinguished.
- **AC-53**: Re-evaluation after failure is measurable.
- **AC-54**: Same-action repetition metrics reflect authoritative actions.

## Missing / Unknown / Safety Handling — AC-55 to AC-62

- **AC-55**: `UNKNOWN` execution is not converted to `FAILED`.
- **AC-56**: `SUCCEEDED` execution without recovery evidence is not converted to `RECOVERED`.
- **AC-57**: Pending/censored cases follow documented policy.
- **AC-58**: Missing lifecycle artifacts are explicitly surfaced.
- **AC-59**: Unsafe dispatch rate is computed.
- **AC-60**: Unsafe dispatch count is zero for a valid benchmark.
- **AC-61**: Policy bypass count is zero.
- **AC-62**: Duplicate execution/outcome rates remain zero when system invariants hold.

## Cohorts & Reporting — AC-63 to AC-72

- **AC-63**: Cohort segmentation is deterministic.
- **AC-64**: Small cohorts are flagged.
- **AC-65**: Failure-category breakdown exists.
- **AC-66**: Action breakdown exists.
- **AC-67**: Payment-method breakdown exists where data is available.
- **AC-68**: Executive summary contains sample size and uncertainty.
- **AC-69**: Primary KPI table includes numerator/denominator.
- **AC-70**: Baseline table contains absolute deltas.
- **AC-71**: Safety table includes zero-violation checks.
- **AC-72**: Limitations are included in every finalized report.

## Security, Boundaries & Quality — AC-73 to AC-84

- **AC-73**: No credentials appear in evaluation artifacts.
- **AC-74**: No raw provider payloads appear in reports.
- **AC-75**: No simulator oracle truth enters runtime inputs.
- **AC-76**: Phase 15 cannot execute providers.
- **AC-77**: Phase 15 cannot authorize policy decisions.
- **AC-78**: Phase 15 cannot select runtime recovery actions.
- **AC-79**: Phase 15 cannot mutate canonical business truth.
- **AC-80**: Evaluation artifacts are separate from business-domain sources of truth.
- **AC-81**: Acceptance runner has no unconditional PASS placeholders.
- **AC-82**: Failure-detection self-test exits non-zero on injected failure.
- **AC-83**: Ruff, format and Mypy pass.
- **AC-84**: Full regression is green and Git scope contains only intended Phase 15 changes.

---

# 26. Required Verification Commands

```powershell
$env:POSTGRES_TEST_URL="postgresql+asyncpg://postgres:postgres_local_dev_2026@127.0.0.1:5432/apro_test_db"

pytest tests/evaluation/ -v
pytest tests/policy/ tests/execution/ tests/providers/ tests/recovery_loop/ -v
pytest tests/ -q

ruff check .
ruff format --check .
mypy src

python scripts/run_phase_15_acceptance.py
```

If an existing benchmark/evaluation suite has another canonical name, reuse it instead of creating a duplicate.

---

# 27. Git / Provenance Rules

Vidisha remains the only commit/push authority.

Antigravity must:

```text
implement
test
verify
report
STOP
```

Antigravity must NOT:

```text
commit
push
rewrite Phase 14 history
```

Before sign-off:

```powershell
git status --short --untracked-files=all
git diff --name-only
git diff --stat
git log -3 --oneline
```

Phase 14 must remain semantically unchanged except for bug fixes explicitly authorized by Architecture Leads.

---

# 28. Required Final Walkthrough Evidence

The completion report must contain:

```text
Phase 15 implementation: COMPLETE / INCOMPLETE

Benchmark dataset:
dataset_id:
dataset_version:
snapshot_hash:

Eligible cases:
Excluded cases:
Pending/censored cases:

APRO:
recovery_rate:
gross_recovered_amount:
net_recovered_revenue:
intervention_cost:
median_time_to_recovery:

Baseline comparison:
No-intervention:
Fixed retry:
Payment link:
Fixed escalation:

Incremental recovery:
95% CI:
Statistical method:
Bootstrap seed:
Bootstrap iterations:

Prediction quality:
Brier score:
Calibration:

Adaptive recovery:
single-cycle recovery:
multi-cycle recovery:
mean cycles:
bounded termination:

Safety:
unsafe dispatches:
policy bypasses:
stale policy reuse:
duplicate executions:
duplicate outcomes:

Scenarios:
10/10

Acceptance:
84/84

Tests:
Phase 15 tests:
Full regression:
Ruff:
Format:
Mypy:

Reproducibility:
identical repeated run: PASS/FAIL
report hash stable: PASS/FAIL

Git:
commits:
pushes:
Phase 0–14 modified semantics:
```

No report may state that APRO “wins” unless the evidence actually supports the claim.

---

# 29. Phase Boundary With Phase 16

Phase 15 produces backend evaluation truth and structured report data.

It does NOT implement:

```text
React dashboard
frontend pages
interactive filtering
web reviewer UI
charts UI
```

Phase 16 consumes the Phase 15 data contract.

---

# 30. Phase Boundary With Phase 17

Phase 15 measures performance under defined benchmark conditions.

It does NOT implement:

```text
attack harness
fuzzing
adversarial prompt injection
credential attack simulations
tamper campaigns
red-team automation
```

Those belong to Phase 17.

---

# 31. Phase Boundary With Phase 18

Phase 15 may produce credible evidence for the final demo/pitch, including:

```text
recovery uplift
net revenue recovered
cost efficiency
safety invariants
adaptive recovery performance
statistical uncertainty
```

It does not implement the demo or pitch itself.

---

# 32. Definition of Done

```text
[ ] Canonical evaluation/benchmark infrastructure identified or added
[ ] Dataset snapshot is deterministic
[ ] Runtime truth / evaluation truth boundary proven
[ ] Primary KPIs implemented and tested
[ ] Baselines implemented as evaluation-only constructs
[ ] Statistical uncertainty implemented
[ ] Bootstrap reproducibility proven
[ ] Prediction calibration implemented where labels exist
[ ] Adaptive-loop metrics reconstructed from persisted truth
[ ] Cohort reporting implemented
[ ] Missing/unknown/censored handling explicit
[ ] Security sanitization verified
[ ] No provider dispatch possible
[ ] No decision/policy authority duplicated
[ ] 10/10 manual scenarios pass
[ ] 84/84 acceptance criteria pass
[ ] Phase 15 tests pass
[ ] Full regression passes
[ ] Ruff passes
[ ] Formatting passes
[ ] Mypy passes
[ ] Git scope verified
[ ] Antigravity has not committed/pushed
```

Phase 15 closes only when the benchmark report is reproducible and a reviewer can independently inspect its evidence without relying on manually typed headline numbers.

---

## Research Notes

1. Razorpay's official Payment Links documentation describes Payment Links as a create/share/receive/track workflow and documents Test Mode for testing. This supports keeping Phase 15 read-only with respect to live provider dispatch.
   - https://razorpay.com/docs/payments/payment-links/
   - https://razorpay.com/docs/api/payments/payment-links/create-standard/

2. Razorpay documents Payment Link paid events and the paid/partially-paid lifecycle, supporting the rule that recovery metrics rely on authoritative payment evidence rather than execution success alone.
   - https://razorpay.com/docs/webhooks/payment-links/

3. NIST's e-Handbook describes confidence intervals and the interpretation of stated confidence levels, supporting the requirement to report uncertainty alongside benchmark point estimates.
   - https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm

---

**END OF PHASE 15 SPECIFICATION**
