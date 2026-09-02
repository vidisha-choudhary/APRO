# APRO — Phase 10 Policy & Safety Engine Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 10 — Policy & Safety Engine  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0

---

## 1. Purpose

Phase 10 implements APRO's deterministic **Policy & Safety Engine**.

Phase 9 determines the economically preferred action. Phase 10 independently determines whether that proposed action is permitted under explicit safety, governance, state, approval, and operational constraints.

The governing principle is:

> **Prediction does not equal permission.**

The policy engine is deterministic. It does not learn, improvise, optimize economics, execute actions, or mutate its own rules.

### Phase boundary

```text
Trusted Event / Current Payment State
                +
Recovery Case Context
                +
Phase 7 DiagnosisResult
                +
Phase 8 Outcome Predictions
                +
Phase 9 RecoveryDecision
                +
Versioned Policy Configuration
                ↓
        PHASE 10 POLICY ENGINE
                ↓
       ALLOW / BLOCK /
       REQUIRE_HUMAN_APPROVAL
                +
        Policy Reasons / Evidence
                +
        Policy Trace / Provenance
                ↓
        Phase 11 Execution Framework
```

Phase 10 never calls a real executor.

---

## 2. Authority Hierarchy

Implementation must follow this authority order:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. Completed Phase 0–9 specifications and acceptance evidence
10. This document

`docs/POLICY_AND_SAFETY_SPECIFICATION.md` is the authoritative policy contract. This phase specification operationalizes that contract; it must not silently redefine it.

If a conflict is discovered:

```text
STOP
↓
Document the conflict
↓
Report to User + GPT
↓
Architecture decision
↓
Update specification if required
↓
Continue
```

---

## 3. Relationship to Completed Phases

### Phase 7
Provides failure diagnosis. Phase 10 may consume diagnosis and confidence but may not retrain or modify Model A.

### Phase 8
Provides action-conditioned recovery predictions. Phase 10 may validate and consume them but may not retrain or modify Model B.

### Phase 9
Produces an economically preferred `RecoveryDecision`. Phase 10 is the authoritative permission gate before any future execution. A Phase 9 action is never sufficient authorization by itself.

### Phase 11
Will provide the execution framework. Phase 10 ends at a policy decision and does not perform external execution.

---

## 4. Scope

### In scope

- deterministic policy evaluation;
- explicit `ALLOW`, `BLOCK`, and `REQUIRE_HUMAN_APPROVAL` outcomes;
- hard safety rules;
- payment-state checks;
- trusted-event checks;
- supported-action validation;
- retry controls;
- cooldown/retry-spacing controls;
- repeated-intervention protection;
- high-value transaction protection;
- low-confidence protection;
- minimum expected-value protection;
- STOP and ESCALATE handling;
- human approval integrity;
- stale/out-of-order state protection;
- reconciliation requirements;
- model-failure fail-safe behavior;
- idempotency checks;
- Payment Link duplication/capacity checks;
- explicit rule registry and reason codes;
- versioning and compatibility checks;
- deterministic policy traces;
- portable policy artifacts;
- governed policy evaluation, segment analysis, and distribution-shift analysis;
- automated and manual acceptance tests.

### Explicitly out of scope

- Razorpay API calls;
- Payment Link creation;
- retry execution;
- customer outreach or messaging;
- money movement;
- autonomous scheduling;
- production serving;
- policy learning;
- reinforcement learning;
- bandits;
- adaptive experimentation;
- dynamic policy mutation;
- live external intervention;
- replacement of Model A, Model B, or Phase 9.

---

## 5. Core Policy Contract

Define an immutable `PolicyDecision` equivalent to:

