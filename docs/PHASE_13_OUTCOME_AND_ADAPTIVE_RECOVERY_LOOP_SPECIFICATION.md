# APRO — PHASE 13 SPECIFICATION
## Outcome & Adaptive Recovery Loop

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 13 — Outcome & Adaptive Recovery Loop  
**Architecture Leads:** Vidisha + GPT  
**Implementation Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation Planning  
**Baseline:** Phase 12 — Razorpay TEST-Mode Provider Integration & External Adapter Boundary  
**Phase 12 Baseline Commit:** `b1dfa36`  
**Repository:** `C:\APRO`  
**Branch:** `main`

---

# 1. Purpose

Phase 13 closes APRO's recovery loop.

Up to Phase 12, APRO can:

```text
observe a failed payment
→ diagnose the failure
→ predict action outcomes
→ select an economically preferred action
→ apply deterministic safety/policy
→ authorize execution
→ execute through a provider/simulation boundary
```

Phase 13 adds the missing post-execution control loop:

```text
Execution
    ↓
Outcome Observation
    ↓
Outcome Classification
    ↓
Recovery Case Update
    ↓
Explicit Disposition
    ├── RECOVERED / COMPLETE
    ├── STOP / TERMINATE
    ├── ESCALATE / TERMINATE
    ├── WAIT / OBSERVE
    └── RE-EVALUATE
             ↓
       Fresh Observable Context
             ↓
       Phase 7 Diagnosis (if required)
             ↓
       Phase 8 Outcome Prediction
             ↓
       Phase 9 Economic Decision
             ↓
       Phase 10 Policy & Safety
             ↓
       Phase 11 Execution
             ↓
       Phase 12 Provider / Simulation
             ↓
       Observe again
```

The central objective is:

> **Adapt based on observed outcomes, but never bypass the existing decision, policy, safety, or execution authorities.**

---

# 2. Authority Hierarchy

Implementation must follow:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. Completed Phase 0–12 specifications and verified implementations
10. This specification

If a conflict is discovered:

```text
STOP
  ↓
Document conflict
  ↓
Report to Vidisha + GPT
  ↓
Architecture decision
  ↓
Specification update if required
  ↓
Continue
```

Antigravity must not independently redesign APRO.

---

# 3. Source-Derived Phase 13 Contract

The authoritative Implementation Master Plan defines Phase 13 as:

**Outcome & Adaptive Recovery Loop**

Objective:

> **Close the loop.**

Required flow:

```text
Execution
    ↓
Outcome
    ↓
Case Update
    ↓
Re-evaluation
```

Required capabilities:

- successful recovery;
- failed recovery;
- pending outcome;
- re-evaluation;
- stopping;
- escalation;
- action-history awareness.

Required adaptive demonstration:

```text
Action 1
    ↓
Failure
    ↓
Re-evaluation
    ↓
Action 2
    ↓
Recovery
```

The same failed action must not simply be repeated blindly.

---

# 4. Architectural Position

Phase 13 is a controller/orchestration layer. It is not a replacement for:

- Phase 7 diagnosis;
- Phase 8 recovery outcome prediction;
- Phase 9 economic action selection;
- Phase 10 policy and safety;
- Phase 11 execution;
- Phase 12 provider transport.

The authority chain remains:

```text
Observed Facts
    ↓
Phase 7 Diagnosis
    ↓
Phase 8 Outcome Prediction
    ↓
Phase 9 Economic Decision
    ↓
Phase 10 Policy Permission
    ↓
Phase 11 Execution
    ↓
Phase 12 Provider / Simulation
    ↓
Phase 13 Outcome
    ↓
Fresh Context / Re-evaluation
    ↓
Phase 7/8/9/10/11 again
```

Phase 13 may decide that a **new decision cycle should occur**. It may not select the next action itself.

---

# 5. Core Invariants

## 5.1 Execution != Recovery

A provider/executor success means an action completed according to the executor contract.

It does not by itself prove revenue was recovered.

Recovery must be supported by observed evidence.

---

## 5.2 Outcome is Evidence, Not Authority

The outcome may change the next decision context.

It cannot authorize a new action.

---

## 5.3 Re-Evaluation != Re-Execution

`RE_EVALUATE` means:

```text
refresh context
→ optionally re-diagnose
→ refresh outcome predictions
→ recompute economics
→ obtain new policy decision
```

It does not mean:

```text
execute another action immediately
```

---

## 5.4 No Blind Repetition

A previously failed action must be represented in the next decision context.

Immediate repetition without fresh justification is prohibited.

---

## 5.5 Terminal Cases Stay Terminal

After:

```text
RECOVERED
STOPPED
ESCALATED
```

the case cannot re-enter the adaptive loop.

Existing domain state-machine enforcement is authoritative.

---

# 6. Scope

