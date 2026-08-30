# APRO — Phase 6 Dataset & Evaluation Foundation Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 6 — Dataset & Evaluation Foundation  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0

---

## 1. Purpose

Phase 6 establishes the dataset and evaluation foundation required before APRO's final intelligence models are built.

Phase 5 provides the independent synthetic scenario and outcome engine. Phase 6 turns those reproducible scenarios into governed datasets and benchmark runs that can later support:

- Model A — Failure Diagnosis;
- Model B — Action-Conditioned Recovery Prediction;
- deterministic baseline comparison;
- economic-value evaluation;
- safety/reliability evaluation;
- reproducible benchmark evidence.

Phase 6 must make it possible to answer, with controlled and auditable data:

> Does APRO perform better than reasonable alternative strategies without training/evaluation leakage or unfair access to hidden truth?

The primary evaluation unit is the **Recovery Case**.

The initial benchmark target is **at least 1,000 independent Recovery Cases**, with support for substantially larger batches.

---

## 2. Authoritative Source Hierarchy

Implementation must follow the repository's established authority hierarchy:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. Completed Phase 0–5 specifications and evidence
10. This document: `docs/PHASE_06_DATASET_EVALUATION_FOUNDATION_SPECIFICATION.md`

The master plan defines Phase 6 as:

- dataset generation;
- train/validation/test split;
- temporal separation where applicable;
- feature snapshotting;
- benchmark runner;
- metric collection;
- baseline framework.

The simulation/evaluation specification additionally requires:

- 1,000+ case benchmark capability;
- held-out evaluation protection;
- multiple seeds;
- dataset/scenario/configuration versioning;
- baseline comparison;
- economic and safety metrics;
- per-case traces;
- distribution-shift capability;
- reproducible benchmark runs;
- honest reporting and benchmark integrity.

Antigravity must not independently redesign these boundaries.

If a conflict is discovered:

```text
STOP
↓
DOCUMENT THE CONFLICT
↓
REPORT TO ARCHITECTURE LEADS
↓
ARCHITECTURE DECISION
↓
UPDATED SPECIFICATION IF REQUIRED
↓
CONTINUE
```

---

## 3. Phase Dependency

Phase 6 depends directly on the completed Phase 5 Simulation Engine.

Current lineage:

```text
PHASE 4
Recovery Case Orchestration
        ↓
PHASE 5
Simulation Engine
        ↓
PHASE 6
Dataset & Evaluation Foundation
        ↓
PHASE 7 ─────────── PHASE 8
Diagnosis            Recovery Prediction
        ↓                  ↓
        └────── PHASE 9 ───┘
```

Phase 7 and Phase 8 must consume the governed foundation produced here rather than creating incompatible dataset/split/benchmark conventions.

---

## 4. Scope

### 4.1 In Scope

Phase 6 implements:

- dataset generation from Phase 5 scenarios;
- dataset record schemas;
- observable feature snapshots;
- hidden evaluation truth separation;
- dataset manifests;
- dataset versioning;
- feature-schema versioning;
- scenario/configuration version tracking;
- deterministic dataset generation;
- train/validation/test splitting;
- temporal separation where applicable;
- leakage prevention and split-integrity checks;
- benchmark dataset generation;
- benchmark versioning;
- distribution-shift benchmark support;
- benchmark runner;
- baseline framework;
- baseline fairness constraints;
- metric collection;
- economic metrics;
- intervention metrics;
- decision-quality metric primitives;
- safety/reliability metric collection;
- per-case evaluation traces;
- batch aggregation;
- multi-seed benchmark execution;
- reproducibility manifests;
- benchmark summary artifacts;
- failure/segment analysis hooks.

### 4.2 Explicitly Out of Scope

Phase 6 must NOT implement:

