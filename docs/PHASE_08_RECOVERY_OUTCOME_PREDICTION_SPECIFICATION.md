# APRO — Phase 8 Recovery Outcome Prediction Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 8 — Recovery Outcome Prediction (Model B)  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0

## 1. Purpose

Phase 8 implements **Model B — Recovery Outcome Prediction**.

Model B estimates the likely outcome of a **specific recovery action under a specific decision-time payment context**.

```text
Observable Context
      +
Selected Action
      ↓
    Model B
      ↓
P(success | context, action)
      +
Predicted Outcome State
      +
Predicted Recovered Amount
```

Model B predicts outcomes. It does not select actions, optimize economics, enforce policy, or execute recovery.

## 2. Authoritative Sources

Follow, in order:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. Completed Phase 0–7 specifications and acceptance evidence
10. `docs/PHASE_08_RECOVERY_OUTCOME_PREDICTION_SPECIFICATION.md`

Reuse Phase 6 dataset/evaluation infrastructure and Phase 7 diagnosis outputs. Do not create competing systems.

If a material conflict exists:

```text
STOP → document → report → architecture decision
```

## 3. Phase Lineage

```text
Phase 1  Webhook validation
Phase 2  Persistence
Phase 3  Canonical event pipeline
Phase 4  Recovery case orchestration
Phase 5  Independent simulation
Phase 6  Dataset/evaluation foundation
Phase 7  Failure diagnosis (Model A)
Phase 8  Recovery outcome prediction (Model B)
Phase 9  Economic decision engine
```

## 4. Scope

### In scope

- action-conditioned outcome labels;
- action taxonomy/versioning;
- Model B features;
- optional frozen Model A outputs;
- training/validation/held-out discipline;
- baselines;
- candidate outcome classifiers/regressors;
- success probabilities;
- outcome states;
- bounded recovered-amount predictions;
- calibration;
- uncertainty;
- per-action evaluation;
- potential-outcome evaluation;
- segment analysis;
- distribution-shift evaluation;
- error analysis;
- prediction traces;
- model versioning;
- portable artifacts;
- reproducibility;
- reports.

### Explicitly out of scope

- action selection;
- optimal-action ranking;
- ERV;
- utility/economic optimization;
- policy/guardrails;
- recovery execution;
- Razorpay outbound APIs;
- Payment Link creation;
- retries/outreach;
- autonomous intervention;
- production serving;
- reinforcement learning;
- bandits;
- online learning;
- Phase 9 logic.

## 5. Core Prediction Contract

Use an immutable, serializable result such as:

```text
OutcomePrediction
├── prediction_id
├── record_id
├── scenario_id
├── action
├── model_version
├── dataset_version
├── feature_schema_version
├── action_schema_version
├── diagnosis_model_version (optional)
├── predicted_success_probability
├── predicted_outcome_state
├── predicted_recovered_amount
├── confidence
├── uncertainty_state
├── evaluation_run_id
└── provenance
```

Invariants:

```text
0 <= success_probability <= 1
0 <= predicted_recovered_amount <= payment_amount
action is supported
ordering is deterministic
```

## 6. Action Taxonomy

The initial action space is:

```text
RETRY
PAYMENT_LINK
OUTREACH
STOP
ESCALATE
```

Use deterministic action order and an explicit `action_schema_version`.

Do not silently change action semantics.

## 7. Outcome Taxonomy

At minimum:

```text
SUCCESS
FAILURE
```

Preserve additional governed simulator outcome states where the Phase 5 contract defines them. Do not silently collapse meaningful states.

## 8. Causal Boundary

Required model relationship:

```text
Decision-Time Observable Context + Action → Model B → Outcome under that Action
```

Forbidden model inputs:

```text
EvaluationTruthRecord
potential_outcomes
realized current-action outcome
recoverability
customer_behavior_class
latent_customer_intent
latent_bank_condition
best_achievable_action
best_achievable_value
post-action results
future information
```

Potential outcomes may be used for governed label construction and evaluator-side counterfactual metrics only.

