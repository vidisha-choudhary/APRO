# APRO — Phase 7 Failure Diagnosis Intelligence Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 7 — Failure Diagnosis Intelligence (Model A)  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0

---

## 1. Purpose

Phase 7 implements APRO's first intelligence layer:

> **Model A — Failure Diagnosis**

Its responsibility is to transform a governed, decision-time observable payment-failure snapshot into a structured APRO failure diagnosis.

Conceptually:

```text
PHASE 6 GOVERNED MODEL INPUT
        ↓
Diagnosis feature representation
        ↓
Diagnosis baseline / candidate model
        ↓
Predicted failure category
        ↓
Diagnosis probabilities
        ↓
Confidence / uncertainty
        ↓
Auditable diagnosis result
```

Phase 7 must answer:

> What is the most likely normalized APRO failure category for this payment failure, based only on information available at decision time?

Phase 7 must NOT decide:

- whether recovery should be attempted;
- which recovery action should be chosen;
- how much money is expected to be recovered;
- whether an action is economically optimal;
- whether an action is policy-permitted;
- whether an action should be executed.

Those responsibilities belong to later phases.

---

## 2. Authoritative Source Hierarchy

Implementation must follow:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. Completed Phase 0–6 specifications and acceptance evidence
10. This document:
   `docs/PHASE_07_FAILURE_DIAGNOSIS_INTELLIGENCE_SPECIFICATION.md`

Phase 6 owns:

- dataset generation;
- feature snapshotting;
- split policy;
- leakage controls;
- benchmark foundation;
- baseline framework;
- metric/tracing infrastructure.

Phase 7 consumes those contracts. Do not create competing dataset or benchmark systems.

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

Current lineage:

```text
PHASE 1
Razorpay Failure/Webhook Validation
        ↓
PHASE 2
Persistence
        ↓
PHASE 3
Canonical Event Pipeline
        ↓
PHASE 4
Recovery Case Orchestration
        ↓
PHASE 5
Independent Simulation Engine
        ↓
PHASE 6
Dataset & Evaluation Foundation
        ↓
PHASE 7
Failure Diagnosis Intelligence (Model A)
        ↓
PHASE 8
Recovery Outcome Prediction (Model B)
        ↓
PHASE 9
Economic Decision Engine
```

Phase 7 must consume the Phase 6 model-input/evaluation-truth boundary.

---

## 4. Scope

### 4.1 In Scope

Phase 7 implements:

- normalized APRO diagnosis-label construction;
- diagnosis-specific feature preparation;
- diagnosis baselines;
- candidate diagnosis classifiers;
- training/validation/held-out test discipline;
- model selection;
- probability outputs;
- confidence/uncertainty representation;
- probability calibration;
- held-out diagnosis evaluation;
- diagnosis-specific metrics;
- confusion-matrix analysis;
- segment analysis;
- structured error analysis;
- prediction traces;
- model versioning;
- model artifact persistence/loading;
- experiment metadata;
- reproducibility;
- distribution-shift evaluation;
- diagnosis evaluation reports.

### 4.2 Explicitly Out of Scope

Phase 7 must NOT implement:

- action-conditioned recovery prediction;
- `P(success | context, action)`;
- recovery-value prediction;
- Expected Recovery Value;
- economic action ranking;
- policy engine;
- policy rules;
- execution framework;
- Razorpay outbound operations;
- customer outreach;
- real recovery actions;
- autonomous retry;
- production intervention;
- adaptive recovery loop;
- dashboard;
- final production decision loop;
- reinforcement learning;
- online learning;
- final submission/benchmark program.

Phase 7 predicts diagnosis only.

---

## 5. Core Diagnosis Contract

The diagnosis output must be structured and immutable.

Conceptually:

```text
DiagnosisResult
├── prediction_id
├── record_id
├── scenario_id
├── model_version
├── dataset_version
├── feature_schema_version
├── taxonomy_version
├── predicted_category
├── class_probabilities
├── confidence
├── uncertainty_state
├── evaluation_run_id
└── provenance
```