- Model A diagnosis model;
- Model B recovery prediction model;
- ML training algorithms;
- model selection;
- model hyperparameter search;
- model calibration;
- production feature store;
- economic decision engine;
- ERV-based production decisioning;
- policy engine;
- policy rules H1–H10;
- execution framework;
- Razorpay outbound operations;
- real customer intervention;
- adaptive recovery loop;
- production dashboard;
- final Phase 15 benchmark program;
- final submission/reporting package.

Phase 6 creates the foundation consumed by those later systems.

It may expose generic interfaces for models, predictions, policies, actions, and outcomes, but it must not implement the later business logic.

---

## 5. Core Architecture

The Phase 6 architecture is:

```text
PHASE 5 SCENARIO GENERATOR
          │
          ├───────────────┐
          ▼               ▼
 OBSERVABLE STATE     HIDDEN TRUTH
          │               │
          ▼               │
   FEATURE SNAPSHOT       │
          │               │
          ├───────────────┤
          ▼               ▼
     DATASET RECORD   EVALUATION TRUTH
          │               │
          ├───────┬───────┘
          ▼       ▼
       TRAIN    VALIDATION
          │
          ▼
      HELD-OUT TEST
          │
          ▼
   BENCHMARK DATASET
          │
          ▼
    BENCHMARK RUNNER
          │
     ┌────┼─────────┐
     ▼    ▼         ▼
 BASELINES  APRO   OUTCOME ENGINE
     │      │         │
     └──────┼─────────┘
            ▼
      METRIC COLLECTION
            │
            ▼
       PER-CASE TRACE
            │
            ▼
     BENCHMARK SUMMARY
```

The critical separation is:

```text
APRO/model input
≠
hidden evaluation truth
```

The benchmark evaluator may use hidden truth.

APRO must not.

---

## 6. Dataset Types

Phase 6 must support four logical dataset types:

```text
TRAINING
VALIDATION
HELD_OUT_TEST
BENCHMARK
```

Each dataset must identify its type explicitly.

### Training Dataset

Used later by model-training phases.

May contain:

- observable feature snapshot;
- task-specific training labels where justified;
- scenario metadata required for reproducibility.

Must not contain hidden truth as model features.

### Validation Dataset

Used for model selection/tuning by later phases.

Must be separate from training data.

May contain labels/truth needed for validation.

Must not be reused as final test data.

### Held-Out Test Dataset

Reserved for final model evaluation.

Must remain untouched during:

- feature selection;
- model selection;
- hyperparameter tuning;
- threshold tuning;
- calibration tuning;
- repeated experimentation.

### Benchmark Dataset

Reserved for benchmark runs and strategy comparison.

It must have its own version.

It must remain frozen for a benchmark version.

---

## 7. Dataset Record

Every dataset record must contain enough metadata to reconstruct its provenance.

Minimum metadata:

```text
dataset_version
dataset_type
record_id
scenario_id
generation_seed
scenario_version
configuration_version
feature_schema_version
benchmark_version (when applicable)
```

Where temporal evaluation is enabled, also record:

```text
decision_timestamp
```

A record may contain:

```text
observable_features
labels
evaluation_context
```

but hidden truth must remain in a separate evaluator-only structure.

---

## 8. Hidden Truth Separation

Phase 5 already establishes hidden and observable scenario state.

Phase 6 must preserve that separation.

Use two conceptual layers:

```text
ModelInputRecord
```

and:

```text
EvaluationTruthRecord
```

`ModelInputRecord` may contain:

- observable context;
- action candidates;
- pre-decision historical features;
- decision timestamp;
- dataset/version metadata;
- training label where the later supervised task legitimately requires it.

`EvaluationTruthRecord` may contain:

- recoverability;
- customer behavior class;
- true failure mechanism;
- action-conditioned potential outcomes;
- realized outcome;
- best achievable outcome/value;
- other simulator-only truth required for evaluation.

The evaluator may join these records internally.

They must never be exposed to the model through the model-input interface.

---

## 9. Feature Snapshotting

Phase 6 must create a frozen feature snapshot at the exact decision point.

The snapshot must represent only information available at decision time.

Example:

```text
decision_timestamp = T0

feature snapshot:
    payment amount
    payment method
    attempt count
    failure information
    pre-decision customer history
    temporal information
```

Forbidden in the feature snapshot:

```text
future payment capture
post-action behavior
post-action outcome
hidden recoverability
hidden customer behavior class
potential outcome
future intervention result
APRO-selected action outcome
```

Every snapshot must identify:

```text
feature_schema_version
```

A material feature-definition change requires a new feature schema version.

A feature schema must be reproducible from the same governed source data.

---

## 10. Leakage Prevention

Leakage prevention is a hard Phase 6 requirement.

Every candidate feature must satisfy:

> Could this information have been known at the exact moment of the model decision?

If the answer is no, it must not enter the model input.

Phase 6 must contain automated checks for at least:

- future outcome fields;
- post-action timestamps;
- hidden simulation fields;
- labels accidentally present as features;
- cross-split record overlap;
- duplicate scenario IDs across incompatible splits;
- customer/history leakage across temporal boundaries where grouping requires protection.

A test passing only because the current synthetic data happens to contain no leak is insufficient.

The dataset layer must actively validate the schema and record boundaries.

---

## 11. Deterministic Dataset Generation

Given the same:

```text
dataset configuration
dataset_version
scenario_version
configuration_version
generation seed set
```

the generated dataset must be reproducible.

The order of test execution or process scheduling must not alter generated records.

Dataset ordering must be deterministic.

A dataset manifest must record the exact generation inputs.

---

## 12. Dataset Versioning

Every generated dataset must have an explicit:

```text
dataset_version
```

Examples:

```text
dataset-v1
dataset-v2
benchmark-v1
benchmark-v2
```

A material change to:

- included scenarios;
- sampling/distribution rules;
- split policy;
- label construction;
- feature schema;
- evaluation truth semantics;
- benchmark eligibility;

requires a new dataset/benchmark version.

Do not silently mutate an existing benchmark.

---

## 13. Scenario and Configuration Version Tracking

Each record must preserve:

```text
scenario_version
configuration_version
```

from the Phase 5 simulation layer.

This prevents later evaluation from becoming impossible to reproduce after simulator changes.

A benchmark manifest must capture all relevant versions.

---

## 14. Train / Validation / Test Splitting

Phase 6 must provide deterministic splitting.

Minimum split:

```text
TRAINING
VALIDATION
HELD_OUT_TEST
```

The split must occur before later model tuning.

### Preferred temporal strategy

Where decision timestamps are available:

```text
older cases
    ↓
TRAINING

later cases
    ↓
VALIDATION

latest cases
    ↓
HELD_OUT_TEST
```

This better approximates future deployment.

### Group leakage protection

When multiple records can belong to the same underlying customer, payment episode, or scenario lineage, the split system must support grouping so related records do not cross train/test boundaries improperly.

No scenario may appear simultaneously in training and held-out test.

No record duplication may be used to inflate counts.

---

## 15. Temporal Separation

Where temporal evaluation is enabled:

- define a deterministic cutoff;
- record the cutoff in the dataset manifest;
- guarantee test timestamps are later than training timestamps;
- prevent history generated after a decision from appearing in an earlier snapshot;
- report split ranges.

A temporal split is not merely a random split with timestamps attached.

If a random split is used for a specific experiment, the reason and exact seed must be recorded.

---

## 16. Benchmark Dataset

The benchmark dataset is an immutable evaluation asset for a given benchmark version.

Minimum initial size:

```text
1,000 Recovery Cases
```

The architecture should support:

```text
10,000+
```

for stress evaluation.

Benchmark datasets must include meaningful representation across:

```text
failure families
payment value buckets
attempt counts
customer histories
action types
recoverability classes
scenario difficulty
```

No major category should appear only accidentally or in negligible quantity without explicit reporting.

---

## 17. Distribution Shift

Phase 6 must support a benchmark distribution that differs somewhat from the training distribution.