## 6.1 In Scope

Phase 13 implements:

1. Outcome observation input boundary.
2. Outcome classification.
3. Outcome persistence through existing `Outcome`.
4. Case-state advancement.
5. Explicit loop disposition.
6. Action-history awareness.
7. Re-evaluation eligibility.
8. Bounded adaptive control.
9. Re-entry into Phase 7/8/9/10/11 where required.
10. Successful recovery.
11. Failed recovery.
12. Pending outcome.
13. Expiration.
14. STOP.
15. ESCALATE.
16. No-blind-repetition handling.
17. Outcome idempotency.
18. Concurrent processing safety.
19. Final state safety before every new execution.
20. Simulation/stub-based adaptive testing.
21. Acceptance runner.
22. Regression and quality validation.

## 6.2 Explicitly Out of Scope

Phase 13 MUST NOT implement:

- a new action-ranking algorithm;
- a second economic decision engine;
- a second policy engine;
- a second execution framework;
- new Razorpay adapters;
- production provider integration;
- reinforcement learning;
- bandits;
- online policy learning;
- automatic model retraining;
- self-modifying policy;
- dashboard functionality;
- full Phase 14 audit/observability infrastructure;
- Phase 15 benchmark infrastructure;
- Phase 17 adversarial campaign infrastructure.

---

# 7. Existing Domain Contract

The existing domain contains the required outcome vocabulary.

`Outcome`:

```text
outcome_id
case_id
execution_id
type
amount_recovered
evidence_reference
observed_at
```

`OutcomeType`:

```text
RECOVERED
FAILED
PENDING
EXPIRED
STOPPED
ESCALATED
```

Do not create a competing persistent outcome taxonomy.

Existing RecoveryCase terminal states are:

```text
RECOVERED
STOPPED
ESCALATED
```

Existing relevant non-terminal state:

```text
OBSERVING
EVALUATING
```

Existing action history is represented by:

```text
RecoveryAction
Execution
Outcome
RecoveryCase
```

Prefer these existing entities over a duplicate history store.

---

# 8. Execution Status vs Outcome Type

The loop must preserve:

```text
ExecutionStatus
```

as distinct from:

```text
OutcomeType
```

Execution statuses:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
UNKNOWN
CANCELLED
```

Outcome types:

```text
RECOVERED
FAILED
PENDING
EXPIRED
STOPPED
ESCALATED
```

Examples:

```text
ExecutionStatus.SUCCEEDED
+
payment.captured
→ RECOVERED
```

```text
ExecutionStatus.SUCCEEDED
+
no recovery evidence yet
→ PENDING
```

```text
ExecutionStatus.UNKNOWN
+
no definitive evidence
→ PENDING
```

Never equate executor success with revenue recovery.

---

# 9. Outcome Evidence Boundary

Phase 13 consumes normalized evidence.

Allowed evidence sources:

```text
normalized PaymentEvent
trusted Payment state
normalized provider evidence
ExecutionResult
simulation outcome
explicit test/stub evidence
```

Raw provider JSON must not be parsed inside the recovery-loop layer.

Provider-specific normalization remains downstream of Phase 12.

---

# 10. Razorpay Outcome Evidence

Current official Razorpay documentation provides payment state webhook events including:

```text
payment.authorized
payment.captured
payment.failed
```

Razorpay also documents Payment Link webhook events including:

```text
payment_link.paid
payment_link.partially_paid
payment_link.cancelled
payment_link.expired
```

These are provider facts that can be normalized into APRO's outcome/evidence boundary.

Razorpay specifically documents that payment status changes can be observed through webhook events and that Payment Link events expose payment-link status changes. The current official documentation must be rechecked during implementation for any provider-specific mapping details.

---

# 11. Outcome Resolution

The Outcome Processor must classify only what current evidence proves.

Conservative precedence:

```text
verified payment/recovery success
    ↓
RECOVERED

explicit terminal STOP
    ↓
STOPPED

explicit human escalation
    ↓
ESCALATED

verified expiration
    ↓
EXPIRED

definitive failed recovery
    ↓
FAILED

no definitive evidence yet
    ↓
PENDING
```

The most important rule:

> **Do not classify RECOVERED merely because execution succeeded.**

---

# 12. Explicit Disposition

Phase 13 introduces an explicit control disposition distinct from `OutcomeType`.

Recommended vocabulary:

```text
WAIT_FOR_OUTCOME
RE_EVALUATE
STOP
ESCALATE
COMPLETE
```

This is an implementation/control contract, not a replacement for the domain OutcomeType taxonomy.

### WAIT_FOR_OUTCOME

Additional evidence is required.

No new intervention occurs.

### RE_EVALUATE

A fresh decision cycle is justified.

The controller returns to the existing decision chain.

### STOP

Terminate intentional recovery processing.

### ESCALATE

Terminate automation and route to human review.

### COMPLETE

Recovery is confirmed; the case is terminal.

---

# 13. Disposition Is Not Permission

The following distinction is mandatory:

```text
RE_EVALUATE
≠
ALLOW
```

A re-evaluation still needs:

```text
Phase 9
    ↓
