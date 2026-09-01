# APRO — Phase 9 Economic Decision Engine Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 9 — Economic Decision Engine  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0

---

## 1. Purpose

Phase 9 is the decision layer that converts the upstream intelligence outputs into a bounded, auditable recovery decision.

Phase 7 answers:

> What kind of failure is this?

Phase 8 answers:

> What is likely to happen under each recovery action?

Phase 9 answers:

> Given the available actions, their predicted outcomes, their expected economic value, and the configured policy/safety constraints, what action should APRO select?

Conceptually:

```text
Decision-Time Payment Context
        +
Phase 7 Diagnosis
        +
Phase 8 Action-Conditioned Outcome Predictions
        +
Economic Inputs / Costs
        +
Policy / Safety Constraints
        ↓
Phase 9 Economic Decision Engine
        ↓
Selected Recovery Action
        +
Decision Rationale
        +
Expected Economic Value
        +
Policy / Safety Result
        +
Decision Trace
```

Phase 9 is the first phase in which APRO may **select** a recovery action.

It still must NOT execute that action.

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
9. Completed Phase 0–8 specifications and acceptance evidence
10. This document:
   `docs/PHASE_09_ECONOMIC_DECISION_ENGINE_SPECIFICATION.md`

Phase 9 must consume the stable contracts created by Phase 6, Phase 7, and Phase 8.

Do not recreate:

- the governed dataset system;
- the benchmark system;
- Model A;
- Model B;
- webhook/persistence infrastructure.

If any authoritative document conflicts with this specification:

```text
STOP
↓
DOCUMENT THE CONFLICT
↓
REPORT TO USER + GPT
↓
ARCHITECTURE DECISION
↓
CONTINUE ONLY AFTER RESOLUTION
```

---

## 3. Phase Lineage

```text
Phase 1 — Webhook validation
        ↓
Phase 2 — Persistence
        ↓
Phase 3 — Canonical event pipeline
        ↓
Phase 4 — Recovery case orchestration
        ↓
Phase 5 — Independent simulation engine
        ↓
Phase 6 — Dataset & evaluation foundation
        ↓
Phase 7 — Failure diagnosis (Model A)
        ↓
Phase 8 — Recovery outcome prediction (Model B)
        ↓
Phase 9 — Economic Decision Engine
```

Phase 9 is the first layer that may convert predictions into an action decision.

---

## 4. Scope

### 4.1 In Scope

Implement:

- action-selection decision logic;
- economic utility calculation;
- Expected Recovery Value / expected utility calculation;
- action cost modeling;
- bounded penalties and incentives;
- candidate-action eligibility processing;
- policy/safety constraint integration;
- infeasible-action filtering;
- deterministic tie-breaking;
- decision rationale;
- decision confidence;
- decision trace;
- decision versioning;
- model/policy provenance;
- sensitivity analysis;
- action-level utility comparison;
- benchmark evaluation;
- counterfactual decision evaluation;
- regret analysis;
- segment analysis;
- distribution-shift analysis;
- reproducibility;
- decision artifact persistence;
- machine-readable and human-readable reports.

### 4.2 Explicitly Out of Scope

Phase 9 must NOT implement:

- real recovery execution;
- Razorpay outbound payment operations;
- actual Payment Link creation;
- actual retry execution;
- customer outreach;
- production messaging;
- autonomous scheduling;
- live money movement;
- live customer intervention;
- production serving;
- online policy learning;
- reinforcement learning;
- bandits;
- adaptive experimentation;
- real-time policy mutation.

The decision engine may **select** an action but must only return a decision object.

---

## 5. Core Decision Contract

Create an immutable decision result such as:

```text
RecoveryDecision
├── decision_id
├── record_id
├── scenario_id
├── recovery_case_id (optional)
├── selected_action
├── decision_status
├── expected_recovery_value
├── expected_gross_recovery
├── expected_cost
├── utility_by_action
├── eligibility_by_action
├── policy_result
├── confidence
├── rationale
├── diagnosis_model_version
├── outcome_model_version
├── policy_version
├── decision_model_version
├── dataset_version
├── evaluation_run_id
└── provenance
```

The result must be:

- immutable;
- serializable;
- deterministic for identical frozen inputs and configuration.

---

## 6. Decision Status