Examples:

```text
different failure-family mix
different payment-value distribution
changed customer behavior distribution
changed action effectiveness
higher ambiguity
```

The shifted benchmark must remain governed and reproducible.

If simulator configuration changes materially, the configuration version must change.

The purpose is to test whether later models learned useful structure rather than memorizing one exact simulator distribution.

---

## 18. Challenge / Stress Dataset Support

Phase 6 should support explicit challenge subsets for later evaluation.

Useful challenge patterns include:

```text
rare failure + high value
first-time customer + transient failure
repeated failure + historically reliable customer
low-confidence-like observable context
conflicting signals
high-value ambiguous scenario
```

Challenge subsets must be generated from governed configuration and identified in the dataset manifest.

Do not inject hidden labels into the challenge features.

---

## 19. Candidate Action Representation

The benchmark foundation must preserve the Phase 5 action vocabulary:

```text
RETRY
PAYMENT_LINK
OUTREACH
STOP
ESCALATE
```

Dataset records must preserve the candidate action set.

Action order must be deterministic.

The benchmark runner must support a strategy selecting one permitted action per case.

Phase 6 does not execute those actions.

It evaluates their simulated consequences.

---

## 20. Baseline Framework

The benchmark runner must support deterministic baseline strategy adapters.

Minimum required baselines:

### Baseline 0 — No Intervention

```text
Always STOP
```

### Baseline 1 — Always Retry

```text
If recovery candidate:
    RETRY
```

subject to the same benchmark eligibility and safety constraints available to the benchmark runner.

### Baseline 2 — Static Failure Rules

A fixed, documented rule set.

Initial example:

```text
TRANSIENT          → RETRY
AUTHENTICATION     → OUTREACH
OTHERWISE          → STOP
```

The actual configured rules must be explicit and versioned.

### Baseline 3 — Global Action Rate

Select the action with the highest historically observed recovery rate.

When trained/derived from data, the rate must be computed only from the training portion available to the baseline.

It must not inspect validation/test/benchmark outcomes before evaluation.

---

## 21. Baseline Fairness

Every baseline must operate on the same benchmark cases.

Every strategy must receive only information allowed at decision time.

No baseline may receive:

```text
hidden state
future outcome
potential outcomes
privileged truth
different recovery opportunities
```

Baselines must use the same benchmark action availability.

The same safety eligibility constraints must apply unless a baseline is explicitly labeled as a theoretical unconstrained comparator.

Benchmark traces must record:

```text
strategy_name
strategy_version
chosen_action
```

---

## 22. Benchmark Runner

Implement a deterministic benchmark runner capable of:

```text
load frozen benchmark dataset
        ↓
load strategy adapters
        ↓
run every strategy over every case
        ↓
obtain simulated outcome
        ↓
collect per-case trace
        ↓
aggregate metrics
        ↓
produce benchmark summary
```

For initial Phase 6 acceptance, the runner must support at least:

```text
1,000 cases
multiple seeds
No Intervention
Always Retry
Static Rules
```

It should also support Global Action Rate.

The benchmark runner must not require manual intervention for ordinary batch cases.

---

## 23. Outcome Evaluation

The benchmark evaluator must use Phase 5's independent outcome engine.

For a chosen action:

```text
observable/model decision
        +
simulator-managed hidden truth
        ↓
outcome
```

The evaluator may compare the chosen action against hidden potential outcomes for counterfactual analysis.

Those hidden alternatives must never become model input.

Phase 6 must not alter the Phase 5 outcome-generation semantics.

---

## 24. Primary Economic Metrics

Implement metric collection for:

```text
Revenue at Risk
Revenue Recovered
Incremental Revenue Recovered
Recovery Rate
Recovered Revenue / Intervention
Intervention Rate
Unnecessary Intervention Rate
Stop Rate
Escalation Rate
```

Definitions:

### Revenue at Risk

```text
sum of eligible payment amounts
```

### Revenue Recovered