Phase 10
    ↓
Phase 11
```

Likewise:

```text
STOP
```

is a control outcome, not an error.

---

# 14. Recovery Case State Transitions

Use existing domain transitions.

Required semantics:

```text
OBSERVING → RECOVERED
```

when recovery is confirmed.

```text
OBSERVING → EVALUATING
```

when failure occurred and continuation is eligible.

```text
OBSERVING → STOPPED
```

when no further automated continuation is permitted.

```text
OBSERVING → ESCALATED
```

when human review is required.

Do not directly assign state values in ways that bypass domain transition functions.

---

# 15. Action History

Before re-evaluation, the loop must expose sufficient historical context.

At minimum:

```text
action_id
action_type
execution_id
execution_status
outcome_type
observed_at
provider_reference where safe
attempt order
```

The next decision context must be able to answer:

```text
What was attempted?
Was execution successful?
What happened after execution?
How many attempts have occurred?
Which actions have failed?
Which actions have succeeded?
```

---

# 16. No-Blind-Repetition Rule

Required behavior:

```text
Action A
→ FAILED
→ persist outcome
→ update history
→ re-evaluate
```

The next decision must not repeat Action A blindly.

Preferred implementation:

```text
history-aware candidate context/eligibility
```

rather than a hard-coded Action B.

If Phase 9 legitimately selects the same action again, the repeat must be explainable by materially changed context and must pass a fresh Phase 10 policy decision.

Phase 13 must never force:

```text
Action A → Action B
```

independently of Phase 9.

---

# 17. Re-Evaluation Context

Fresh context should include, where available:

```text
payment current state
latest trusted event
latest diagnosis
latest execution
latest outcome
attempt count
previous actions
previous outcomes
elapsed time
provider reference
decision-time customer/payment context
available execution mechanisms
```

Do not include:

```text
potential_outcomes
oracle_action
hidden recoverability
future latent state
```

from the simulation engine.

---

# 18. Re-Diagnosis

A failed action does not automatically require re-diagnosis.

Phase 13 may re-use the existing diagnosis or request Phase 7 to produce a new diagnosis.

The choice must be deterministic and based on new observable evidence.

No new diagnosis model may be invented.

---

# 19. Re-Prediction

When a new decision cycle occurs, Phase 8 must use the updated context.

Conceptually:

```text
fresh context
+
candidate action
→
P(success | context, action)
```

Phase 13 must not manufacture or alter Model B predictions.

---

# 20. Re-Decision Authority

Phase 9 remains the only action-selection authority.

Correct:

```text
Phase 13 → request re-evaluation
Phase 7/8 → refresh intelligence
Phase 9 → select action
Phase 10 → authorize
Phase 11 → execute
```

Incorrect:

```text
Phase 13 → choose Action 2
```

This distinction must be explicit in code and tests.

---

# 21. Policy Re-Entry

Every new recovery action from re-evaluation must receive a new policy decision.

Do not reuse an old `ALLOW`.

A policy decision authorizes a particular execution context.

---

# 22. Execution Re-Entry

Every new recovery action must use Phase 11.

Required:

```text
new PolicyDecision
    ↓
ApprovedExecutionRequest
    ↓
StateGuard
    ↓
idempotency
    ↓
execute
```

Phase 13 must never invoke Phase 12 provider transport directly.

---

# 23. Final State Recheck

Before every new externally meaningful action:

```text
new decision
→ policy
→ Phase 11 final StateGuard
→ execution
```

must remain intact.

Example:

```text
Action 1 FAILED
    ↓
re-evaluation
    ↓
payment CAPTURED
    ↓
StateGuard
    ↓
zero Action 2 execution
```

---

# 24. Loop Boundedness

The loop must have a finite termination mechanism.

Use existing safety/policy controls whenever possible:

```text
maximum interventions
maximum attempts
same-action limits
minimum ERV
no remaining eligible actions
policy block
case expiration
escalation
```

Do not introduce conflicting duplicate policy thresholds.

Do not implement:

```python
while recoverable:
    re_evaluate()
    execute()