Use explicit statuses such as:

```text
ACTION_SELECTED
NO_ELIGIBLE_ACTION
NO_POSITIVE_UTILITY
ABSTAIN
```

The exact enumeration should be versioned.

The engine must never silently turn an infeasible action into a valid one.

---

## 7. Recovery Action Taxonomy

Consume the established five-action taxonomy:

```text
RETRY
PAYMENT_LINK
OUTREACH
STOP
ESCALATE
```

Maintain deterministic ordering.

Do not redefine action semantics in Phase 9.

Use the Phase 8 action schema/version.

---

## 8. Upstream Inputs

Phase 9 should consume:

### Context

```text
decision-time ModelInputRecord
```

### Model A

```text
DiagnosisResult
```

including:

```text
predicted diagnosis
class probabilities
confidence
uncertainty
model version
```

### Model B

One action-conditioned prediction for each eligible candidate action:

```text
OutcomePrediction(action=RETRY)
OutcomePrediction(action=PAYMENT_LINK)
OutcomePrediction(action=OUTREACH)
OutcomePrediction(action=STOP)
OutcomePrediction(action=ESCALATE)
```

where supported.

### Economic Configuration

Versioned economic inputs:

```text
action_cost
recovery_cap
minimum_utility_threshold
risk_penalty
customer_friction_cost
operational_cost
```

Only approved configuration may influence the utility calculation.

### Policy / Safety Configuration

Versioned eligibility/constraint configuration.

---

## 9. Action Eligibility

Before comparing utility, determine whether each action is eligible.

Eligibility may depend on explicitly configured rules such as:

```text
payment state
payment amount
failure diagnosis
attempt count
cooldown status
action-specific prerequisites
known safety restrictions
business constraints
```

Phase 9 must not invent policy rules outside the authoritative policy specification.

Separate:

```text
eligibility
```

from:

```text
economic utility
```

An action that is policy-infeasible must not win merely because it has high predicted value.

---

## 10. Policy Boundary

Phase 9 may consume policy constraints from the established policy contract.

Policy evaluation must be explicit:

```text
candidate action
      ↓
policy/safety checks
      ↓
ELIGIBLE / INELIGIBLE
```

Then:

```text
eligible actions
      ↓
economic comparison
```

Do not hide policy rules inside the utility formula.

Do not allow the economic optimizer to override safety/policy constraints.

---

## 11. Expected Recovery Value

Phase 9 may calculate an expected economic quantity from Phase 8 predictions.

A baseline conceptual form is:

```text
ExpectedGrossRecovery(a)
    =
P(success | context, a)
×
ExpectedRecoveredAmount(context, a)
```

Then:

```text
ExpectedRecoveryValue(a)
    =
ExpectedGrossRecovery(a)
−
ActionCost(a)
−
OperationalCost(a)
−
CustomerFrictionCost(a)
−
RiskPenalty(a)
```

The exact formula MUST follow the authoritative economic/policy specification if it defines one.

Do not silently invent monetary coefficients.

All coefficients must be versioned configuration.

---

## 12. Economic Unit Consistency

All monetary values must use the project's canonical integer representation for money, such as:

```text
paise / cents
```

Do not mix:

```text
integer minor units
floating-point currency amounts
```

without explicit conversion.

Utility calculations must avoid avoidable floating-point money errors.

Prefer:

```text
Decimal
integer minor units
```

or another existing project-standard representation.

---

## 13. Recovery Bounds

Phase 9 must not select an action whose predicted economic value violates explicit recovery bounds.

At minimum:

```text
expected recovered amount >= 0
expected recovered amount <= payment amount
```

unless an authoritative upstream contract states otherwise.

Do not let an invalid prediction silently pass through the decision layer.

---

## 14. Cost Model

Implement a versioned action-cost configuration.

Conceptually:

```text
RETRY
    operational cost
    customer friction cost
    risk penalty

PAYMENT_LINK
    operational cost
    customer friction cost
    risk penalty

OUTREACH
    operational cost
    customer friction cost
    risk penalty

STOP
    cost = configured baseline, usually zero

ESCALATE
    operational/handling cost
```

The exact values must come from explicit configuration.

Never hardcode hidden business economics inside action-selection code.

---

## 15. Utility Calculation