```text
PolicyDecision
├── policy_decision_id
├── case_id
├── payment_id
├── event_id (optional)
├── decision_id (optional)
├── requested_action
├── policy_outcome
├── effective_action (optional)
├── reason_code
├── reason_detail
├── approval_required
├── approval_reference (optional)
├── reconciliation_required
├── defer_until (optional)
├── rules_evaluated
├── rules_triggered
├── payment_state_observed
├── event_trust_state
├── model_output_valid
├── policy_version
├── rule_set_version
├── action_schema_version
├── decision_model_version
├── diagnosis_model_version
├── outcome_model_version
├── dataset_version (optional)
├── evaluation_run_id (optional)
└── provenance
```

The result must be immutable, serializable, auditable, and deterministic for identical frozen inputs and configuration.

---

## 6. Policy Outcomes

Every policy evaluation returns exactly one of:

```text
ALLOW
BLOCK
REQUIRE_HUMAN_APPROVAL
```

No implicit policy outcome is permitted.

The result may also communicate:

```text
effective_action = requested action
 effective_action = STOP
 effective_action = ESCALATE
```

only when explicitly authorized by configuration/rules.

---

## 7. Deterministic Evaluation Order

Implement the policy sequence defined by the authoritative safety specification:

```text
1. Is the event trusted?
2. Is the payment state current?
3. Is the payment still recoverable?
4. Is the action supported?
5. Is the action within attempt limits?
6. Is the transaction within automation limits?
7. Is model confidence sufficient?
8. Is expected recovery value sufficient?
9. Are repeated-intervention constraints satisfied?
10. Does any human-approval rule apply?
11. Produce ALLOW / BLOCK / REQUIRE_HUMAN_APPROVAL
```

Hard safety rules take precedence over economic value.

---

## 8. Rule Precedence

A deterministic precedence system must exist. Minimum conceptual precedence is:

```text
HARD SAFETY BLOCK
        >
STALE / UNKNOWN STATE
        >
UNSUPPORTED ACTION
        >
ATTEMPT / INTERVENTION LIMIT
        >
INVALID MODEL OUTPUT
        >
CONFIDENCE / ECONOMIC GUARDRAILS
        >
HUMAN APPROVAL REQUIREMENT
        >
ALLOW
```

If several rules trigger, the policy result and triggered-rule list must be deterministic.

---

## 9. Event Trust and Duplicate Protection

### Invalid/untrusted event

An invalid webhook signature must not enter an authorized recovery path.

Policy result must represent rejection/blocking explicitly and preserve the reason.

### Duplicate event

If an `event_id` is already processed:

```text
IGNORE_DUPLICATE
```

A duplicate delivery must not authorize another externally meaningful action.

---

## 10. Payment-State Safety

### Captured-payment hard block

If:

```text
payment.status == CAPTURED
```

return:

```text
BLOCK
reason_code = PAYMENT_ALREADY_RECOVERED
```

This rule outranks model output, confidence, ERV, customer history, retries, and action ranking.

### Unknown state

If the current payment state is unknown or cannot be trusted, never assume `FAILED` or `CAPTURED`.

Use an explicit:

```text
RECONCILIATION_REQUIRED
```

or configured human-approval outcome.

---

## 11. Stale and Out-of-Order Events

Webhook arrival order must not be treated as occurrence order.

An event older than the trusted current state, or inconsistent with a newer captured state, must not blindly overwrite current state.

Example:

```text
10:02 payment.captured
10:05 payment.failed
```

If the current trusted state is captured, policy must prevent recovery authorization from the stale failure event.

Reason code should distinguish stale/inconsistent state from ordinary captured-payment protection where appropriate.

---

## 12. Supported Action Rule

Use the established Phase 8 action taxonomy:

```text
RETRY
PAYMENT_LINK
OUTREACH
STOP
ESCALATE
```

If an action has no valid execution contract:

```text
BLOCK
reason_code = UNSUPPORTED_ACTION
```

Phase 10 must never represent an unsupported action as executable.

---

## 13. Model Output Validation

Validate all model-derived fields used in the policy decision.

Reject output containing:

- NaN;
- infinity;
- probability below `0`;
- probability above `1`;
- unknown action;
- missing required fields;
- recovered amount below `0`;
- recovered amount above payment amount;
- incompatible schema/version;
- inconsistent record/scenario identifiers where those contracts apply.

Default behavior is fail-closed.

Policy must never infer a missing model value.

---

## 14. Retry Controls

All retry controls are configuration-driven and versioned.

Required configuration concepts:

```text
MAX_RETRIES
RETRY_COOLDOWN_SECONDS
MAX_SAME_ACTION_REPETITIONS
```

### Retry count

If:

```text
retry_count >= MAX_RETRIES
```

then `RETRY` must be blocked or routed according to explicit policy.

### Retry spacing

If:

```text
current_time < next_retry_allowed_at
```

then the retry must be blocked or deferred.

### Same-action repetition

Do not allow indefinite:

```text
RETRY → FAILED → RETRY → FAILED → RETRY
```

beyond the configured action-specific limit.

---

## 15. Total Intervention Limit

Maintain:

```text
TOTAL_INTERVENTIONS
MAX_TOTAL_INTERVENTIONS
```

If the maximum has been reached, automated active interventions are prohibited.

The configured response may be STOP, ESCALATE, or human approval as explicitly defined.

---

## 16. High-Value Transaction Protection

Define a configurable:

```text
HIGH_VALUE_THRESHOLD
```

Do not invent or hide a production threshold in implementation code.

If:

```text
payment.amount >= HIGH_VALUE_THRESHOLD
```

the configured policy may require:

```text
REQUIRE_HUMAN_APPROVAL
```

Fixture-specific thresholds used in tests must be explicit test configuration.

---

## 17. Confidence Protection

Support distinct configurable thresholds for:

```text
MIN_DIAGNOSIS_CONFIDENCE
MIN_OUTCOME_CONFIDENCE
MIN_DECISION_CONFIDENCE
```

Low confidence must not silently authorize automated recovery.

Possible configured outcomes are:

```text
REQUIRE_HUMAN_APPROVAL
BLOCK
STOP
```

Do not treat one high model probability as sufficient permission.

---

## 18. Expected-Value and Negative-Utility Protection

Phase 10 consumes Phase 9 economic outputs; it does not recompute the Phase 9 optimizer.

If:

```text
ERV < MIN_EXPECTED_RECOVERY_VALUE
```

automated active recovery must not be allowed.

If:

```text
ERV <= 0
```

the action must not execute automatically.

Economic preference and policy permission remain separate concepts.

---

## 19. STOP and ESCALATE

### STOP

STOP is a valid first-class safe outcome.

Examples:

- insufficient expected value;
- captured payment;
- exhausted attempts;
- exhausted intervention limits;
- insufficient confidence where configured to stop;
- no supported action remains.

### ESCALATE

ESCALATE is appropriate when the system must not resolve the case autonomously, including:

- high-value cases;
- low confidence;
- conflicting evidence;
- unknown failure;
- repeated failed interventions;
- unsupported edge cases;
- policy exceptions;
- reconciliation ambiguity.

---

## 20. Human Approval

When:

```text
policy_outcome == REQUIRE_HUMAN_APPROVAL
```

no future execution framework may proceed without an explicit valid approval.

An approval must bind to:

```text
case_id
decision_id
approved_action
approver_reference
timestamp
policy_version
```

Approval is action-specific.

An approval for `PAYMENT_LINK` must not authorize `RETRY`.

---

## 21. Approval Validity and Replay Protection

Approval records should carry explicit validity data as required by the policy contract:

```text
approval_id
case_id
decision_id
approved_action
approver_reference
approved_at
expires_at (optional)
policy_version
```

Reject:

- missing approval;
- mismatched case;
- mismatched decision;
- mismatched action;
- expired approval;
- incompatible policy version.

Approvals must not be reusable to broaden authority.