```

with no finite bound.

Any Phase 13-specific bound must be deterministic and versioned.

---

# 25. STOP Conditions

Terminate when:

```text
payment recovered/captured
no permissible action remains
attempt/intervention limit reached
expected value insufficient
case expired
policy blocks continuation
explicit STOP chosen
```

STOP is a valid control outcome.

---

# 26. ESCALATE Conditions

Support human escalation for:

```text
repeated failed recovery
persistent ambiguity
conflicting evidence
high-value uncertainty
policy-driven human review
```

Reuse the existing Phase 11 escalation mechanism.

No automatic financial action continues after escalation without a separately authorized human workflow.

---

# 27. Pending Outcome Handling

Pending means:

> **The available evidence is insufficient to declare recovery or definitive failure.**

Example:

```text
Payment Link created
→ customer has not paid
→ PENDING
→ WAIT_FOR_OUTCOME
```

Do not launch another action simply because the first outcome is pending.

The case must remain observable.

---

# 28. Unknown Execution Handling

When:

```text
ExecutionStatus.UNKNOWN
```

the loop must not automatically classify it as:

```text
OutcomeType.FAILED
```

It should remain pending/indeterminate until trustworthy evidence resolves the state.

This is particularly important for provider/network ambiguity.

---

# 29. Expiration

When trustworthy evidence establishes expiration:

```text
OutcomeType.EXPIRED
```

may be persisted.

The loop then terminates through:

```text
STOP
```

or:

```text
ESCALATE
```

according to applicable policy/operations semantics.

---

# 30. Outcome Idempotency

Duplicate outcome evidence must not:

```text
create duplicate Outcome
advance case twice
trigger duplicate re-evaluation
create duplicate execution
create duplicate Payment Link
create duplicate escalation
```

Use authoritative identities such as:

```text
provider event identity
execution_id + normalized evidence identity
outcome_id
```

Reuse existing event-deduplication mechanisms.

---

# 31. Concurrency

Outcome processing may race with:

```text
new webhook
payment capture
another worker
duplicate provider event
new execution
```

For one logical outcome:

```text
multiple workers
    ↓
one durable logical advancement
```

Use existing PostgreSQL transaction/uniqueness patterns.

---

# 32. Atomic Advancement

Where practical:

```text
persist Outcome
+
advance RecoveryCase
+
persist disposition
```

should form one atomic logical operation.

If an external observation prevents full atomicity, the durable state must remain recoverable and idempotent.

---

# 33. Loop Identity

Each adaptive cycle requires a deterministic identity.

Conceptually:

```text
case_id
+
cycle/attempt number
+
prior execution/outcome identity
```

Do not depend solely on random IDs or wall-clock time.

---

# 34. Canonical Execution Sequence

The canonical sequence is:

```text
1. Observe execution result / new evidence.
2. Resolve current Outcome.
3. Persist immutable Outcome.
4. Update RecoveryCase.
5. Update action history.
6. Resolve explicit disposition.

7. If COMPLETE:
       terminate with RECOVERED.

8. If STOP:
       terminate with STOPPED.

9. If ESCALATE:
       terminate automation with ESCALATED.

10. If WAIT_FOR_OUTCOME:
        remain observable.

11. If RE_EVALUATE:
        build fresh context
        → re-diagnose if required
        → refresh predictions
        → Phase 9 decision
        → Phase 10 policy
        → Phase 11 execution
        → Phase 12 provider/simulation
        → observe again.
```

No step may shortcut a higher-authority phase.

---

# 35. Real vs Simulated Outcome Provenance

Each outcome should preserve provenance through the existing domain/audit-ready references.

Where applicable distinguish:

```text
RAZORPAY
SIMULATOR
SYSTEM
```

or corresponding existing `AuditActor` semantics.

A simulation result must never be represented as real provider evidence.

---

# 36. Simulation Leakage Boundary

Simulation is allowed to generate outcomes.

Phase 13 can consume:

```text
normalized outcome
```

but MUST NOT consume:

```text
potential_outcomes
oracle_action
hidden recoverability
future latent state
```

Acceptance tests must deliberately verify this boundary.

---

# 37. Immutability

Historical records remain immutable:

```text
Decision
PolicyDecision
Execution
Outcome
```

Phase 13 updates mutable:

```text
RecoveryCase
```

state.

A second adaptive cycle creates new historical records rather than mutating the first cycle.

---

# 38. Version Provenance

Each re-evaluation cycle must preserve the versions used for that cycle:

```text
diagnosis model version
outcome model version
decision/model version
policy version
rule-set version
execution mode
```

Never overwrite earlier cycle provenance.

---

# 39. Provider Neutrality

Provider-specific parsing remains in Phase 12.

Phase 13 accepts normalized evidence only.

The recovery loop must not import raw Razorpay transport models merely to interpret outcomes.

---

# 40. Error Handling

Fail closed on:

```text
invalid evidence
entity mismatch
terminal case
invalid downstream decision
policy failure
execution authorization failure
```

Safe fallbacks include:

```text
WAIT_FOR_OUTCOME
STOP
ESCALATE
```

according to the authoritative semantics.

Never turn malformed evidence into successful recovery.

---

# 41. Security

No Phase 13 model or result may contain:

```text
provider credentials
authorization headers
secret keys
raw secret-bearing payloads
simulator hidden truth
```

Only safe evidence references should be retained.

---

# 42. Phase 14 Boundary

Phase 13 should preserve:

```text
case_id
action_id
decision_id
policy_decision_id
execution_id
outcome_id
provider_reference
```

for future reconstructability.

But full:

```text
structured logging
correlation framework
audit reconstruction
observability dashboards
```

remain Phase 14.

---

# 43. Phase 15 Boundary

Phase 13 must create clean outcome histories that Phase 15 can evaluate.

It must not implement:

```text
1,000+ case final benchmark
baseline comparison framework
statistical reporting
```

in this phase.

---

# 44. Phase 16 Boundary

No dashboard implementation.

Expose backend state that Phase 16 can visualize later.

---

# 45. Phase 17 Boundary

Basic Phase 13 safety tests are mandatory:

```text
duplicate outcome
concurrent processing
terminal replay
unknown execution
bounded loop
no-blind repetition
capture race
```

Comprehensive adversarial testing remains Phase 17.

---

# 46. Proposed Logical Package

A reasonable logical structure is:

```text
src/apro/recovery_loop/
    __init__.py
    enums.py
    models.py
    outcomes.py
    dispositions.py
    history.py
    context.py
    guards.py
    controller.py
    exceptions.py