```text
payment amount
```

when the simulated outcome successfully recovers the payment; otherwise zero.

### Recovery Rate

```text
recovered cases / eligible cases
```

The denominator must be explicit in the metric configuration.

### Incremental Recovery

```text
strategy recovered revenue
−
baseline recovered revenue
```

### Intervention Efficiency

```text
recovered revenue / number of interventions
```

### Intervention Rate

```text
intervention cases / eligible cases
```

### Unnecessary Intervention Rate

Defined from benchmark ground truth.

Examples:

- intervention where STOP would have produced the same result;
- intervention on a non-recoverable case;
- repeated intervention after recovery.

The definition must be fixed in the benchmark configuration.

---

## 25. Decision Quality Metric Primitives

Phase 6 must support generic decision-quality calculations that can later be used by APRO evaluation.

At minimum:

```text
Optimal Action Rate
Regret
Expected Value Capture
Action Selection Accuracy
```

### Regret

```text
best achievable recovered value
−
actual recovered value
```

using hidden benchmark truth.

This metric is evaluator-only.

### Expected Value Capture

```text
actual recovered value
/
best achievable recovered value
```

with an explicitly defined zero-denominator policy.

APRO must never receive the hidden best action/value during decision-making.

---

## 26. Safety and Reliability Metric Collection

Phase 6 must provide collection fields for:

```text
Policy Violation Count
Duplicate Execution Count
Captured-Payment Intervention Count
Retry-Limit Violation Count
Invalid-Model-Execution Count
Unknown-State Unsafe Execution Count
Webhook Processing Success
Event Deduplication Rate
Decision Success Rate
Execution Success Rate
Unknown Execution Rate
API Error Rate
Average Decision Latency
```

Phase 6 does not implement the Policy Engine or Execution Framework.

It provides the metric schema and collection interfaces so later phases can submit the relevant signals.

For metrics whose upstream subsystem does not yet exist, the Phase 6 result must represent that absence explicitly rather than inventing a successful value.

---

## 27. Metric Integrity

Metrics must be:

- deterministic;
- reproducible;
- explicitly defined;
- integer-safe for monetary amounts;
- free of hidden test leakage;
- computed from frozen run data;
- traceable to per-case records.

All monetary values must remain in integer minor units internally.

Every metric result should identify:

```text
benchmark_version
dataset_version
scenario_version
configuration_version
seed
strategy
metric_version
```

where applicable.

---

## 28. Multi-Seed Evaluation

A single random seed is not sufficient evidence.

The benchmark runner must support multiple independent seeds.

At minimum the framework must accept multiple seed values such as:

```text
42
101
2026
31415
```

The exact final seed set may be configured later.

Results must be available:

```text
per seed
and
aggregated
```

Aggregation must not silently mix incompatible benchmark/configuration versions.

---

## 29. Statistical Reporting

For multi-seed runs, Phase 6 should support:

```text
mean
median
standard deviation
minimum
maximum
```

for important metrics.

Where practical, provide confidence intervals for:

```text
recovery rate
incremental recovery
intervention rate
```

The method used must be explicit and reproducible.

Phase 6 must not make superiority claims from a single random run.

---

## 30. Per-Case Trace

Every benchmark case must produce a traceable record.

At minimum:

```text
case_id
scenario_id
strategy_name
strategy_version
dataset_version
scenario_version
configuration_version
seed
observable feature snapshot/reference
candidate actions
chosen action
outcome
recovered amount
latency
```

The trace schema must be extensible for later fields:

```text
diagnosis
probabilities
expected_values
recommendation
policy_result
execution
```

Phase 6 may leave later-phase fields absent or explicitly unavailable.

It must not fabricate them.

---

## 31. Benchmark Aggregation

Results must be aggregatable by:

```text
all cases
failure category/family
payment value bucket
action
customer behavior class
scenario family
scenario difficulty
seed
strategy
```

Aggregation must be deterministic.

Segment counts must be included so that small subgroups are visible rather than silently overinterpreted.