---

## 22. Current-State Recheck

Phase 10 must expose a final current-state gate suitable for Phase 11 to invoke immediately before execution.

Example:

```text
10:00 payment.failed
10:01 Phase 9 → PAYMENT_LINK
10:02 payment.captured
10:03 policy re-check
```

Expected result:

```text
BLOCK
reason_code = PAYMENT_ALREADY_RECOVERED
```

No executor may bypass this gate.

---

## 23. Reconciliation and Unknown External Results

Phase 10 must support explicit reconciliation state for future execution results.

A timeout must not be interpreted automatically as success or failure.

Represent an uncertain outcome as:

```text
RECONCILIATION_REQUIRED
```

until provider state can be resolved.

Phase 10 itself does not perform the provider reconciliation call.

---

## 24. External Idempotency

Every externally meaningful future action must have a deterministic internal idempotency identity binding at least:

```text
case_id
action
execution_attempt
```

A duplicate authorization for an already-authorized/executed idempotency identity must be blocked or represented as an idempotency conflict according to policy.

Phase 10 never performs the external call.

---

## 25. Payment Link Protection

Support configured:

```text
PAYMENT_LINK_CREATION_COUNT
MAX_PAYMENT_LINK_CREATIONS
```

When capacity is exhausted, block or require approval according to policy.

If an existing valid Payment Link is already associated with the same approved action, prefer reuse of its reference over duplicate authorization.

Phase 10 does not create the Payment Link.

---

## 26. Model Failure Fallback

If Model A fails, never invent a diagnosis.

Configured fallback may be:

```text
DETERMINISTIC_BASELINE
STOP
ESCALATE
REQUIRE_HUMAN_APPROVAL
```

If Model B fails, never invent probabilities.

Configured fallback may be:

```text
STATIC_BASELINE
STOP
ESCALATE
REQUIRE_HUMAN_APPROVAL
```

Fallback policy is versioned and testable.

---

## 27. Configuration Contract

Create a validated immutable policy configuration with all behavior-changing values explicitly represented.

Suggested structure:

```text
PolicyConfig
├── policy_version
├── policy_schema_version
├── rule_set_version
├── action_schema_version
├── max_retries
├── retry_cooldown_seconds
├── max_same_action_repetitions
├── max_total_interventions
├── high_value_threshold
├── min_diagnosis_confidence
├── min_outcome_confidence
├── min_decision_confidence
├── min_expected_recovery_value
├── max_payment_link_creations
├── approval_expiry_seconds (optional)
├── stale_event_policy
├── unknown_state_policy
├── model_failure_policy
├── unsupported_action_policy
├── negative_erv_policy
├── precedence_configuration
└── effective_at
```

No thresholds may be scattered as magic numbers through the codebase.

---

## 28. Rule Registry

Every policy rule must be explicitly represented in a deterministic registry or equivalent structure.

Each rule should expose:

```text
rule_id
rule_version
priority
enabled
action_scope
description
trigger_condition
policy_outcome
reason_code
```

Required rule coverage should include:

```text
H1_PAYMENT_CAPTURED
H2_INVALID_EVENT
H3_DUPLICATE_EVENT
H4_UNSUPPORTED_ACTION
H5_INVALID_MODEL_OUTPUT
R_RETRY_LIMIT
R_RETRY_COOLDOWN
R_SAME_ACTION_LIMIT
R_TOTAL_INTERVENTION_LIMIT
S_HIGH_VALUE
S_LOW_CONFIDENCE
S_MIN_ERV
S_NEGATIVE_ERV
S_STALE_STATE
S_RECONCILIATION
S_PAYMENT_LINK_CAPACITY
S_IDEMPOTENCY_CONFLICT
```

Names may differ internally if the same contracts remain explicit and auditable.

---

## 29. Stable Reason Codes

At minimum support these machine-readable reason codes:

```text
PAYMENT_ALREADY_RECOVERED
INVALID_EVENT
DUPLICATE_EVENT
UNSUPPORTED_ACTION
INVALID_MODEL_OUTPUT
MAX_RETRIES_REACHED
RETRY_COOLDOWN_ACTIVE
MAX_SAME_ACTION_REPETITIONS_REACHED
MAX_TOTAL_INTERVENTIONS_REACHED
HIGH_VALUE_REQUIRES_APPROVAL
LOW_CONFIDENCE_REQUIRES_APPROVAL
INSUFFICIENT_EXPECTED_VALUE
NEGATIVE_EXPECTED_VALUE
STALE_OR_INCONSISTENT_EVENT
RECONCILIATION_REQUIRED
PAYMENT_LINK_CAPACITY_REACHED
DUPLICATE_PAYMENT_LINK
MODEL_A_FAILURE
MODEL_B_FAILURE
APPROVAL_REQUIRED
APPROVAL_MISMATCH
APPROVAL_EXPIRED
IDEMPOTENCY_CONFLICT
```

Reason codes must be stable for identical inputs/configuration.

---

## 30. Policy Trace

Every policy evaluation must generate an auditable trace equivalent to:

```text
PolicyEvaluationTrace
├── policy_decision_id
├── case_id
├── payment_id
├── event_id
├── decision_id
├── requested_action
├── policy_outcome
├── effective_action
├── payment_state
├── event_trust_state
├── model_output_valid
├── rules_evaluated
├── rules_triggered
├── final_reason_code
├── approval_required
├── reconciliation_required
├── idempotency_key
├── policy_version
├── rule_set_version
├── action_schema_version
├── decision_model_version
├── diagnosis_model_version
├── outcome_model_version
├── dataset_version (optional)
├── evaluation_run_id (optional)
└── timestamp / latency metadata
```

Do not place simulator hidden truth, potential outcomes, oracle actions, latent variables, or future outcome information into the live policy trace.

---

## 31. Policy Artifact

Persist a portable policy artifact containing:

```text
policy_version
policy_schema_version
rule_set_version
action_schema_version
all thresholds
rule definitions
precedence configuration
fallback configuration
approval configuration
idempotency configuration
effective_at
created_at
deterministic_identity
```

`created_at` is provenance metadata and is excluded from deterministic identity.

The deterministic identity must cover canonical policy semantics/configuration only.

---

## 32. Artifact Compatibility

Artifact loading must reject incompatible configurations when:

- policy schema is incompatible;
- action schema is incompatible;
- required fields are absent;
- rule versions are incompatible;
- precedence is invalid;
- configuration violates validation constraints.

Failure must be explicit and fail-closed.

---

## 33. Determinism

For identical frozen inputs and configuration, the policy decision must be identical.

Do not use randomness, process order, dictionary iteration order, or wall-clock time as hidden decision inputs.

Wall-clock values may be evaluated only when explicitly supplied as decision-time state, such as retry cooldown checks.

Where reproducibility is required, the policy decision ID must be derived deterministically from canonical decision inputs/configuration.

---

## 34. Fail-Closed Behavior

Examples:

```text
missing policy configuration      → explicit configuration error / BLOCK
invalid action                    → BLOCK
invalid model output              → BLOCK
unknown state                     → RECONCILIATION_REQUIRED
untrusted event                   → reject / BLOCK
mismatched approval               → BLOCK
expired approval                  → BLOCK
incompatible artifact             → reject load
```

Missing information must never become permission.

---

## 35. Sensitive-Data Boundary

Policy evaluation and traces must use only necessary data.

Do not log or persist:

- full card numbers;
- secrets;
- credentials;
- webhook signing secrets;
- unnecessary customer PII.

Prefer stable identifiers, reason codes, and structured evidence.

---

## 36. Evaluation Separation

Live policy evaluation and evaluator-side simulator analysis must remain separate.