Required invariants:

```text
all probabilities ∈ [0,1]
probability sum ≈ 1
class order deterministic
predicted_category belongs to taxonomy
```

For evaluator-side records, actual truth may be attached separately:

```text
actual_category
```

but actual truth must never be passed to the diagnosis model.

---

## 6. Diagnosis Taxonomy

Use the established APRO normalized taxonomy:

```text
TRANSIENT_FAILURE
BANK_SIDE_FAILURE
CUSTOMER_SIDE_FAILURE
AUTHENTICATION_FAILURE
PAYMENT_METHOD_FAILURE
GATEWAY_FAILURE
TIMEOUT
UNKNOWN_FAILURE
```

Class order must be deterministic and versioned.

Do not silently redefine meanings.

If taxonomy changes materially, create a new:

```text
taxonomy_version
```

and require a new model version.

Provider metadata remains provider observation, not taxonomy itself.

---

## 7. Diagnosis Labels

Phase 6 evaluation truth may contain hidden simulator truth describing the true failure mechanism.

Phase 7 may construct the supervised diagnosis target from that truth.

Represent it as an explicit type such as:

```text
DiagnosisLabel
```

containing:

```text
failure_category
taxonomy_version
label_source
```

For synthetic data, `label_source` must identify governed simulator truth.

The label construction path must remain separate from model-input feature construction.

---

## 8. Strict Model-Input Boundary

The model must receive:

```text
ModelInputRecord
```

or a diagnosis-specific transformation of it.

It must NEVER receive:

```text
EvaluationTruthRecord
potential_outcomes
recoverability
customer_behavior_class
latent_customer_intent
latent_bank_condition
true_failure_mechanism
best_achievable_action
best_achievable_value
realized_outcome
post_action_result
future information
```

Do not pass a complete `DatasetRecord` into model fitting or prediction.

Preferred:

```text
GovernedDataset
      ↓
ModelInputRecord
      ↓
DiagnosisFeatureBuilder
      ↓
Model A
```

Labels are joined only in the training/evaluation layer.

---

## 9. Decision-Time Feature Contract

Features must be available at the payment-failure decision point.

Allowed examples:

### Payment

```text
amount
currency
payment_method
payment_value_tier
```

### Provider failure metadata

```text
failure_code
failure_reason
failure_source
failure_step
failure_description
```

### Historical context

```text
previous_payment_count
previous_success_count
previous_failure_count
previous_recovery_count
previous_retry_success
previous_payment_link_success
```

only when strictly pre-decision.

### Temporal context

```text
hour
weekday
time_since_previous_attempt
time_since_previous_success
```

### Attempt context

```text
current_attempt_number
historical_failure_count
```

No future/post-action information may be used.

---

## 10. Missing and Noisy Provider Data

Feature preparation must explicitly handle:

- missing error code;
- missing reason;
- missing source;
- missing step;
- missing description;
- empty strings;
- null values;
- unseen categorical values.

Missingness must not be converted into a fake diagnosis.

Where useful, missingness may be represented explicitly.

Never use default labels merely because a provider field is missing.

---

## 11. Diagnosis Feature Schema

Create a versioned diagnosis feature schema:

```text
feature_schema_version
```

Each feature definition should record, where practical:

```text
name
type
source
transformation
allowed range/category
missing behavior
decision-time availability
leakage status
```

Material feature-definition changes require a new schema version.

A trained model must declare the schema version it expects.

---

## 12. Feature Engineering

Support deterministic diagnosis-specific features such as:

```text
failure_code_present
failure_reason_present
failure_source_present
failure_step_present
failure_description_length
historical_failure_rate
historical_success_rate
historical_recovery_rate
attempt_count
time_since_previous_attempt
time_since_previous_success
payment_value_tier
payment_method
hour_bucket
weekday
```