---

## 32. Failure-Mode Analysis Hooks

The evaluation foundation must make it possible to identify later:

```text
poor diagnosis segments
poor action-prediction segments
poor recovery segments
over-intervention segments
under-intervention segments
high-regret cases
```

Phase 6 does not implement Model A or Model B failure diagnosis.

It provides the grouping, filtering, trace, and aggregation structures required to analyze those failures later.

---

## 33. Benchmark Reproducibility Manifest

Every benchmark run must have a machine-readable manifest containing at minimum:

```text
benchmark_version
dataset_version
scenario_version
configuration_version
feature_schema_version
seed
case_count
strategy_versions
metric_version
```

Later phases may add:

```text
model_versions
policy_version
execution_version
```

The manifest must be sufficient to identify the exact benchmark inputs.

---

## 34. Benchmark Summary Artifacts

Each completed benchmark run should generate:

```text
benchmark_summary.json
benchmark_summary.md
```

The summary must contain:

```text
dataset version
scenario version
configuration version
seed(s)
case count
revenue at risk
revenue recovered
recovery rate
incremental recovery
intervention count
intervention rate
unnecessary intervention rate
escalation rate
stop rate
safety metrics
reliability metrics
baseline comparisons
```

The Markdown summary is presentation-oriented.

The JSON summary is authoritative machine-readable output.

---

## 35. Benchmark Integrity Rules

A benchmark version is immutable.

If results expose a weakness:

```text
document result
↓
identify cause
↓
improve system
↓
create new version where benchmark inputs changed
↓
re-run
```

Do not modify the benchmark simply because APRO performed poorly.

Do not tune later models against the held-out benchmark and then report the same run as untouched evidence.

Do not cherry-pick only successful cases.

---

## 36. No Cherry-Picking

The evaluation foundation must preserve all eligible cases.

A benchmark report must not silently exclude difficult or unsuccessful cases.

Any exclusion must be:

- defined before the run;
- recorded in configuration;
- counted;
- justified.

A curated demo dataset may exist later, but it is not a substitute for the frozen benchmark.

---

## 37. Simulator-Induced Bias Protection

The dataset/evaluation layer must not reward APRO by construction.

It must not:

- modify outcomes based on APRO decisions;
- remove scenarios on which APRO performs poorly;
- reveal hidden optimal actions to APRO;
- give APRO additional recovery opportunities;
- alter baseline fairness.

The causal relationship remains:

```text
Hidden Scenario State
        ↓
Independent Outcome Engine
        ↓
Action Outcome
```

while:

```text
Observable State
        ↓
APRO / Strategy
        ↓
Chosen Action
```

remains a separate path.

---

## 38. Benchmark Coverage Gates

The framework must be able to report coverage across:

```text
failure family
recoverability class
customer behavior class
payment value tier
payment method
scenario difficulty
candidate action
seed
```

The benchmark should expose any materially underrepresented category.

A benchmark should not be considered complete merely because the total case count reaches 1,000.

---

## 39. Phase 6 APIs / Components

The implementation should organize around clear module boundaries, such as:

```text
simulation/
    [existing Phase 5 components]

dataset/
    models
    generator
    manifest
    splitter
    feature_snapshot
    leakage_checks

evaluation/
    benchmark
    baselines
    metrics
    aggregation
    traces
    reports
```

Exact package names may differ if the existing repository architecture has a better equivalent.

Do not duplicate Phase 5 simulation functionality.

---

## 40. Persistence Boundary

Phase 6 does not require a production database for dataset artifacts unless the existing architecture genuinely needs persistence.

Prefer deterministic file-based or in-memory generation for v1 where practical.

Dataset/benchmark artifacts should be serializable and portable.

Do not couple benchmark correctness to PostgreSQL availability.

---

## 41. Performance Requirements

The implementation should be able to:

- generate the minimum 1,000-case benchmark;
- execute all initial baselines over the complete batch;
- collect per-case traces;
- aggregate all required metrics;
- reproduce the same run deterministically.