Evaluator-only analysis may use:

```text
EvaluationTruthRecord
potential_outcomes
oracle_action
realized outcome
```

but those values must never enter the live policy engine's decision path.

---

## 37. Evaluation Metrics

Report at minimum:

```text
policy allow rate
policy block rate
human approval rate
constraint violation count
ineligible selection rate
captured-payment protection count
invalid-model-output rejection count
duplicate protection count
retry-limit block count
cooldown block count
same-action-limit block count
total-intervention-limit block count
high-value approval count
low-confidence approval count
reconciliation-required count
idempotency-conflict count
```

Distinguish legitimate policy blocks from actual policy violations.

A safe policy block is not an implementation failure.

---

## 38. Segment Evaluation

Evaluate policy behavior across:

```text
scenario_family
payment_method
payment_value_tier
scenario_difficulty
failure_diagnosis
diagnosis_confidence_tier
selected_action
policy_outcome
policy_reason
seed
```

Additional useful segments:

```text
retry_count_bucket
intervention_count_bucket
approval_required
stale_state
model_validity
```

Always report support counts.

---

## 39. Distribution Shift

Compare in-distribution and shifted governed benchmarks for:

```text
allow rate
block rate
approval rate
constraint violations
captured-payment blocks
invalid-output blocks
reconciliation rate
action distribution after policy
```

Do not tune production policy thresholds against the held-out benchmark.

Any changed policy configuration must receive a new version.

---

## 40. Error Analysis

Identify at minimum:

```text
wrong policy outcomes vs expected safety behavior
high-confidence policy mistakes
negative-utility attempts that were incorrectly permitted
near-threshold decisions
policy-filtered Phase 9 selections
stale-state protections
model-failure protections
shift-sensitive policy behavior
```

Each evaluator-side case should preserve enough context to explain the decision without leaking simulator truth into the live path.

---

## 41. Source Tree

Expected implementation package:

```text
src/apro/policy/
├── __init__.py
├── enums.py
├── models.py
├── config.py
├── rules.py
├── engine.py
├── validation.py
├── approvals.py
├── idempotency.py
├── state_guard.py
├── traces.py
├── artifacts.py
├── evaluation.py
└── reports.py
```

Expected tests:

```text
tests/policy/
├── __init__.py
├── test_taxonomy.py
├── test_config.py
├── test_rules.py
├── test_engine.py
├── test_state_guard.py
├── test_validation.py
├── test_approvals.py
├── test_idempotency.py
├── test_traces.py
├── test_artifacts.py
├── test_evaluation.py
├── test_distribution_shift.py
├── test_reproducibility.py
├── test_leakage_policy.py
└── test_reports.py
```

Acceptance runner:

```text
scripts/run_phase_10_acceptance.py
```

Modules may be consolidated if the contracts remain explicit and independently testable.

---

## 42. Automated Test Requirements

### Taxonomy

- policy outcome enumeration;
- deterministic reason codes;
- deterministic rule identifiers;
- schema/version checks.

### Configuration

- valid configurations accepted;
- invalid thresholds rejected;
- invalid precedence rejected;
- incompatible versions rejected;
- deterministic identity excludes `created_at`.

### Hard safety rules

- captured payment always blocked;
- invalid event blocked/rejected;
- duplicate event protected;
- unsupported action blocked;
- invalid model output blocked.

### Retry controls

- max retry rejection;
- cooldown rejection/defer;
- same-action repetition rejection;
- total intervention limit.

### Approval

- required approval is enforced;
- approval binds to case;
- approval binds to decision;
- approval binds to action;
- mismatch rejected;
- expiration rejected;
- incompatible policy version rejected.

### State

- captured state beats economic value;
- unknown state cannot authorize;
- stale event cannot overwrite current captured state;
- final current-state recheck works.

### Idempotency

- duplicate authorization identity rejected;
- distinct execution attempts remain distinguishable.