For every candidate action, calculate a complete utility record:

```text
ActionUtility
├── action
├── eligible
├── reason_if_ineligible
├── predicted_success_probability
├── predicted_recovered_amount
├── expected_gross_recovery
├── action_cost
├── operational_cost
├── customer_friction_cost
├── risk_penalty
├── expected_recovery_value
└── utility_version
```

The decision engine should expose the utility of **all evaluated actions**, not only the winner.

---

## 16. Candidate Comparison

The engine must:

1. obtain candidate predictions;
2. evaluate eligibility;
3. reject ineligible actions;
4. calculate utility for each eligible action;
5. compare utilities;
6. apply the configured threshold;
7. apply deterministic tie-breaking;
8. return the decision.

Conceptual rule:

```text
eligible_actions = policy_allowed(actions)

utilities = calculate_utility(eligible_actions)

best = argmax(utility)

if best.utility < configured_minimum_utility:
    return NO_POSITIVE_UTILITY / ABSTAIN

return best.action
```

The exact threshold/status behavior must be configuration-driven.

---

## 17. Deterministic Tie-Breaking

When two actions have economically equal utility within the configured tolerance:

```text
utility_tolerance
```

apply deterministic tie-breaking.

The tie-break configuration must be explicit and versioned.

Example only:

```text
STOP
ESCALATE
RETRY
PAYMENT_LINK
OUTREACH
```

Do not assume this order unless the authoritative policy/economic specification defines it.

Never use:

```text
random selection
UUID
system time
process order
```

for tie resolution.

---

## 18. Decision Threshold

Support a configurable minimum utility threshold:

```text
minimum_expected_recovery_value
```

The threshold must be versioned.

If no eligible action clears the threshold:

```text
NO_POSITIVE_UTILITY
```

or the configured abstention status is returned.

Do not force an intervention solely because one action has the highest negative utility.

---

## 19. Confidence

Decision confidence must be distinct from Model A/Model B confidence.

A decision-confidence representation may incorporate:

```text
utility margin between first and second eligible actions
prediction uncertainty
policy certainty
diagnosis uncertainty
```

The exact formula must be explicit and versioned.

Do not call a decision "high confidence" solely because Model B probability is high.

---

## 20. Sensitivity Analysis

The decision engine should support local sensitivity analysis.

For the winning action, evaluate how the decision changes under controlled perturbations of:

```text predicted success probability
predicted recovered amount
action cost
risk penalty
minimum utility threshold
```

The output should identify:

```text decision_stable
decision_sensitive
```

where justified.

Do not use sensitivity analysis to retroactively tune the held-out benchmark.

---

## 21. Counterfactual Decision Evaluation

Phase 9 may use governed simulator potential outcomes to evaluate the selected decision.

For each scenario:

```text selected_action
vs
simulator oracle/best potential action
```

Evaluator-side metrics may include:

```text decision regret
oracle gap
utility lift
recovery lift
avoidable intervention rate
```

These are evaluation metrics only.

Do not feed evaluator truth into the live decision calculation.

---

## 22. Decision Quality Metrics

Report:

```text
decision accuracy vs simulator oracle
oracle gap
mean utility
median utility
mean decision regret
median decision regret
recovery rate
recovered amount
incremental recovery
intervention rate
no-intervention rate
```

Also report:

```text unnecessary intervention rate
ineligible-selection rate
constraint violation count
```

Constraint violations must be zero.

---

## 23. Action Distribution

Report:

```text selected action distribution
```

and compare it to:

```text baseline action distributions
```

Do not optimize the action distribution merely for visual plausibility.

Interpret action frequency together with utility and outcome metrics.

---

## 24. Segment Evaluation

Evaluate decisions across:

```text scenario family
payment method
payment value tier
scenario difficulty
failure diagnosis
diagnosis confidence
action
seed
```

Also useful:

```text historical failure count
metadata completeness
utility-margin bucket
```

Always report support.

---

## 25. Distribution Shift

Evaluate decision behavior against a governed shifted benchmark.

Compare:

```text in-distribution
vs
shifted distribution
```

for:

```text mean utility
decision regret
action distribution
intervention rate
recovery rate
constraint violations
```

Do not retune the decision engine on shifted results unless a new governed experiment is created.

---

## 26. Error Analysis