Any learned transformation must be fit only on TRAINING data and then frozen for validation/test.

Do not compute aggregate historical statistics from validation or held-out test data.

---

## 13. Text Features

Simple local text features are permitted where justified:

```text
normalized tokens
keyword indicators
length/count features
TF-IDF-style features
```

Do not introduce a hosted LLM simply to classify failure descriptions.

Do not transmit payment payloads to external services.

Do not add Gemini or other network AI dependencies.

A deterministic local pipeline is preferred for Phase 7 v1.

---

## 14. Diagnosis Baselines

Implement at least:

### Baseline 0 — Majority Class

Predict the most frequent TRAINING diagnosis class.

### Baseline 1 — Provider Rule Baseline

A fixed, versioned mapping based only on observable provider metadata.

Illustrative structure:

```text
timeout-like evidence
    → TIMEOUT

authentication evidence
    → AUTHENTICATION_FAILURE

bank-side evidence
    → BANK_SIDE_FAILURE

gateway evidence
    → GATEWAY_FAILURE

otherwise
    → UNKNOWN_FAILURE
```

The exact rule configuration must be explicit and versioned.

### Baseline 2 — Historical Conditional Baseline

A deterministic empirical baseline calculated strictly from permitted TRAINING observations.

It must not inspect hidden truth.

### Baseline 3 — Simple Statistical Classifier

A lightweight statistical model using the same model-input feature boundary.

Baselines are comparison references, not the final APRO intelligence claim.

---

## 15. Candidate Model Interface

Implement a model interface supporting at minimum:

```text
fit(training_features, training_labels)
predict(model_input)
predict_proba(model_input)
```

Optionally:

```text
evaluate(validation_dataset)
```

The production-facing API must not require hidden truth.

Candidate algorithms may include lightweight approved classifiers such as:

```text
logistic regression
decision tree
random forest
gradient boosting
```

or another justified tabular classifier.

Use the smallest dependency set that provides credible performance.

---

## 16. Training Discipline

Training may use only:

```text
DatasetType.TRAINING
```

Validation may be used for:

```text
candidate comparison
hyperparameter selection
threshold decisions
calibration decisions
```

Held-out test/benchmark may NOT be used for:

```text
fitting
feature selection
model selection
hyperparameter tuning
calibration fitting
threshold tuning
```

Training APIs should reject held-out/test data explicitly.

---

## 17. Class Imbalance

Report diagnosis class counts and detect imbalance.

Permitted remedies:

```text
class weights
balanced training sampling
```

where justified.

Never rebalance validation/test evaluation data.

Report class support alongside performance.

---

## 18. Model Selection

Model selection must happen using TRAINING/VALIDATION only.

Candidate selection criteria should consider:

```text
macro F1
balanced accuracy
log loss
calibration quality
minority-class recall
```

The primary selection metric must be explicit and versioned.

Do not select the final model using held-out test performance.

---

## 19. Probability Output

For every prediction, provide probabilities for all eight classes.

Required:

```text
probabilities sum ≈ 1
all values ∈ [0,1]
deterministic class ordering
```

Expose:

```text
predicted_category
class_probabilities
```

separately.

---

## 20. Confidence and Uncertainty

Define confidence explicitly.

A valid v1 definition may be:

```text
confidence = max(class_probability)
```

or another justified deterministic/calibrated definition.

Support uncertainty states such as:

```text
HIGH_CONFIDENCE
MEDIUM_CONFIDENCE
LOW_CONFIDENCE
ABSTAIN
```

only if thresholds are explicitly defined.

Do not claim uncertainty calibration without evidence.

A low-confidence diagnosis does not trigger recovery action.

---

## 21. Calibration

Evaluate probability calibration.

At minimum support:

```text
log loss
Brier score
expected calibration error
reliability information
```

Where justified, implement:

```text
Platt-style calibration
isotonic calibration
```

Calibration must be fit using TRAINING/VALIDATION only.