### Payment Link

- capacity limit enforced;
- duplicate link protection enforced.

### Model failures

- Model A failure fallback;
- Model B failure fallback;
- no fabricated outputs.

### Artifact

- save/load equality;
- compatibility rejection;
- deterministic identity;
- truthful creation metadata.

### Leakage

Prove that the live policy engine cannot access:

```text
EvaluationTruthRecord
potential_outcomes
oracle action
future outcomes
hidden customer intent
latent bank condition
```

unless those fields are passed through an explicitly evaluator-only path.

### Reproducibility

Frozen inputs/configuration must reproduce canonical policy outputs and traces, excluding explicitly wall-clock-only metadata.

---

## 43. Manual Acceptance Scenarios

Implement and pass at least these 12 cases:

```text
CASE 1 — Captured Payment
A captured payment must BLOCK automatic recovery.

CASE 2 — Invalid Event
An untrusted/invalid webhook must not authorize recovery.

CASE 3 — Duplicate Event
A duplicate event must not authorize a second external action.

CASE 4 — Retry Limit
A retry at/above MAX_RETRIES must be blocked.

CASE 5 — Retry Cooldown
A retry during an active cooldown must be blocked/deferred.

CASE 6 — High Value
A high-value case must require human approval when configured.

CASE 7 — Low Confidence
A low-confidence case must not authorize automatic recovery.

CASE 8 — Invalid Model Output
An invalid probability or recovered amount must be rejected.

CASE 9 — Stale State
A payment.failed event after trusted payment.captured must not authorize recovery.

CASE 10 — Approval Mismatch
Approval for PAYMENT_LINK must not authorize RETRY.

CASE 11 — Intervention Limit
Exhausted intervention budget must prevent another active intervention.

CASE 12 — Reproducibility
Identical frozen input/configuration and reloaded policy artifact must produce identical policy decisions.
```

Each case must assert both the outcome and the relevant reason code/evidence.

---

## 44. Acceptance Criteria

Phase 10 passes only when all of these are genuinely verified:

```text
AC-01  Explicit ALLOW / BLOCK / REQUIRE_HUMAN_APPROVAL outcomes
AC-02  Deterministic rule precedence
AC-03  Captured-payment hard block
AC-04  Invalid-event protection
AC-05  Duplicate-event protection
AC-06  Unsupported-action protection
AC-07  Invalid-model-output rejection
AC-08  Retry-limit enforcement
AC-09  Retry cooldown enforcement
AC-10  Same-action repetition protection
AC-11  Total intervention limit enforcement
AC-12  High-value protection
AC-13  Low-confidence protection
AC-14  Minimum ERV protection
AC-15  Negative-ERV protection
AC-16  STOP and ESCALATE handling
AC-17  Human approval integrity
AC-18  Final current-state recheck
AC-19  Stale/out-of-order protection
AC-20  Reconciliation/unknown-state handling
AC-21  Idempotency protection
AC-22  Payment Link capacity/duplication protection
AC-23  Model failure fail-safe behavior
AC-24  Version/schema compatibility
AC-25  Complete policy trace
AC-26  Policy artifact persistence and reload
AC-27  Deterministic policy identity
AC-28  Bit-for-bit reproducibility
AC-29  Policy safety metrics
AC-30  Segment evaluation
AC-31  Distribution-shift evaluation
AC-32  Leakage prevention
AC-33  Zero policy constraint violations in governed evaluation
AC-34  Zero execution side effects
AC-35  Zero outbound effects
AC-36  Automated policy tests
AC-37  Manual acceptance suite
AC-38  Full Phase 0–9 regression compatibility
```

The acceptance runner must contain real assertions and observed measurements. Never hardcode PASS values.

---

## 45. Quality Gates

Required:

```powershell
.venv\Scripts\pytest.exe -v tests/policy/
.venv\Scripts\pytest.exe -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\mypy.exe src
```