## 9. Model Input

Model B may consume:

```text
Phase 6 ModelInputRecord
+
selected action
+
optional frozen Phase 7 Model A output
```

Permitted Model A fields:

```text
predicted diagnosis
diagnosis class probabilities
diagnosis confidence
diagnosis uncertainty state
diagnosis model version
```

Do not pass complete dataset records containing hidden evaluation truth.

## 10. Action-Conditioned Training Labels

Construct a typed `RecoveryOutcomeLabel` from the governed simulator truth for the action being modeled.

Conceptually:

```text
Scenario S
 ├── RETRY        → outcome label
 ├── PAYMENT_LINK → outcome label
 ├── OUTREACH     → outcome label
 ├── STOP         → outcome label
 └── ESCALATE     → outcome label
```

Each label should retain:

```text
scenario_id
action
outcome_state
recovered_amount
label_source
dataset_version
```

Labels must be constructed separately from features.

## 11. Potential Outcomes

Phase 8 is the first intelligence phase allowed to use simulator potential outcomes in evaluator-side analysis.

Allowed evaluator use:

```text
predicted outcome under action A
vs
simulated potential outcome under action A
```

Evaluator-only metrics may include:

```text
action-wise regret
oracle gap
success-rate lift over baseline
recovery-value lift over baseline
```

These metrics must never become training features or an action policy.

## 12. Feature Schema

Create a versioned feature schema, for example:

```text
recovery-outcome-feature-v1
```

Record:

```text
feature name
type
source
transformation
missing-value behavior
decision-time availability
leakage status
feature_schema_version
action_schema_version
```

Material feature changes require a new schema version.

## 13. Permitted Context Features

Payment:

```text
amount
currency
payment_method
payment_value_tier
```

Failure metadata:

```text
failure_code
failure_reason
failure_source
failure_step
failure_description
presence indicators
```

Pre-decision historical context:

```text
previous_payment_count
previous_success_count
previous_failure_count
previous_recovery_count
previous_retry_success
previous_payment_link_success
historical_failure_rate
historical_success_rate
historical_recovery_rate
```

Temporal/attempt context:

```text
hour
weekday
time_since_previous_attempt
time_since_previous_success
current_attempt_number
historical_failure_count
```

Optional frozen Model A features:

```text
predicted category
class probabilities
confidence
uncertainty state
```

## 14. Action Encoding

The model must receive the chosen action explicitly, e.g.:

```text
action_one_hot
```

The same context under different actions must remain distinguishable:

```text
(C, RETRY) != (C, PAYMENT_LINK)
```

Prefer a shared action-conditioned model unless a separate design is justified.

## 15. Missing Data

Support:

- null values;
- empty strings;
- missing provider metadata;
- unseen categorical values;
- missing historical statistics;
- missing optional Model A output.

Missingness must not become a fabricated outcome label.

## 16. Baselines

Implement at least:

### Global Action Rate

Empirical action-level success/recovery behavior from legitimate TRAINING observations.

Requirements:

- training-only fit;
- explicit unfitted failure;
- no potential-outcome inspection.

### Action-Stratified Historical Baseline

Condition empirical behavior on permitted historical context plus action.

### Static Outcome Rule Baseline

A deterministic, explicit, versioned action-conditioned rule.

### Simple Statistical Baseline

A lightweight action-conditioned classifier/regressor using the same observable information boundary.

## 17. Candidate Model Interface

Preferred public training path:

```text
fit_on_dataset(training_dataset)
```

with internal fitting machinery separated from governed dataset access.

Inference:

```text
predict(context, action)
predict_proba(context, action)
```

Amount:

```text
predict_recovered_amount(context, action)
```

Candidate models may include lightweight methods such as:

```text
logistic regression
decision tree
random forest
gradient boosting
```

Use the smallest justified dependency set.

## 18. Success vs Amount

Prefer separate semantic outputs:

```text
P(success | context, action)
```

and:

```text
E[recovered_amount | context, action]
```