Identify:

```text
wrong decisions vs oracle
high-confidence wrong decisions
negative-utility selections
near-tie decisions
policy-filtered best-prediction actions
large-regret decisions
shift-sensitive decisions
```

For each case preserve:

```text scenario_id
selected_action
oracle_action (evaluator-side)
utility_by_action
prediction inputs
policy eligibility
decision confidence
decision rationale
```

The oracle action is evaluator-side truth.

---

## 27. Decision Trace

Every evaluated decision must record:

```text
decision_id
record_id
scenario_id
recovery_case_id (optional)
selected_action
decision_status
utility_by_action
eligibility_by_action
expected_recovery_value
expected_gross_recovery
expected_cost
decision_confidence
rationale
diagnosis_model_version
outcome_model_version
policy_version
decision_model_version
dataset_version
evaluation_run_id
```

Do not embed hidden simulator truth into the live decision portion of the trace.

---

## 28. Model/Policy Versioning

Every decision run must identify:

```text
decision_model_version
economic_config_version
policy_version
diagnosis_model_version
outcome_model_version
action_schema_version
feature_schema_version
dataset_version
training/evaluation seed
```

Material changes create new versions.

---

## 29. Decision Artifact

Persist a portable decision-engine configuration/artifact containing:

```text
economic coefficients
thresholds
tie-break policy
eligibility configuration
utility formula version
decision model version
policy version
action schema version
```

A loaded artifact must produce equivalent decisions for identical frozen inputs.

Do not store executable policy code inside opaque blobs.

Prefer explicit serializable configuration.

---

## 30. Training Boundary

Phase 9 is primarily a decision/economic layer.

If no learned decision model is introduced, there is no new ML training phase.

If a learned component is introduced later:

```text
TRAINING only
VALIDATION for selection
HELD_OUT_TEST for final evaluation
```

must remain enforced.

For Phase 9 v1, a deterministic configured economic decision engine is preferred.

Do not train a black-box action policy in this phase.

---

## 31. No Policy/Utility Conflation

Keep separate objects for:

```text
ActionEligibility
ActionUtility
DecisionResult
```

The architecture should make it impossible to confuse:

```text
"cannot perform"
```

with:

```text
"not economically worthwhile"
```

For example:

```text
PAYMENT_LINK
    eligible = false
    reason = policy restriction
```

is not equivalent to:

```text
PAYMENT_LINK
    eligible = true
    expected_recovery_value = -₹50
```

---

## 32. Decision Safety Invariants

The decision engine must enforce:

```text
no action outside taxonomy
no ineligible action selected
no negative-payment recovery
no utility from hidden truth
no future information
no outbound side effects
no action execution
no silent fallback
```

Every returned decision must be auditable.

---

## 33. Action Selection Must Not Execute

The output:

```text
selected_action = RETRY
```

means only:

> The decision engine selected RETRY.

It does NOT:

- send a retry request;
- call Razorpay;
- create a Payment Link;
- message a customer;
- enqueue execution.

Execution belongs to a later phase.

---

## 34. Baselines

Implement at least:

### Baseline 0 — No Intervention

Always choose:

```text
STOP
```

or the project's configured no-action representation.

### Baseline 1 — Highest Predicted Success

Choose the eligible action with highest:

```text
P(success | context, action)
```

without economic cost optimization.

This is a diagnostic baseline, not the final policy.

### Baseline 2 — Highest Predicted Recovery Amount

Choose the eligible action with highest:

```text
predicted_recovered_amount
```

again without economic optimization.

### Baseline 3 — Static Action Rule

An explicit deterministic rule using observable decision context.

### Baseline 4 — Economic Decision Engine

The Phase 9 policy itself.

Compare all against the same frozen benchmark.

---

## 35. Decision Algorithm

The v1 deterministic engine should implement:

```text
INPUT:
    context
    Model A diagnosis
    Model B predictions
    economic configuration
    policy configuration

STEP 1:
    validate all versions and schemas

STEP 2:
    evaluate eligibility for each action

STEP 3:
    discard ineligible actions

STEP 4:
    calculate expected gross recovery

STEP 5:
    subtract configured costs/penalties

STEP 6:
    calculate expected recovery value

STEP 7:
    compare eligible actions

STEP 8:
    apply utility threshold

STEP 9:
    apply deterministic tie-break

STEP 10:
    return immutable RecoveryDecision
```