Manual acceptance:

```powershell
.venv\Scripts\python.exe .\scripts\run_phase_10_acceptance.py
```

The acceptance run must demonstrate:

- all criteria pass;
- all manual cases pass;
- zero execution calls;
- zero outbound network/Razorpay/customer effects;
- deterministic reproducibility;
- no live-path truth leakage.

---

## 46. Generated Evidence

Acceptance may create:

```text
artifacts/policy/
├── policy_artifact.json
├── policy_manifest.json
├── policy_evaluation.json
├── policy_evaluation.md
├── policy_trace.jsonl
├── policy_reason_counts.json
└── policy_safety_metrics.json
```

These are generated evidence, not source code. Do not automatically add them to the source commit unless explicitly approved.

---

## 47. Git / Provenance Boundary

Phase 10 must not silently modify completed Phase 0–9 files.

Before staging, verify:

```powershell
git status --short --untracked-files=all
git diff --name-only
git diff --stat
git diff --cached --name-only
```

The Phase 10 commit must contain only approved Phase 10 implementation/specification/test/acceptance files and separately approved shared-file changes.

Never stage:

```text
.venv/
artifacts/
local credentials
database files
temporary logs
scratch files
```

---

## 48. Implementation Stop Conditions

Antigravity must stop and report if:

- a policy threshold must be invented;
- a Phase 0–9 contract must change;
- Phase 9 behavior must be silently redesigned;
- a real external call is required to prove a safety invariant;
- simulator truth is required by the live policy path;
- an authority boundary is ambiguous;
- a safety rule conflicts with the economic engine;
- the implementation would allow execution despite an unresolved hard safety condition.

---

## 49. Deliverables

Required:

```text
docs/PHASE_10_POLICY_AND_SAFETY_ENGINE_SPECIFICATION.md
src/apro/policy/
tests/policy/
scripts/run_phase_10_acceptance.py
```

Optional local/generated evidence:

```text
artifacts/policy/
```

At phase closure provide:

1. implementation summary;
2. exact changed-file list;
3. automated test results;
4. quality-gate results;
5. manual acceptance output;
6. policy artifact identity;
7. reproducibility result;
8. safety/constraint metrics;
9. Git provenance report;
10. explicit phase-boundary confirmation.

---

## 50. Phase 11 Handoff

Phase 10 ends at a permission contract:

```text
Policy Decision
```

Phase 11 begins at:

```text
Policy Decision
        ↓
Execution Framework
```

The Phase 10 contract must let Phase 11 determine:

```text
whether execution is permitted
which action is permitted
whether human approval is required
whether reconciliation is required
which idempotency identity applies
which policy/rule version authorized the action
why it was permitted or blocked
```

Phase 10 must never invoke a real executor.

---

## 51. Final Architectural Invariant

After Phase 10, the APRO chain is:

```text
Webhook
   ↓
Verification
   ↓
Canonical Event
   ↓
Recovery Case
   ↓
Model A — Failure Diagnosis
   ↓
Model B — Recovery Outcome Prediction
   ↓
Phase 9 — Economic Decision
   ↓
Phase 10 — Policy & Safety Gate
   ↓
Phase 11 — Execution Framework
```

The crucial separation is:

```text
AI prediction
    ≠
economic preference
    ≠
permission
    ≠
execution
```

Each boundary must remain independently testable, versioned, auditable, and fail-closed.

---

## 52. Closure Rule

Phase 10 may be declared complete only when:

```text
Implementation complete
        AND
Targeted policy tests green
        AND
Full regression green
        AND
Ruff green
        AND
Formatter green
        AND
Mypy green
        AND
Manual acceptance green
        AND
Zero execution side effects
        AND
Zero outbound effects
        AND
Leakage boundary verified
        AND
Artifact compatibility verified
        AND
Reproducibility verified
        AND
Git provenance clean
```

Only then may Phase 11 begin.