Do not collapse them into an ambiguous scalar.

Enforce:

```text
0 <= predicted_recovered_amount <= payment_amount
```

Report unavailable amount predictions honestly rather than fabricating them.

## 19. Training Discipline

Only `DatasetType.TRAINING` may be used for fitting.

Validation may be used for:

```text
model selection
hyperparameter selection
calibration
threshold selection
```

`VALIDATION`, `HELD_OUT_TEST`, and `BENCHMARK` must be rejected by training APIs.

Held-out test and benchmark are never for fitting or tuning.

## 20. Multiple Action Rows

A scenario may produce one governed row per action.

Preserve parent `scenario_id`.

Do not treat the five action rows as five unrelated scenarios for scenario-level metrics.

Action-level metrics may evaluate each action row independently.

## 21. Calibration

Evaluate probability calibration:

```text
overall
per action
```

Minimum:

```text
Log Loss
Brier Score
Expected Calibration Error
```

Calibration fitting is TRAINING/VALIDATION only.

Never calibrate on held-out outcomes.

## 22. Uncertainty

Expose:

```text
confidence
uncertainty_state
```

A valid v1 confidence can be:

```text
max(success_probability, 1 - success_probability)
```

unless another justified definition is used.

Do not claim calibrated prediction intervals without evidence.

## 23. Classification Metrics

Report:

```text
Accuracy
Balanced Accuracy
Precision
Recall
F1
Log Loss
Brier Score
ECE
```

ROC-AUC/PR-AUC may be reported where meaningful.

Report per-action metrics and macro averages across actions.

## 24. Recovery Amount Metrics

Where amount prediction exists:

```text
MAE
RMSE
Median Absolute Error
```

Optionally normalized MAE.

Report overall and per action/value tier.

## 25. Segment Evaluation

Evaluate across:

```text
action
scenario family
payment method
payment value tier
scenario difficulty
diagnosis category
diagnosis confidence bucket
seed
```

Useful additional segments:

```text
provider metadata present/missing
high vs low historical failure count
```

Always include support counts.

## 26. Distribution Shift

Evaluate against at least one governed Phase 6 shifted benchmark.

Compare in-distribution vs shifted results for:

```text
success prediction quality
amount error
calibration
per-action performance
```

Do not retune against shifted benchmark results.

## 27. Error Analysis

Create evaluator-side error records for:

```text
incorrect success prediction
high-confidence incorrect prediction
large amount error
action-specific systematic failure
segment-specific failure
shift degradation
```

Retain:

```text
record_id
scenario_id
action
actual outcome
predicted outcome
predicted probability
predicted amount
confidence
observable feature reference
model version
```

Actual simulator truth remains evaluator-side.

## 28. Prediction Traces

Each evaluation prediction should record:

```text
prediction_id
record_id
scenario_id
action
dataset_version
feature_schema_version
action_schema_version
diagnosis_model_version (optional)
model_version
predicted_success_probability
predicted_outcome_state
predicted_recovered_amount
confidence
uncertainty_state
evaluation_run_id
```

Prediction IDs must be deterministic.

## 29. Model Versioning

Every artifact records:

```text
model_name
model_version
training_dataset_version
feature_schema_version
action_schema_version
diagnosis_model_version (if used)
taxonomy_version (if relevant)
training_seed
algorithm
hyperparameter reference/hash
calibration_version
created_at
```

Use actual creation timestamps but exclude wall-clock time from deterministic artifact identity.

## 30. Artifact Compatibility

Loading must verify:

```text
feature_schema_version
action_schema_version
taxonomy_version
diagnosis_model_version, when applicable
```

Incompatibility must fail explicitly.

No silent schema adaptation.

## 31. Reproducibility

Identical frozen:

```text
training dataset
feature schema
action schema
Model A artifact, if used
algorithm/configuration
training seed
runtime/dependencies
```

must produce canonically equivalent results.

Repeated inference must preserve:

```text
prediction_id
action
success probability
outcome state
recovered amount
confidence
uncertainty
```