```

Adapt to repository conventions.

Do not duplicate existing domain or execution components.

---

# 47. Suggested Contracts

Conceptual only; follow repository patterns:

```python
class RecoveryLoopDisposition(StrEnum):
    WAIT_FOR_OUTCOME = "WAIT_FOR_OUTCOME"
    RE_EVALUATE = "RE_EVALUATE"
    STOP = "STOP"
    ESCALATE = "ESCALATE"
    COMPLETE = "COMPLETE"
```

And:

```python
class OutcomeProcessingResult(BaseModel):
    outcome: Outcome
    disposition: RecoveryLoopDisposition
    case_status: RecoveryCaseStatus
    re_evaluation_id: str | None
```

These names may be adapted if the repository already has equivalent types.

---

# 48. Outcome Processor Responsibilities

The Outcome Processor should:

1. validate case/execution/entity bindings;
2. determine the strongest supported outcome;
3. create an immutable Outcome;
4. reject/deduplicate duplicate outcome evidence;
5. advance RecoveryCase via existing domain transitions;
6. update/consult action history;
7. produce an explicit disposition.

It must NOT independently select the next recovery action.

---

# 49. Recovery Loop Controller Responsibilities

The Recovery Loop Controller should:

```text
receive outcome
→ call OutcomeProcessor
→ determine whether terminal/wait/re-evaluate
→ if re-evaluate, construct fresh context
→ invoke the existing downstream decision chain
```

It must not contain an alternative copy of Phase 9 or Phase 10.

---

# 50. Adaptive End-to-End Contract

A valid adaptive path is:

```text
Payment Failure
      ↓
Decision 1
      ↓
Policy 1
      ↓
Action 1
      ↓
Execution 1
      ↓
Outcome 1 = FAILED
      ↓
Outcome persisted
      ↓
History updated
      ↓
Case = EVALUATING
      ↓
Fresh context
      ↓
Phase 7/8 refresh as required
      ↓
Phase 9 Decision 2
      ↓
Policy 2
      ↓
Action 2
      ↓
Execution 2
      ↓
Outcome 2 = RECOVERED
      ↓
Case = RECOVERED
```

The acceptance test must prove that Action 2 originated from the Phase 9 decision engine.

---

# 51. Anti-Cheating Rule

This is NOT sufficient:

```text
if action1_failed:
    action2 = PAYMENT_LINK