Held-out test is evaluation-only.

---

## 22. Held-Out Evaluation

The final held-out evaluation must occur only after:

```text
features frozen
model selected
hyperparameters frozen
calibration method frozen
thresholds frozen
```

Every test evaluation must identify:

```text
model_version
dataset_version
feature_schema_version
taxonomy_version
evaluation_run_id
```

Do not tune against held-out results and reuse that same run as the final claim.

---

## 23. Diagnosis Metrics

Implement:

```text
Accuracy
Balanced Accuracy
Macro Precision
Macro Recall
Macro F1
Weighted F1
Log Loss
Brier Score
```

Also provide:

```text
per-class precision
per-class recall
per-class F1
support
top-1 accuracy
top-2 accuracy
```

where applicable.

---

## 24. Confusion Matrix

Generate a deterministic confusion matrix for held-out evaluation.

Requirements:

- fixed taxonomy order;
- auditable row/column labels;
- counts preserved;
- traceable to model/dataset/schema/taxonomy/evaluation-run versions.

The final report should identify strongest confusions and underdiagnosed classes.

---

## 25. Segment Evaluation

Report diagnosis metrics across governed segments including:

```text
scenario family
payment value tier
payment method
scenario difficulty
seed
```

Diagnosis-specific segments may include:

```text
failure_code_present
failure_description_present
high vs low historical failure count
```

Always report segment support counts.

Do not overinterpret tiny segments.

---

## 26. Error Analysis

Create evaluator-side structures for:

```text
misclassified cases
actual category
predicted category
probability distribution
confidence
observable feature reference
```

Actual category may be available to post-hoc evaluation/error analysis.

It must never flow into Model A as an input.

Support identification of:

```text
high-confidence wrong predictions
low-confidence predictions
systematic class confusions
missing-metadata failures
distribution-shift failures
```

---

## 27. Prediction Trace

Every evaluated prediction must record:

```text
prediction_id
record_id
scenario_id
dataset_version
feature_schema_version
taxonomy_version
model_version
predicted_category
class_probabilities
confidence
uncertainty_state
evaluation_run_id
```

Evaluator-only truth may be stored separately.

---

## 28. Model Versioning

Every Model A artifact must record:

```text
model_name
model_version
training_dataset_version
feature_schema_version
taxonomy_version
training_seed
algorithm
hyperparameter reference/hash
calibration_version
created_at
```

Material model changes require a new model version.

Do not silently overwrite evaluated models.

---

## 29. Model Artifact

Persist a portable artifact containing:

```text
trained parameters/weights
feature schema metadata
taxonomy metadata
calibration parameters
model provenance
version metadata
```

The artifact must load for inference/evaluation without retraining.

Do not build a production model-serving platform.

---

## 30. Benchmark Integration

Reuse the Phase 6 evaluation foundation.

Model A evaluation must run using existing:

```text
HELD_OUT_TEST
BENCHMARK
```

datasets and Phase 6 benchmark/evaluation infrastructure where applicable.

Do not create a second benchmark engine.

Do not modify Phase 6 benchmark semantics.

---

## 31. Distribution Shift Evaluation

Evaluate the selected Model A against the governed Phase 6 shifted benchmark.

Compare:

```text
in-distribution
vs
shifted distribution
```

at minimum for:

```text
macro F1
macro recall
log loss
calibration metric(s)
```

Do not retune the final model on shifted benchmark outcomes unless a new explicit experiment changes the training designation.

---

## 32. Experiment Configuration

Record for every training/evaluation run:

```text
experiment_id
model_version
dataset_version
feature_schema_version
taxonomy_version
training_seed
split configuration
algorithm
hyperparameters
calibration method
primary selection metric
```

Configuration must be serializable.

Material changes require a new experiment/model version.

---

## 33. Reproducibility

Given identical:

```text
training dataset
feature schema
taxonomy
algorithm/configuration
training seed
runtime/dependency configuration
```