No network operations occur.

---

## 36. Reporting

Generate:

```text
economic_decision_evaluation.json
economic_decision_evaluation.md
economic_decision_trace.jsonl
economic_decision_manifest.json
economic_decision_action_utility.json
```

Reports should include:

```text
decision configuration
policy version
action costs
threshold
tie-break rules
baseline performance
selected engine performance
utility metrics
regret
oracle gap
action distribution
segment results
shift results
error analysis
reproducibility
constraint violations
```

---

## 37. Testing Requirements

Create a Phase 9 test suite covering:

### Taxonomy

- five actions;
- deterministic order;
- decision statuses.

### Eligibility

- eligible action;
- ineligible action;
- all actions ineligible;
- policy reason retention.

### Utility

- formula correctness;
- cost subtraction;
- risk/fractional penalties;
- monetary unit correctness;
- recovery bounds.

### Threshold

- above threshold;
- exactly threshold;
- below threshold;
- negative utility;
- no positive utility.

### Tie Breaking

- exact tie;
- tolerance tie;
- deterministic tie resolution.

### Prediction Integration

- Model A version;
- Model B version;
- action alignment;
- missing prediction rejection.

### Decision Safety

- no ineligible action selected;
- no hidden truth;
- no future information;
- no execution call.

### Sensitivity

- stable decision;
- threshold-sensitive decision;
- cost-sensitive decision.

### Baselines

- no intervention;
- highest success;
- highest recovery amount;
- static rule.

### Evaluation

- oracle comparison;
- regret;
- utility;
- recovery;
- intervention rate;
- segment evaluation;
- shifted benchmark.

### Artifacts

- save;
- load;
- compatibility checks;
- deterministic identity.

### Reproducibility

- same inputs/configuration → same decision;
- same artifact → same decision;
- deterministic trace.

### Reporting

- JSON;
- Markdown;
- utility table;
- traces;
- manifest.

---

## 38. Acceptance Criteria

Phase 9 is complete only when:

### AC-01 — Action Selection
The engine can select exactly one eligible action or return an explicit no-action/abstention status.

### AC-02 — Economic Utility
Economic value is calculated from explicit, versioned inputs.

### AC-03 — Expected Recovery Value
Expected recovery value is calculated according to the authoritative economic formula.

### AC-04 — Cost Model
Action costs and penalties are explicit and versioned.

### AC-05 — Eligibility
Policy/safety eligibility is evaluated before economic selection.

### AC-06 — Ineligible Protection
An ineligible action can never be selected.

### AC-07 — Threshold
Minimum utility/decision threshold is enforced.

### AC-08 — Tie Breaking
Utility ties resolve deterministically.

### AC-09 — Multi-Action Comparison
All supported eligible actions are compared.

### AC-10 — Model A Integration
Diagnosis outputs are consumed with explicit version compatibility.

### AC-11 — Model B Integration
Action-conditioned outcome predictions are consumed with explicit version compatibility.

### AC-12 — Decision Confidence
Decision confidence is explicit and distinct from upstream model confidence.

### AC-13 — Sensitivity
Decision sensitivity can be measured under controlled input perturbations.

### AC-14 — Baselines
Required non-economic baselines are implemented and evaluated.

### AC-15 — Counterfactual Evaluation
Evaluator-side oracle/regret metrics are produced from governed simulator truth.

### AC-16 — Segment Evaluation
Decision quality is reportable by required segments.

### AC-17 — Distribution Shift
Decision performance is evaluated under governed distribution shift.

### AC-18 — Decision Trace
Every evaluated decision is auditable.

### AC-19 — Versioning
Decision/economic/policy/model versions are explicit.

### AC-20 — Artifact Loading
Decision configuration loads without ambiguity.

### AC-21 — Reproducibility
Identical frozen inputs/configuration reproduce identical decisions.

### AC-22 — No Execution
No action-selection path performs real recovery.

### AC-23 — No Outbound Effects
No Razorpay/customer network side effects exist.

### AC-24 — Benchmark Integrity
Held-out information is not used to tune the final decision engine.

### AC-25 — Constraint Safety
Constraint violations are zero.