Do not use UUID4 or wall-clock prediction time in prediction identity.

## 32. Artifact Persistence

Persist:

```text
trained parameters
feature schema
action schema
taxonomy metadata
diagnosis dependency/version if used
calibration parameters
model provenance
version metadata
```

The artifact must load without retraining.

Do not build production serving infrastructure.

## 33. Evaluation Integration

Reuse Phase 6 and Phase 7 infrastructure.

Evaluate through governed:

```text
VALIDATION
HELD_OUT_TEST
BENCHMARK
```

with strict training separation.

Do not create a competing benchmark runner.

## 34. Reporting

Suggested outputs:

```text
recovery_outcome_evaluation.json
recovery_outcome_evaluation.md
recovery_outcome_confusion.json
recovery_outcome_trace.jsonl
recovery_outcome_model_manifest.json
```

Reports must separate:

```text
success prediction
recovery amount prediction
per-action results
segments
potential-outcome evaluation
distribution shift
calibration
reproducibility
```

Never present Model B as an action-selection policy.

## 35. Leakage Protection

Reject or prevent:

```text
potential_outcomes
realized_outcome
recoverability
customer_behavior_class
latent_customer_intent
latent_bank_condition
best_achievable_action
best_achievable_value
current-action future result
post_action_result
future timestamps
future customer behavior
future payment attempts
```

Historical features are permitted only when available before the decision.

## 36. Failure Handling

Fail explicitly for:

- empty training data;
- missing outcome labels;
- unsupported action;
- unsupported action schema;
- invalid probabilities;
- recovered amount outside bounds;
- inconsistent action order;
- held-out training attempt;
- missing diagnosis artifact when required;
- incompatible artifact;
- missing feature schema;
- inconsistent scenario/action alignment.

Do not silently drop actions, substitute actions, or fabricate outcomes.

## 37. Testing Requirements

Create tests covering:

### Taxonomy
- all five actions;
- deterministic order;
- action schema version.

### Labels
- action-conditioned construction;
- scenario/action alignment;
- potential-outcome isolation;
- provenance.

### Features
- decision-time boundary;
- action encoding;
- missing metadata;
- optional Model A output;
- hidden-truth rejection;
- future-data rejection.

### Training governance
- TRAINING allowed;
- VALIDATION rejected;
- HELD_OUT_TEST rejected;
- BENCHMARK rejected.

### Baselines
- global action rate;
- action-stratified historical;
- static rule;
- simple statistical baseline.

### Candidate model
- fit/predict;
- predict_proba;
- action sensitivity;
- probability validity;
- amount bounds.

### Calibration
- TRAINING/VALIDATION only;
- held-out rejection;
- per-action calibration.

### Evaluation
- model selection on validation;
- frozen held-out evaluation;
- per-action metrics;
- potential-outcome metrics;
- segments;
- distribution shift.

### Leakage
- hidden truth forbidden;
- current-action future outcome forbidden;
- post-action timestamps forbidden.

### Reproducibility
- fixed artifact/input → same prediction;
- canonical trace equality.

### Artifacts
- save;
- load;
- compatibility rejection.

### Reports
- JSON;
- Markdown;
- manifest;
- action-conditioned traces.

## 38. Acceptance Criteria

### AC-01 — Action Taxonomy
All five recovery actions are supported.

### AC-02 — Outcome Labels
Action-conditioned labels come from governed Phase 6 simulator truth.

### AC-03 — Action Conditioning
Model B distinguishes the same context under different actions when signal exists.

### AC-04 — Observable Input Boundary
Only decision-time observable context, action, and permitted frozen Model A outputs enter Model B.

### AC-05 — Leakage Prevention
Hidden truth/future/post-action information cannot enter features.

### AC-06 — Training Discipline
Fitting is TRAINING-only.

### AC-07 — Validation Discipline
Selection/calibration uses TRAINING/VALIDATION only.

### AC-08 — Held-Out Protection
HELD_OUT_TEST/BENCHMARK cannot be used for fitting or tuning.