The framework should be designed so larger batches can be run without architectural changes.

A 10,000+ case stress run is desirable but not the minimum acceptance threshold.

---

## 42. Testing Requirements

Phase 6 must have automated tests for at least:

### Dataset generation

- correct record types;
- correct dataset metadata;
- correct version propagation;
- deterministic generation;
- multiple seeds;
- expected dataset sizes.

### Splitting

- train/validation/test counts;
- deterministic split;
- no scenario overlap across incompatible splits;
- temporal ordering when enabled;
- grouped leakage protection where applicable.

### Feature snapshot

- decision-time-only fields;
- forbidden future fields rejected;
- hidden truth absent from model-input records;
- feature schema version recorded.

### Benchmark dataset

- minimum-size generation;
- coverage reporting;
- versioned benchmark manifest;
- frozen dataset reproducibility;
- distribution-shift configuration.

### Baselines

- No Intervention;
- Always Retry;
- Static Rules;
- Global Action Rate.

Verify each baseline:

- selects valid actions;
- uses only permitted information;
- never reads hidden truth;
- produces deterministic results.

### Metrics

Test every required economic/intervention metric.

Test:

- zero-denominator behavior;
- integer monetary arithmetic;
- per-seed aggregation;
- strategy comparison;
- segment aggregation.

### Benchmark runner

- processes all cases;
- produces one trace per case/strategy;
- produces correct aggregate counts;
- reproduces identical results from identical inputs.

### Integrity

Test:

- benchmark immutability/versioning;
- manifest completeness;
- no cherry-picking;
- hidden truth unavailable to strategy/model inputs.

---

## 43. Manual Acceptance

Phase 6 must include a local manual acceptance run after automated tests pass.

The manual run must demonstrate:

```text
Phase 5 scenario generation
        ↓
dataset generation
        ↓
TRAINING / VALIDATION / TEST datasets
        ↓
held-out benchmark dataset
        ↓
run baselines
        ↓
collect outcomes
        ↓
calculate metrics
        ↓
produce per-case trace
        ↓
produce benchmark summary
```

Minimum manual benchmark:

```text
1,000 Recovery Cases
```

Minimum strategies:

```text
No Intervention
Always Retry
Static Rules
```

Show:

```text
case count
dataset_version
benchmark_version
seed(s)
revenue at risk
revenue recovered
recovery rate
intervention rate
baseline comparison
```

Also demonstrate:

```text
same manifest + same seeds
        ↓
same dataset
        ↓
same benchmark results
```

Do not run real Razorpay operations.

Do not use live customer/payment data.

---

## 44. Acceptance Criteria

Phase 6 is complete only when all of the following are true:

### AC-01 — Dataset Generation
Training, validation, held-out test, and benchmark datasets can be generated.

### AC-02 — Dataset Versioning
Every dataset has an explicit immutable version.

### AC-03 — Provenance
Scenario seed/version/configuration version propagate into dataset records.

### AC-04 — Feature Snapshotting
Decision-time observable features can be frozen with a feature schema version.

### AC-05 — Leakage Prevention
Automated checks prevent hidden/future/post-action information from entering model inputs.

### AC-06 — Train/Validation/Test Split
Deterministic non-overlapping splits are supported.

### AC-07 — Temporal Separation
Temporal split is supported where decision timestamps are available/applicable.

### AC-08 — Held-Out Protection
Held-out test data cannot be silently used by tuning/split-generation logic.

### AC-09 — Benchmark Dataset
A frozen benchmark of at least 1,000 Recovery Cases can be generated.

### AC-10 — Distribution Shift
A governed shifted benchmark configuration is supported.

### AC-11 — Multiple Seeds
Benchmark execution supports multiple independent seeds.

### AC-12 — Baseline Framework
No Intervention, Always Retry, and Static Rules are executable; Global Action Rate is supported.