the resulting model outputs must be canonically reproducible.

Explicitly control all supported library random states.

Do not depend on:

```text
global random state
system time
unordered iteration
process scheduling
```

for model semantics.

---

## 34. Artifact Compatibility

A model artifact must declare compatibility with:

```text
feature_schema_version
taxonomy_version
```

Loading an incompatible artifact must fail explicitly.

Do not silently transform an incompatible input schema.

---

## 35. Reporting

Generate:

```text
diagnosis_evaluation.json
diagnosis_evaluation.md
confusion_matrix.json
prediction_trace.jsonl
model_manifest.json
```

The JSON result is authoritative machine-readable output.

Reports must distinguish:

```text
training
validation
held-out
distribution-shift
```

and must include:

```text
model version
dataset version
feature schema version
taxonomy version
training configuration
class distribution
baseline results
candidate results
selected model
held-out metrics
calibration metrics
confusion matrix
segment metrics
distribution-shift results
error-analysis summary
reproducibility metadata
```

Do not fabricate unavailable metrics.

---

## 36. Evaluation Integrity

Phase 7 must preserve the following causality:

```text
Observable Model Input
        ↓
Model A
        ↓
Diagnosis Prediction
```

while:

```text
Hidden Evaluation Truth
        ↓
Label Construction / Post-Hoc Evaluation
```

remains separate.

Never create a feature that is a disguised hidden label.

Examples of prohibited leakage:

```text
recoverability_proxy derived from hidden state
future outcome encoding
potential outcome encoding
true failure mechanism copied into features
post-action success flag
```

---

## 37. Manual Acceptance

After automated tests pass, run a local end-to-end Model A acceptance test.

Minimum flow:

```text
Phase 6 TRAINING dataset
        ↓
diagnosis label construction
        ↓
diagnosis feature preparation
        ↓
baseline evaluation
        ↓
candidate model training
        ↓
validation model selection
        ↓
probability calibration
        ↓
held-out evaluation
        ↓
confusion matrix
        ↓
segment analysis
        ↓
prediction traces
        ↓
distribution-shift evaluation
        ↓
diagnosis report
```

The run must show:

```text
model_version
dataset_version
feature_schema_version
taxonomy_version
training seed
class distribution
selected model
held-out Accuracy
held-out Macro F1
held-out Log Loss
calibration metric(s)
confusion matrix
distribution-shift result
```

Repeat the evaluation from the same frozen artifacts and confirm canonical-equivalent predictions/results.

No live Razorpay operations.

No outbound network calls.

No live customer/payment data.

---

## 38. Testing Requirements

Create automated tests covering:

### Taxonomy

- all eight classes;
- deterministic ordering;
- taxonomy versioning;
- invalid taxonomy rejection.

### Labels

- correct label construction;
- invalid/missing labels rejected;
- labels unavailable to feature builder.

### Features

- decision-time features;
- provider metadata missingness;
- hidden truth rejection;
- future-field rejection;
- schema version enforcement.

### Baselines

- majority class;
- provider rules;
- historical conditional;
- simple statistical baseline.

### Training

- training-only enforcement;
- deterministic fitting;
- class distribution reporting;
- held-out rejection.

### Model

- fit/predict/predict_proba;
- probability validity;
- deterministic class order;
- artifact serialization/loading.

### Calibration

- calibration training uses allowed data only;
- held-out calibration is rejected;
- calibrated probabilities remain valid.

### Metrics

- all required classification metrics;
- log loss;
- Brier;
- calibration;
- per-class metrics;
- confusion matrix;
- edge cases.

### Held-Out Evaluation

- model selection before test;
- no test fitting;
- provenance recorded.

### Distribution Shift

- shifted benchmark execution;
- comparison metrics;
- no hidden retuning.

### Reproducibility

- same frozen inputs → same predictions;
- same artifact → same evaluation;
- canonical equivalent outputs.

### Reporting