```

The implementation fails architecture review if it directly hard-codes replacement actions.

Valid proof requires:

```text
failure observed
→ context updated
→ existing decision engine called
→ decision output inspected
→ selected action used
```

---

# 52. Acceptance Criteria

## Outcome Handling

**AC-01** — Execution status is distinct from recovery outcome.

**AC-02** — RECOVERED requires reliable recovery evidence.

**AC-03** — Definitive failed recovery maps to FAILED.

**AC-04** — Pending evidence maps to PENDING.

**AC-05** — Expiration maps to EXPIRED.

**AC-06** — STOP maps to STOPPED.

**AC-07** — Escalation maps to ESCALATED.

## Case Lifecycle

**AC-08** — OBSERVING → RECOVERED works.

**AC-09** — OBSERVING → EVALUATING works when continuation is eligible.

**AC-10** — OBSERVING → STOPPED works.

**AC-11** — OBSERVING → ESCALATED works.

**AC-12** — Terminal cases cannot reopen.

## Disposition

**AC-13** — Every processed outcome produces an explicit disposition.

**AC-14** — WAIT_FOR_OUTCOME causes zero additional recovery execution.

**AC-15** — RE_EVALUATE returns to the existing decision chain.

**AC-16** — STOP terminates automation safely.

**AC-17** — ESCALATE terminates automation and routes to human review.

**AC-18** — COMPLETE terminates confirmed recovery.

## Adaptation

**AC-19** — Prior action/outcome is persisted before re-evaluation.

**AC-20** — Next decision receives action/outcome history.

**AC-21** — Failed actions are not blindly repeated.

**AC-22** — Re-evaluation uses fresh observable context.

**AC-23** — Re-diagnosis behavior is deterministic.

**AC-24** — Phase 8 predictions are refreshed when required.

**AC-25** — Phase 9 remains the sole action-selection authority.

## Policy / Execution Safety

**AC-26** — Every new action receives a new Phase 10 policy decision.

**AC-27** — Previous ALLOW cannot authorize a changed later action.

**AC-28** — Phase 11 StateGuard remains mandatory.

**AC-29** — Captured payment blocks later execution.

**AC-30** — Policy BLOCK prevents adaptive dispatch.

## Boundedness

**AC-31** — Adaptive processing has an explicit finite bound.

**AC-32** — Attempt/intervention limits are honored.

**AC-33** — Same-action repetition limits are honored.

**AC-34** — No eligible continuation terminates instead of looping indefinitely.

## Idempotency / Concurrency

**AC-35** — Duplicate outcomes do not create duplicate Outcome records.

**AC-36** — Duplicate outcomes do not trigger duplicate re-evaluation.

**AC-37** — Concurrent processing produces one logical advancement.

## Pending / Unknown

**AC-38** — Pending outcomes remain observable without immediate extra execution.

**AC-39** — UNKNOWN execution is not automatically converted to FAILED.

## Leakage / Provenance

**AC-40** — Simulator latent truth cannot reach runtime loop logic.

**AC-41** — Real vs simulated outcome provenance is preserved.

**AC-42** — Historical decisions/executions/outcomes remain immutable.

## Determinism

**AC-43** — Disposition resolution is deterministic.

**AC-44** — Loop/re-evaluation identity is deterministic.

## Compatibility

**AC-45** — Phase 10 behavior remains unchanged.

**AC-46** — Phase 11 behavior remains compatible.

**AC-47** — Phase 12 provider boundary remains compatible.

**AC-48** — Simulation behavior remains compatible.

**AC-49** — Full Phase 0–12 regression remains green.

## Security / Boundary

**AC-50** — No secrets enter outcome/loop models.

**AC-51** — Provider-specific parsing remains outside the recovery-loop layer.

**AC-52** — No second policy engine exists.

**AC-53** — No second economic decision engine exists.

**AC-54** — No bypass of Phase 10 or Phase 11 exists.

## Acceptance / Provenance

**AC-55** — Acceptance runner genuinely verifies mandatory criteria.

**AC-56** — Manual acceptance scenarios are executable and documented.

**AC-57** — Quality gates pass.

**AC-58** — Git provenance is clean and reviewed.

---

# 53. Manual Acceptance Scenarios

At minimum:

### Scenario 1 — Successful Recovery

```text
Action 1
→ execution
→ reliable payment success evidence
→ RECOVERED
→ case terminal
→ zero additional action
```

### Scenario 2 — Failed Action → Adaptive Action

```text
Action 1
→ execution
→ FAILED outcome
→ persist outcome
→ update history
→ EVALUATING
→ fresh context
→ Phase 9 selects Action 2
→ Phase 10 ALLOW
→ Phase 11 execution
→ recovery evidence
→ RECOVERED
```

### Scenario 3 — Failed Action → STOP

```text
Action 1
→ FAILED
→ no eligible continuation
→ STOP
→ STOPPED
```

### Scenario 4 — Failed Action → ESCALATE

```text
Action 1
→ FAILED
→ human-review condition
→ ESCALATE
→ ESCALATED
```

### Scenario 5 — Pending

```text
Action executes
→ no recovery evidence
→ PENDING
→ WAIT_FOR_OUTCOME
→ zero additional recovery execution
```

### Scenario 6 — UNKNOWN Execution

```text
UNKNOWN
→ no false FAILED classification
→ wait/observe
```

### Scenario 7 — Duplicate Outcome

```text
same outcome twice
→ one logical Outcome
→ one case advancement
→ zero duplicate re-evaluations
```

### Scenario 8 — Capture Race

```text
Action 1 fails
→ re-evaluation
→ payment becomes CAPTURED
→ Phase 10/11 safety gate
→ zero Action 2 execution
```

### Scenario 9 — No Blind Repetition

```text
Action 1 = RETRY
→ FAILED
→ fresh decision
→ RETRY not blindly repeated
```

### Scenario 10 — Full Adaptive Chain

```text
Payment Failure
→ Diagnosis
→ Decision 1
→ Policy 1
→ Execute 1
→ Outcome 1 FAILED
→ History update
→ Re-evaluation
→ Decision 2
→ Policy 2
→ Execute 2
→ Outcome 2 RECOVERED
→ Case RECOVERED
```

---

# 54. Acceptance Runner

Create:

```text
scripts/run_phase_13_acceptance.py
```

It MUST:

1. Verify each mandatory AC individually.
2. Use genuine assertions.
3. Verify all explicit dispositions.
4. Prove Action 1 → Failure → Re-evaluation → Action 2 → Recovery.
5. Prove Action 2 originated from Phase 9 output.
6. Verify no-blind-repetition.
7. Verify pending and unknown handling.
8. Verify duplicate outcome idempotency.
9. Verify concurrent outcome handling.
10. Verify capture race safety.
11. Verify new actions re-enter Phase 10.
12. Verify new executions re-enter Phase 11.
13. Verify terminal cases cannot reopen.
14. Verify bounded loop termination.
15. Verify simulator latent isolation.
16. Verify full Phase 0–12 regression.
17. Verify Ruff, format, and Mypy.
18. Report PASS/FAIL individually.
19. Exit non-zero on any mandatory failure.

No placeholder loops.

No unconditional PASS.

No hard-coded fake adaptive sequences.

---

# 55. Required Adaptive Acceptance Evidence

The acceptance evidence should show:

```text
CASE: case_demo_001