### AC-09 — Baselines
Required baselines exist.

### AC-10 — Candidate Model
At least one credible Model B exists.

### AC-11 — Success Probability
Valid `P(success | context, action)` is produced.

### AC-12 — Outcome State
Structured outcome state is produced.

### AC-13 — Recovery Amount
Bounded recovery-amount prediction exists where supported.

### AC-14 — Calibration
Calibration is evaluated overall and per action.

### AC-15 — Metrics
Required success and amount metrics are produced.

### AC-16 — Potential-Outcome Evaluation
Evaluator-only counterfactual/potential-outcome metrics are produced.

### AC-17 — Segment Analysis
Required segment evaluation is available.

### AC-18 — Distribution Shift
Model B is evaluated on governed shifted data.

### AC-19 — Error Analysis
Action-conditioned errors are inspectable.

### AC-20 — Prediction Trace
Every evaluation prediction is traceable.

### AC-21 — Versioning
Artifacts carry complete provenance/version metadata.

### AC-22 — Artifact Loading
Artifacts load without retraining and reject incompatible versions.

### AC-23 — Reproducibility
Frozen inputs/artifacts reproduce equivalent results.

### AC-24 — Reporting
Machine-readable and human-readable reports exist.

### AC-25 — Benchmark Integrity
No held-out leakage or cherry-picking.

### AC-26 — Phase Boundary
No Phase 9 economic decisioning, policy, or execution logic.

### AC-27 — Automated Tests
Phase 0–7 regression remains green and Phase 8 tests cover Model B.

### AC-28 — Manual Acceptance
A local end-to-end Model B training/evaluation run succeeds reproducibly.

## 39. Expected Module Boundary

A clean implementation may use:

```text
src/apro/recovery_prediction/
    __init__.py
    enums.py
    models.py
    labels.py
    features.py
    baselines.py
    models/
        __init__.py
        interface.py
        success_classifier.py
        amount_regressor.py
        ...
    calibration.py
    evaluation.py
    traces.py
    artifacts.py
    reports.py
```

Use existing Phase 6/7 abstractions instead of duplicating them where an equivalent interface exists.

## 40. Persistence

No production database persistence is required.

Prefer portable local model/evaluation artifacts.

## 41. Dependency Policy

Use the smallest justified ML dependency set.

No hosted AI service.

No external inference API.

Verify necessity, compatibility, maintenance, reproducibility, and licensing before adding dependencies.

## 42. Manual Acceptance

After automated tests pass, run:

```text
Phase 6 TRAINING dataset
        ↓
action-conditioned label construction
        ↓
observable feature preparation
        ↓
optional frozen Model A output
        ↓
baseline evaluation
        ↓
Model B candidate training
        ↓
validation selection
        ↓
validation calibration
        ↓
held-out evaluation
        ↓
per-action metrics
        ↓
amount metrics
        ↓
potential-outcome evaluation
        ↓
segment evaluation
        ↓
distribution shift
        ↓
artifact save/reload
        ↓
prediction traces
        ↓
reproducibility
        ↓
reports
```

The manual report must show:

```text
model_version
training_dataset_version
validation_dataset_version
held_out_dataset_version
feature_schema_version
action_schema_version
diagnosis_model_version (if used)
training seed
action distribution
selected model
per-action success metrics
per-action amount metrics
calibration metrics
potential-outcome metrics
shift metrics
artifact identity
reproducibility result
```

No live Razorpay operations.

No network calls.

No live customer/payment data.

## 43. Honest Reporting

Distinguish:

```text
training labels
simulated counterfactual potential outcomes
validation performance
held-out performance
shifted-distribution performance
```

Do not claim real-world causal performance from simulator-only evidence.

Do not report action rankings as Model B output.

## 44. Quality Gates

Run:

```powershell
.venv\Scripts\pytest.exe -v tests/recovery_prediction/
.venv\Scripts\pytest.exe -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\mypy.exe src
```