- JSON;
- Markdown;
- manifest;
- prediction traces.

---

## 39. Acceptance Criteria

Phase 7 is complete only when:

### AC-01 — Taxonomy
All eight diagnosis classes are supported.

### AC-02 — Label Construction
Diagnosis labels are explicitly derived from Phase 6 evaluation truth.

### AC-03 — Model Input Separation
Model A receives only decision-time observable inputs.

### AC-04 — Feature Schema
Diagnosis features have a versioned reproducible schema.

### AC-05 — Leakage Prevention
Hidden/future/post-action information cannot enter model inputs.

### AC-06 — Training Discipline
Model training is restricted to TRAINING data.

### AC-07 — Validation Discipline
Model selection/calibration decisions use TRAINING/VALIDATION only.

### AC-08 — Held-Out Protection
HELD_OUT_TEST/BENCHMARK cannot be used for fitting or tuning.

### AC-09 — Baselines
All required diagnosis baselines are implemented and evaluated.

### AC-10 — Candidate Model
At least one credible candidate diagnosis classifier exists.

### AC-11 — Probability Output
Valid probability distribution over all diagnosis classes is produced.

### AC-12 — Confidence
Confidence and uncertainty are explicitly defined and traceable.

### AC-13 — Calibration
Calibration is evaluated and implemented where justified.

### AC-14 — Metrics
All required diagnosis metrics are produced.

### AC-15 — Confusion Matrix
Held-out evaluation provides an auditable confusion matrix.

### AC-16 — Segment Evaluation
Diagnosis metrics can be evaluated by required segments.

### AC-17 — Error Analysis
Misclassifications and confidence/probability traces are inspectable.

### AC-18 — Model Versioning
Every model artifact has explicit version/provenance metadata.

### AC-19 — Reproducibility
Frozen training/evaluation inputs reproduce equivalent predictions/results.

### AC-20 — Distribution Shift
Model A is evaluated on governed shifted data.

### AC-21 — Prediction Trace
Every evaluated prediction is traceable.

### AC-22 — Reports
Machine-readable and human-readable diagnosis reports exist.

### AC-23 — Artifact Loading
A trained model artifact loads without retraining.

### AC-24 — Benchmark Integrity
No hidden-truth model input or held-out cherry-picking occurs.

### AC-25 — Phase Boundary
No Phase 8 recovery prediction, Phase 9 economic decisioning, policy, or execution logic is implemented.

### AC-26 — Automated Tests
All Phase 0–6 regression tests remain green and Phase 7 targeted tests cover Model A.

### AC-27 — Manual Acceptance
A local end-to-end Model A run succeeds with reproducible held-out results.

---

## 40. Expected Module Boundaries

A clean implementation may use:

```text
src/apro/diagnosis/
    __init__.py
    enums.py
    models.py
    labels.py
    features.py
    baselines.py
    models/
        __init__.py
        interface.py
        logistic.py
        ...
    calibration.py
    evaluation.py
    traces.py
    artifacts.py
    reports.py
```

Exact names may differ where the existing architecture has a better equivalent.

Do not duplicate Phase 6 abstractions.

---

## 41. Persistence Boundary

Phase 7 does not require production database persistence.

Prefer portable model artifacts and evaluation outputs.

Do not create database tables merely for experiments.

---

## 42. Dependency Policy

Use the smallest justified ML dependency set.

Before adding dependencies, verify:

- necessity;
- Python compatibility;
- maintenance;
- reproducibility;
- licensing/usage implications.

Do not introduce heavyweight frameworks without clear need.

Do not introduce hosted AI services.

---

## 43. Quality Requirements

Run:

```text
pytest
ruff check .
ruff format --check .
mypy src
```

All existing Phase 0–6 tests must remain passing.

Do not weaken existing tests.

Do not modify the locked Phase 7 specification during implementation.

---

## 44. Phase Boundary Safety Check

Before completion confirm explicitly:

```text
NO Model B
NO P(success | context, action)
NO recovery prediction
NO ERV
NO economic action ranking
NO policy engine
NO execution
NO Razorpay outbound operation
NO customer outreach
NO production intervention
NO adaptive recovery loop
NO dashboard
NO Phase 15 benchmark program
```

---

## 45. Git Rules

During implementation:

- do not commit;
- do not push;
- preserve intentionally pre-existing uncommitted files;
- do not modify unrelated files.

The final report must include:

```text
git status --short --untracked-files=all
git diff --stat
```

and identify every modified/untracked file.

---

## 46. Final Readiness Gate

Phase 7 is ready for architecture review only when:

```text
Diagnosis taxonomy               ✅
Diagnosis labels                 ✅
Decision-time feature schema     ✅
Leakage protection               ✅
Training/validation/test         ✅
Baselines                        ✅
Candidate Model A                ✅
Probability outputs              ✅
Calibration                      ✅
Held-out evaluation              ✅
Diagnosis metrics                ✅
Confusion matrix                 ✅
Segment analysis                 ✅
Error analysis                  ✅
Prediction traces                ✅
Model artifact                   ✅
Artifact loading                 ✅
Distribution shift               ✅
Reproducibility                  ✅
Reporting                        ✅
Automated tests                  ✅
Manual acceptance                ✅
Phase boundary                   ✅
```

---

## 47. Final Report Requirements

After implementation and verification, return:

### A. IMPLEMENTATION SUMMARY
Describe the final Model A architecture.

### B. FILES CREATED
List every new file.

### C. FILES MODIFIED
List every existing file modified and why.

### D. TAXONOMY / LABELS
Describe taxonomy and label provenance.

### E. FEATURE CONTRACT
Describe the final diagnosis feature schema and leakage controls.

### F. BASELINES
List each baseline and its measured results.

### G. MODEL SELECTION
Report candidates, selection criterion, validation results, and chosen model.

### H. CALIBRATION
Report calibration method, fitting data, and metrics.

### I. HELD-OUT EVALUATION
Report final held-out metrics and confusion matrix.

### J. SEGMENT / SHIFT EVALUATION
Report segment and distribution-shift results.

### K. REPRODUCIBILITY
Show equivalent results from identical frozen inputs/artifacts.

### L. ARTIFACTS
Provide model artifact and manifest paths.

### M. TEST RESULTS
Return exact:
- Phase 7 targeted tests;
- full regression;
- Ruff;
- formatter;
- Mypy.

### N. MANUAL ACCEPTANCE
Describe the end-to-end local run and exact observed results.

### O. PHASE BOUNDARY
Confirm no Phase 8+ implementation.

### P. GIT STATE
Return exact:

```text
git status --short --untracked-files=all
```

Confirm:

```text
0 staged
0 commits
0 pushes
```

### Q. SPECIFICATION INTEGRITY
Confirm:

```text
docs/PHASE_07_FAILURE_DIAGNOSIS_INTELLIGENCE_SPECIFICATION.md
```

was not modified.

### R. ARCHITECTURAL ISSUES
Return:

```text
NONE
```

if none. Otherwise explain the issue and STOP.

### S. FINAL STATUS

Return exactly one:

```text
PHASE 7 IMPLEMENTATION COMPLETE — READY FOR ARCHITECTURE REVIEW
```

or:

```text
PHASE 7 IMPLEMENTATION BLOCKED — ARCHITECTURE DECISION REQUIRED
```

STOP.

---

## 48. Non-Negotiable Principle

The diagnosis system must preserve:

```text
Decision-Time Observable Context
             ↓
          Model A
             ↓
Diagnosis Category + Probabilities
```

and separately:

```text
Hidden Evaluation Truth
        ↓
Training Label / Evaluation
```

Hidden truth may guide label construction and post-hoc analysis.

It must never become a feature.

Model A must help APRO **understand the failure**.

It must not yet decide **what APRO should do about it**.