### AC-13 — Baseline Fairness
Baselines receive equal observable information and recovery opportunities and cannot access hidden truth.

### AC-14 — Benchmark Runner
A complete benchmark batch can be processed automatically.

### AC-15 — Economic Metrics
Required revenue/recovery/intervention metrics are collected correctly.

### AC-16 — Decision Metrics
Optimal Action Rate, Regret, Expected Value Capture, and Action Selection Accuracy are supported.

### AC-17 — Safety/Reliability Metrics
The framework can collect required safety/reliability signals without inventing unavailable values.

### AC-18 — Per-Case Trace
Every benchmark case has a traceable evaluation record.

### AC-19 — Aggregation
Results can be aggregated by case, segment, strategy, and seed.

### AC-20 — Reproducibility
Identical benchmark inputs reproduce identical dataset and benchmark results.

### AC-21 — Benchmark Manifest
Every benchmark run records all required version/seed metadata.

### AC-22 — Benchmark Summary
Machine-readable and human-readable benchmark summaries are generated.

### AC-23 — Benchmark Integrity
Frozen benchmark versions cannot be silently mutated or cherry-picked.

### AC-24 — Phase Boundary
No Phase 7+ ML/model implementation or Phase 9+ decision/policy/execution implementation is present.

### AC-25 — Automated Tests
All Phase 0–5 regression tests remain passing, and Phase 6 targeted tests cover the foundation.

### AC-26 — Manual Acceptance
A local 1,000-case benchmark run successfully demonstrates dataset generation, baseline execution, metrics, traces, and reproducibility.

---

## 45. Phase Boundary: What Comes Next

Phase 6 creates the governed foundation for later intelligence.

### Phase 7 will own

```text
Failure Diagnosis
Model A
feature engineering specific to diagnosis
baseline model
candidate models
calibration
diagnosis evaluation
model versioning
prediction persistence
```

### Phase 8 will own

```text
Recovery Outcome Prediction
Model B
action-conditioned features
P(success | context, action)
candidate models
calibration
recovery prediction evaluation
model versioning
```

### Phase 9 will own

```text
Economic Decision Engine
ERV
action ranking
decision rationale
```

Phase 6 must not absorb these responsibilities.

---

## 46. Phase 6 Non-Goals

Phase 6 does not decide:

```text
which action APRO should take in production
```

It provides the environment in which later APRO components can be evaluated.

It also does not prove that APRO is better than baselines yet.

It makes that proof possible and reproducible.

---

## 47. Required Engineering Quality

The implementation must be:

- strongly typed;
- deterministic;
- modular;
- testable;
- serializable;
- versioned;
- explicit about unavailable metrics;
- safe against leakage;
- reproducible;
- independent of live payment execution.

Follow existing project conventions for Python, testing, typing, and package structure.

Do not introduce external network dependencies unless an architectural review explicitly requires them.

---

## 48. Final Readiness Gate

Before Phase 6 implementation is considered complete, verify:

```text
Phase 5 simulator          ✅ available
Dataset generation         ✅
Train/validation/test      ✅
Temporal split             ✅ where applicable
Feature snapshotting       ✅
Leakage checks             ✅
Benchmark dataset          ✅ 1,000+ cases
Multiple seeds             ✅
Baselines                  ✅
Baseline fairness          ✅
Metrics                    ✅
Per-case traces            ✅
Aggregation                ✅
Reproducibility            ✅
Benchmark manifest         ✅
Manual benchmark           ✅
Regression suite           ✅
```

No git staging, commit, or push is part of the implementation phase unless separately authorized.

---

## 49. Status

**Phase:** 6 — Dataset & Evaluation Foundation

**Specification Version:** 1.0

**Status:** Ready for Implementation

**Next phase after acceptance:** Phase 7 — Diagnosis Intelligence

Any material change to dataset methodology, split strategy, benchmark definition, baseline rules, feature-schema contract, leakage policy, or primary metrics must be documented and reviewed before implementation continues.