Initial payment:
FAILED

Action 1:
RETRY

Execution 1:
FAILED / or successful transport followed by failed recovery outcome

Outcome 1:
FAILED

Disposition:
RE_EVALUATE

History:
RETRY / FAILED

Fresh context:
updated

Phase 9:
invoked again

Decision 2:
ALTERNATE_RECOVERY

Policy 2:
ALLOW

Execution 2:
SUCCEEDED

Outcome 2:
RECOVERED

Final Case:
RECOVERED
```

The actual action names depend on the repository/test fixtures.

The key proof is that the second action comes from the real Phase 9 decision output.

---

# 56. Anti-Leakage Acceptance

Acceptance must attempt to expose simulator truth and prove the loop cannot consume it.

The following must remain unavailable to runtime Phase 13:

```text
potential_outcomes
oracle_action
hidden recoverability
future latent state
```

A test that merely avoids referencing these strings is insufficient if the runtime model can actually receive the hidden data.

The preferred proof is to construct the runtime input from an observable-only contract and verify hidden fields cannot be passed through.

---

# 57. Phase Boundary Acceptance

Acceptance must prove:

```text
Phase 13
    ↓
does not replace Phase 9
does not replace Phase 10
does not replace Phase 11
does not replace Phase 12
```

The source tree should be checked for:

```text
second policy engine
second economic decision engine
direct provider invocation
adaptive recursion without bounds
```

---

# 58. Quality Gates

Before Phase 13 closure:

```powershell
pytest tests/recovery_loop/ -v
pytest tests/policy/ -v
pytest tests/execution/ -v
pytest tests/providers/ -v
pytest tests/ -v
ruff check .
ruff format --check .
mypy src
python scripts/run_phase_13_acceptance.py
```

All mandatory gates must pass.

The exact counts must be reported from actual execution.

---

# 59. Full Regression Requirements

Phase 13 must preserve:

```text
Phase 10 safety
Phase 11 execution
Phase 12 provider integration
Phase 0–9 behavior
```

Particular regression areas:

```text
policy precedence
human approval
StateGuard
idempotency
concurrency
simulation
provider boundary
anti-leakage
determinism
```

---

# 60. Database Requirements

Prefer existing:

```text
outcomes
recovery_cases
recovery_actions
executions
```

and existing transaction infrastructure.

Only add schema if a genuine requirement cannot be represented using existing structures.

If schema changes are necessary:

1. document why;
2. follow Alembic conventions;
3. add migration tests;
4. preserve previous compatibility;
5. report exact migration files.

---

# 61. Stop Conditions

Stop and report to Architecture Leads if:

```text
1. Phase 9 must change to make adaptation work.
2. Phase 10 safety must weaken.
3. Phase 11 must be bypassed.
4. Phase 12 provider logic must move into Phase 13.
5. A new action-selection engine seems necessary.
6. Existing OutcomeType must change.
7. Existing RecoveryCase transitions are insufficient.
8. A finite loop bound cannot be implemented.
9. Simulator hidden truth is required at runtime.
10. Human approval must be bypassed.
```

Do not guess through these conditions.

---

# 62. Git Rules

Vidisha owns commits.

Antigravity MUST NOT:

```text
git commit
git push
git amend
git reset --hard
rewrite history
```

At the end:

```powershell
git status --short --untracked-files=all
git diff --stat
git diff --name-only
git log -3 --oneline
```

Confirm:

```text
Phase 0–12 accidental modifications: 0
Unexpected generated files: 0
Secrets committed: 0
```

Leave the worktree ready for Vidisha's review.

---

# 63. Completion Definition

Phase 13 is complete only when:

```text
[ ] Outcome Processor exists.
[ ] Recovery Loop Controller exists.
[ ] Explicit disposition exists.
[ ] RECOVERED works.
[ ] FAILED works.
[ ] PENDING works.
[ ] EXPIRED works.
[ ] STOPPED works.
[ ] ESCALATED works.
[ ] Action history is available.
[ ] No blind repetition exists.
[ ] Re-evaluation uses fresh observable context.
[ ] Phase 9 remains sole action-selection authority.
[ ] Phase 10 re-authorizes every new action.
[ ] Phase 11 executes every new action.
[ ] Final StateGuard remains mandatory.
[ ] Loop is explicitly bounded.
[ ] Duplicate outcomes are idempotent.
[ ] Concurrent outcome processing is safe.
[ ] Terminal cases cannot reopen.
[ ] UNKNOWN execution does not become false failure.
[ ] PENDING does not trigger immediate duplicate execution.
[ ] Simulator hidden truth remains inaccessible.
[ ] Real/simulated provenance is preserved.
[ ] Historical records remain immutable.
[ ] Full Phase 0–12 regression passes.
[ ] Phase 13 tests pass.
[ ] Acceptance runner genuinely passes.
[ ] Manual acceptance scenarios pass.
[ ] Ruff passes.
[ ] Formatter passes.
[ ] Mypy passes.
[ ] Git diff reviewed.
[ ] No Phase 0–12 accidental modifications.
[ ] Working tree ready for Vidisha.
```

---

# 64. Architecture Sign-Off Checklist

Before closure:

```text
[ ] Outcome semantics are evidence-based.
[ ] Execution is not treated as recovery automatically.
[ ] Explicit disposition exists.
[ ] WAIT performs no new execution.
[ ] STOP terminates safely.
[ ] ESCALATE terminates automation safely.
[ ] RE_EVALUATE does not select an action.
[ ] Phase 9 selects the next action.
[ ] Phase 10 authorizes the next action.
[ ] Phase 11 executes the next action.
[ ] Phase 12 remains the provider boundary.
[ ] No blind repetition exists.
[ ] Loop is bounded.
[ ] Duplicate outcomes are idempotent.
[ ] Concurrency is safe.
[ ] Capture race remains protected.
[ ] Simulation truth is isolated.
[ ] Historical records are immutable.
[ ] No Phase 14/15/16/17 functionality was absorbed prematurely.
[ ] Full regression is green.
[ ] Acceptance evidence is genuine.
[ ] Manual validation is complete.
[ ] Git provenance is clean.
```

---

# 65. Phase Boundary Summary

**Phase 10**  
Determines whether a recovery action is permitted.

**Phase 11**  
Executes an already-authorized recovery action.

**Phase 12**  
Connects execution to Razorpay TEST MODE or the approved simulation/stub boundary.

**Phase 13**  
Observes what happened afterward and determines whether the system should:

```text
COMPLETE
WAIT
STOP
ESCALATE
RE-EVALUATE
```

When re-evaluation occurs, control returns through:

```text
Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11 → Phase 12
```

**Phase 14**  
Builds the comprehensive audit/observability layer.

**Phase 15**  
Runs the complete benchmark/evaluation protocol.

**Phase 16**  
Builds the reviewer-facing dashboard.

**Phase 17**  
Performs comprehensive adversarial testing and hardening.

**Phase 18**  
Packages demo, deployment, and submission.

---

# 66. Final Architectural Statement

The APRO adaptive loop is:

```text
OBSERVE
   ↓
UNDERSTAND OUTCOME
   ↓
UPDATE HISTORY
   ↓
CHOOSE DISPOSITION
   ├── COMPLETE
   ├── WAIT
   ├── STOP
   ├── ESCALATE
   └── RE-EVALUATE
             ↓
       Phase 7 / 8
             ↓
       Phase 9
             ↓
       Phase 10
             ↓
       Phase 11
             ↓
       Phase 12
             ↓
       Observe Again
```

The central rule is:

> **Phase 13 decides whether another decision cycle should happen; Phase 13 does not decide which recovery action to take.**

Action selection remains Phase 9.

Permission remains Phase 10.

Execution remains Phase 11.

Provider transport remains Phase 12.

Therefore:

> **Adaptation changes the context, not the authority chain.**

# PHASE 13 SPECIFICATION — READY FOR IMPLEMENTATION PLANNING