All Phase 0–7 tests must remain green.

Do not weaken previous tests.

## 45. Git Rules

During implementation:

- do not commit;
- do not push;
- preserve intentionally pre-existing uncommitted files;
- do not modify unrelated files;
- do not modify the locked Phase 8 specification.

Final report must include:

```text
git status --short --untracked-files=all
git diff --stat
```

and identify every changed/untracked file.

## 46. Final Readiness Gate

Phase 8 is ready for architecture review only when:

```text
Action taxonomy                    ✅
Outcome labels                    ✅
Action-conditioned features       ✅
Observable/hidden separation      ✅
Training discipline               ✅
Baselines                         ✅
Candidate Model B                 ✅
Success probabilities             ✅
Outcome states                    ✅
Recovery amount                   ✅
Calibration                       ✅
Per-action metrics                ✅
Potential-outcome evaluation      ✅
Segment analysis                  ✅
Distribution shift                ✅
Error analysis                    ✅
Prediction traces                ✅
Model artifact                    ✅
Artifact compatibility            ✅
Reproducibility                   ✅
Reports                           ✅
Automated tests                   ✅
Manual acceptance                 ✅
Phase boundary                    ✅
```

## 47. Final Report Requirements

Return:

### A. IMPLEMENTATION SUMMARY
Describe final Model B architecture.

### B. FILES CREATED
Exact list.

### C. FILES MODIFIED
Exact list.

### D. ACTION / OUTCOME TAXONOMY
Describe schemas and versions.

### E. LABEL CONSTRUCTION
Explain action-conditioned truth provenance.

### F. FEATURE CONTRACT
Describe observable features and schema.

### G. LEAKAGE PROTECTION
Provide concrete evidence.

### H. BASELINES
Report each baseline and result.

### I. CANDIDATE MODELS
Report candidates.

### J. MODEL SELECTION
Report validation criterion and selected model.

### K. CALIBRATION
Report method, fitting data, and metrics.

### L. HELD-OUT EVALUATION
Report success and amount metrics overall/per action.

### M. POTENTIAL-OUTCOME EVALUATION
Report evaluator-only simulator metrics.

### N. SEGMENT / SHIFT EVALUATION
Report required segments and shift results.

### O. ERROR ANALYSIS
Report systematic action-conditioned errors.

### P. REPRODUCIBILITY
Demonstrate identical frozen inputs/artifacts produce equivalent outputs.

### Q. ARTIFACTS
Provide model and manifest paths.

### R. TEST RESULTS
Exact targeted, full regression, Ruff, formatter, and Mypy results.

### S. MANUAL ACCEPTANCE
Describe complete local acceptance.

### T. PHASE BOUNDARY
Explicitly confirm no Phase 9 decisioning/policy/execution.

### U. GIT STATE
Return exact status/stat and confirm:

```text
0 staged
0 commits
0 pushes
```

### V. SPECIFICATION INTEGRITY
Confirm:

```text
docs/PHASE_08_RECOVERY_OUTCOME_PREDICTION_SPECIFICATION.md
```

was not modified.

### W. ARCHITECTURAL ISSUES
Return `NONE` if none; otherwise explain and STOP.

### X. FINAL STATUS

Return exactly one:

```text
PHASE 8 IMPLEMENTATION COMPLETE — READY FOR ARCHITECTURE REVIEW
```

or:

```text
PHASE 8 IMPLEMENTATION BLOCKED — ARCHITECTURE DECISION REQUIRED
```

STOP.

## 48. Non-Negotiable Principle

```text
Observable Context + Selected Action
              ↓
           Model B
              ↓
Success Probability + Outcome State + Recovery Amount
```

Separately:

```text
Hidden Simulator Truth
        ↓
Action-Conditioned Label Construction
        ↓
Post-Hoc Potential-Outcome Evaluation
```

Potential outcomes are evaluator/training-target information, never Model B features.

Model B estimates:

> **what is likely to happen under each action**

It does not decide:

> **which action APRO should take.**