### AC-26 — Automated Tests
Phase 0–8 regression remains green and Phase 9 tests cover all decision invariants.

### AC-27 — Manual Acceptance
A local end-to-end decision run succeeds across a governed benchmark and produces reproducible results.

---

## 39. Expected Module Boundaries

A clean implementation may use:

```text
src/apro/decision/
    __init__.py
    enums.py
    models.py
    economics.py
    eligibility.py
    utility.py
    baselines.py
    engine.py
    sensitivity.py
    evaluation.py
    traces.py
    artifacts.py
    reports.py
```

Exact names may differ if the repository already has an appropriate architectural location.

Do not duplicate Phase 6–8 infrastructure.

---

## 40. Persistence Boundary

No production database persistence is required for Phase 9 v1.

Prefer:

```text
portable decision configuration
portable evaluation artifacts
decision traces
reports
```

Do not create database tables merely for decision experiments.

---

## 41. Dependency Policy

Phase 9 v1 should not require a new ML framework.

Prefer deterministic Python/domain logic using existing project dependencies.

Do not introduce:

- hosted AI services;
- online optimization platforms;
- policy SaaS;
- production execution gateways.

---

## 42. Manual Acceptance

After automated tests pass, run a local end-to-end Phase 9 acceptance.

Required flow:

```text
Phase 6 governed benchmark
        ↓
Phase 7 frozen diagnosis predictions
        ↓
Phase 8 frozen action-conditioned predictions
        ↓
Economic configuration
        ↓
Policy/eligibility evaluation
        ↓
Baseline decisions
        ↓
Economic decision engine
        ↓
Per-action utilities
        ↓
Selected action / abstention
        ↓
Oracle/regret evaluation
        ↓
Segments
        ↓
Distribution shift
        ↓
Sensitivity
        ↓
Artifact save/reload
        ↓
Reproducibility
        ↓
Reports
```

The acceptance run must report:

```text
dataset_version
diagnosis_model_version
outcome_model_version
economic_config_version
policy_version
decision_model_version
action_schema_version
seed
candidate/action distribution
baseline results
selected-action distribution
mean utility
mean regret
oracle gap
recovery metrics
intervention rate
constraint violations
distribution-shift results
sensitivity result
artifact identity
reproducibility result
```

No live recovery execution.

No outbound network operations.

No real customer/payment data.

---

## 43. Honest Reporting

The final Phase 9 report must distinguish:

```text
predicted action outcome
economic utility calculation
policy eligibility
selected decision
simulator oracle evaluation
```

Do not claim:

> APRO recovered real money

from simulator-only evaluation.

Valid Phase 9 claim:

> APRO can deterministically combine governed failure diagnosis, action-conditioned outcome predictions, explicit economic costs, and policy constraints to select an auditable recovery action in the simulated evaluation environment.

---

## 44. Phase 10 Handoff

Phase 9 should expose a stable decision contract:

```text
RecoveryDecision
```

containing:

```text
selected_action
decision_status
expected_recovery_value
utility_by_action
eligibility_by_action
decision_confidence
rationale
decision_model_version
economic_config_version
policy_version
diagnosis_model_version
outcome_model_version
provenance
```

A later execution phase may consume this object.

Phase 9 itself must not execute it.

---

## 45. Phase Boundary Safety Check

Before completion explicitly verify:

```text
NO recovery executor
NO Razorpay outbound operation
NO customer outreach
NO payment link creation
NO retry execution
NO scheduling
NO background execution dispatcher
NO production serving
NO live intervention
NO reinforcement learning
NO online learning
NO bandit
NO adaptive experimentation
```

---

## 46. Git Rules

During implementation:

- do not commit;
- do not push;
- preserve intentionally pre-existing uncommitted files;
- do not modify unrelated files;
- do not modify the locked Phase 9 specification.

Final report must include:

```text
git status --short --untracked-files=all
git diff --stat
git diff --name-only
```

and classify every change by provenance.

---

## 47. Quality Gates

Run:

```powershell
.venv\Scripts\pytest.exe -v tests/decision/
.venv\Scripts\pytest.exe -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\mypy.exe src
```

All Phase 0–8 tests must remain passing.

---

## 48. Final Readiness Gate

Phase 9 is ready for architecture review only when:

```text
Action selection                     ✅
Economic utility                     ✅
Expected Recovery Value              ✅
Explicit action costs               ✅
Policy eligibility                   ✅
Ineligible-action protection         ✅
Utility threshold                    ✅
Deterministic tie-breaking           ✅
Model A integration                  ✅
Model B integration                  ✅
Decision confidence                  ✅
Sensitivity analysis                 ✅
Baselines                            ✅
Oracle/regret evaluation             ✅
Segment analysis                     ✅
Distribution shift                   ✅
Decision traces                      ✅
Versioning                           ✅
Artifact compatibility               ✅
Reproducibility                      ✅
Reports                              ✅
Automated tests                      ✅
Manual acceptance                    ✅
No execution                         ✅
No outbound effects                  ✅
```

---

## 49. Final Report Requirements

After implementation and verification, return:

### A. IMPLEMENTATION SUMMARY

Describe the final Phase 9 decision architecture.

### B. FILES CREATED

Exact list.

### C. FILES MODIFIED

Exact list and reasons.

### D. ACTION / DECISION TAXONOMY

Report action and decision status versions.

### E. ECONOMIC MODEL

Report utility formula, costs, thresholds, penalties, and money representation.

### F. ELIGIBILITY / POLICY

Report policy checks, eligibility decisions, and configuration version.

### G. MODEL INPUTS

Report Model A and Model B versions consumed and compatibility checks.

### H. BASELINES

Report baseline decision performance.

### I. DECISION ENGINE

Report selected-model/engine behavior and deterministic tie-breaking.

### J. SENSITIVITY

Report decision-stability analysis.

### K. HELD-OUT EVALUATION

Report decision accuracy/regret/utility/recovery metrics.

### L. COUNTERFACTUAL EVALUATION

Report simulator oracle comparison and regret.

### M. SEGMENT / SHIFT EVALUATION

Report required segment and shifted results.

### N. ERROR ANALYSIS

Report high-regret, constraint-filtered, near-tie, and shift-sensitive cases.

### O. REPRODUCIBILITY

Demonstrate identical frozen inputs/configuration produce identical decisions and traces.

### P. ARTIFACTS

Provide decision configuration, manifest, reports, utility tables, and traces.

### Q. TEST RESULTS

Exact:

```text
Phase 9 targeted tests:
Full regression:
Ruff:
Formatter:
Mypy:
```

with passed/failed/skipped counts.

### R. MANUAL ACCEPTANCE

Describe the complete local run and observed results.

### S. PHASE BOUNDARY

Explicitly confirm no:

```text
execution
Razorpay outbound calls
customer outreach
payment-link creation
retry execution
scheduling
production intervention
```

### T. GIT STATE

Return exact:

```text
git status --short --untracked-files=all
git diff --stat
git diff --name-only
```

Confirm:

```text
0 staged
0 commits
0 pushes
```

### U. SPECIFICATION INTEGRITY

Confirm:

```text
docs/PHASE_09_ECONOMIC_DECISION_ENGINE_SPECIFICATION.md
```

was not modified.

### V. ARCHITECTURAL ISSUES

Return:

```text
NONE
```

if none. Otherwise explain and STOP.

### W. FINAL STATUS

Return exactly one:

```text
PHASE 9 IMPLEMENTATION COMPLETE — READY FOR ARCHITECTURE REVIEW
```

or:

```text
PHASE 9 IMPLEMENTATION BLOCKED — ARCHITECTURE DECISION REQUIRED
```

STOP.

---

## 50. Non-Negotiable Principle

Phase 9 is the deterministic bridge:

```text
Phase 7 Diagnosis
       +
Phase 8 Action-Conditioned Predictions
       +
Explicit Economic Inputs
       +
Policy / Safety Constraints
       ↓
Economic Decision Engine
       ↓
Selected Recovery Action
```

The decision engine may select an action.

It must NOT execute the action.

The exact boundary is:

```text
PREDICT
   ↓
VALUE
   ↓
CONSTRAIN
   ↓
SELECT
   ↓
RETURN DECISION
   X
EXECUTE
```

Phase 9 must remain fully auditable:

> Every selected action must be explainable as the result of explicit upstream predictions, explicit economic configuration, explicit eligibility/policy constraints, and deterministic comparison logic.
