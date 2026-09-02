# APRO — Phase 11 Execution Framework Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 11 — Execution Framework  
**Architecture Leads:** Vidisha + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0  
**Date:** 2026-09-02

---

## 1. Purpose

Phase 11 implements APRO's **Execution Framework**.

Phase 9 determines the economically preferred action.

Phase 10 determines whether that action is permitted under explicit safety and governance constraints.

Phase 11 is responsible for **performing only an already-authorized action through a bounded executor**.

The governing separation is:

```text
AI prediction
    ≠
economic preference
    ≠
permission
    ≠
execution
```

Phase 11 does not choose the action, optimize economics, reinterpret policy, or bypass the Policy & Safety Engine.

Its responsibility begins only after a valid Phase 10 policy decision permits an action.

The approved architectural flow is:

```text
Phase 9 — RecoveryDecision
            ↓
Phase 10 — PolicyEngine
            ↓
ALLOW
            ↓
Phase 11 — Execution Framework
            ↓
Correct Executor
            ↓
Execution lifecycle
            ↓
Execution result
```

The existing master plan defines Phase 11 as the execution architecture without depending on live provider integration. It explicitly requires executor interfaces for Retry, Payment Link, Outreach, Escalation, and No-Op actions, together with execution lifecycle, execution idempotency, execution status, error handling, and simulation executors. fileciteturn28file0L158-L220

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
9. Completed Phase 0–10 specifications and acceptance evidence
10. This document

This document operationalizes the Phase 11 portion of the existing roadmap and architecture. It must not silently redefine higher-authority contracts.

If a conflict is discovered:

```text
STOP
  ↓
Document the conflict
  ↓
Report to Vidisha + GPT
  ↓
Architecture decision
  ↓
Update specification if required
  ↓
Continue implementation
```

Antigravity must not independently redesign APRO. The implementation lead is explicitly required to stop when an architectural clarification is necessary and may not change product behavior, financial authority boundaries, AI decision boundaries, safety invariants, evaluation methodology, or external integration assumptions without approval. fileciteturn27file1L66-L162

---

## 3. Relationship to Completed Phases

### 3.1 Phase 4 — Recovery Case Orchestration

Phase 11 executes within the Recovery Case lifecycle established by Phase 4 and the domain state machines.

The execution framework must not create an alternate case lifecycle.

### 3.2 Phase 7 — Failure Diagnosis

Phase 11 does not invoke, retrain, or modify the diagnosis model.

### 3.3 Phase 8 — Recovery Outcome Prediction

Phase 11 does not invoke, retrain, or modify the outcome-prediction model to select actions.

### 3.4 Phase 9 — Economic Decision Engine

Phase 9 produces the `RecoveryDecision`.

Phase 11 must not independently rank or select actions.

### 3.5 Phase 10 — Policy & Safety Engine

Phase 10 is the authoritative permission boundary.

A Phase 11 execution attempt is valid only when the corresponding policy decision authorizes that action.

The Phase 10 handoff explicitly requires the execution framework to consume whether execution is permitted, which action is permitted, approval/reconciliation state, the applicable idempotency identity, policy/rule version, and the reason for the decision. fileciteturn27file5L909-L937

### 3.6 Phase 12 — Razorpay Test Mode Integration

Phase 12 introduces actual provider-specific integration.

Phase 11 therefore provides provider-neutral execution contracts and simulation/internal implementations, but does not depend on live Razorpay credentials or a production Razorpay client.

The provider-specific implementation must remain behind the adapter boundary described in the technical architecture. Razorpay-specific API details are explicitly required to be isolated behind a gateway/adapter boundary. fileciteturn31file3L1233-L1454

### 3.7 Phase 13 — Outcome & Adaptive Recovery Loop

Phase 11 produces execution results.

Phase 13 consumes execution outcomes and determines whether APRO should observe, re-evaluate, stop, or escalate. The master plan places this adaptive loop after Phase 11 and Phase 12. fileciteturn28file0L326-L422

Phase 11 must not implement the adaptive recovery loop.

---

## 4. Phase Boundary

### In scope

Phase 11 includes:

- execution request validation;
- execution authorization enforcement;
- executor interfaces;
- executor registry;
- execution orchestration;
- execution lifecycle management;
- `PENDING` / `RUNNING` / terminal state handling;
- execution idempotency;
- concurrency-safe duplicate protection;
- final pre-execution state recheck;
- execution error mapping;
- simulation executors;
- internal No-Op/Stop execution;
- internal Escalation execution;
- provider-neutral Retry execution interface;
- provider-neutral Payment Link execution interface;
- provider-neutral Outreach execution interface;
- execution result contracts;
- persistence of execution attempts using the existing persistence layer;
- tests and acceptance coverage.

### Explicitly out of scope

Phase 11 does **not** implement:

- live Razorpay API integration;
- Razorpay authentication or credentials;
- live Payment Link creation against Razorpay;
- real payment retry against Razorpay;
- real customer messaging;
- money movement;
- autonomous scheduling;
- outcome/adaptive re-evaluation;
- model training;
- policy learning;
- reinforcement learning;
- bandits;
- dashboard functionality;
- full observability/dashboard infrastructure;
- benchmark optimization;
- production deployment;
- live-money transactions.

Provider capabilities must be validated in Phase 12 before a concrete real provider implementation is activated. The master plan explicitly defines Phase 12 as the Razorpay Test Mode integration phase. fileciteturn28file1L598-L744

---

## 5. Core Principle

# Execute, Do Not Decide

The Execution Framework is a **command layer**, not a decision layer.

It may validate that an execution request is authorized and structurally valid.

It may not:

- select a different action;
- replace a policy decision;
- ignore a policy block;
- reinterpret a human-approval requirement;
- override captured-payment protection;
- change economic thresholds;
- create a new recovery strategy;
- retry another action because it prefers that action.

The only acceptable decision authority chain is:

```text
RecoveryDecision
    ↓
PolicyDecision
    ↓
Approved execution request
    ↓
Executor
```

The technical architecture states that the Execution Layer performs only actions approved by the Policy Gate and must not independently optimize or select actions. fileciteturn31file3L1334-L1410

---

## 6. Existing Domain Contracts

Phase 1 established the canonical execution-related vocabularies.

### RecoveryActionType

```text
RETRY
ALTERNATE_RECOVERY
OUTREACH
ESCALATE
STOP
```

### RecoveryActionStatus

```text
CANDIDATE
RECOMMENDED
APPROVED
BLOCKED
EXECUTING
COMPLETED
FAILED
CANCELLED
```

### ExecutionStatus

```text
PENDING
RUNNING
SUCCEEDED
FAILED
UNKNOWN
CANCELLED
```

### ExecutionMode

```text
RAZORPAY_TEST_MODE
SIMULATION
INTERNAL
```

These exact vocabularies are part of the existing APRO domain contract. fileciteturn30file4L275-L359

The domain state machines already define:

```text
RecoveryAction:
CANDIDATE
    ↓
RECOMMENDED
    ↓
APPROVED
    ↓
EXECUTING
    ↓
COMPLETED / FAILED / CANCELLED
```

and:

```text
Execution:
PENDING
    ↓
RUNNING
    ↓
SUCCEEDED / FAILED / UNKNOWN / CANCELLED
```

The existing state-machine functions are authoritative. Phase 11 must reuse them rather than maintain a second transition matrix. The existing domain audit confirms these transition paths and terminal-state locks. fileciteturn29file0L27-L50

---

## 7. Existing `Execution` Domain Entity

The canonical domain `Execution` represents one attempt to perform an approved recovery action.

Its established fields are:

```text
Execution
├── execution_id
├── action_id
├── case_id
├── execution_type
├── execution_mode
├── status
├── provider_reference
├── started_at
├── completed_at
├── error_code
└── error_message
```

These fields are already established in the domain contract. fileciteturn30file4L275-L315

The persistence layer already provides:

- `ExecutionModel`
- `ExecutionRepository`
- `save(...)`
- `get_by_id(...)`
- `find_by_idempotency_key(...)`
- `find_by_case_id(...)`

The execution table already has a unique constraint on `idempotency_key`, which was explicitly verified during Phase 2. fileciteturn33file1L80-L115

Phase 11 should use this existing infrastructure rather than creating a second execution persistence model.

No new database schema should be introduced unless implementation discovers a genuine specification conflict requiring architectural review.

---

## 8. Phase 10 Permission Contract

Phase 11 consumes the Phase 10 `PolicyDecision`.

The required authorization semantics are:

### `ALLOW`

An action may be dispatched if all remaining execution preconditions are satisfied.

### `BLOCK`

No executor may be invoked.

### `REQUIRE_HUMAN_APPROVAL`

No executor may be invoked until the Phase 10 approval workflow has produced a policy decision that authorizes execution.

Phase 11 must not independently decide whether an approval is sufficient.

The relevant Phase 10 policy decision remains the authority.

---

## 9. Approved Execution Request

Phase 11 should introduce a provider-neutral immutable request object equivalent to:

```text
ApprovedExecutionRequest
├── execution_id
├── case_id
├── action_id
├── action_type
├── policy_decision_id
├── decision_id
├── idempotency_key
├── execution_mode
├── parameters
├── requested_at
├── policy_version
├── rule_set_version
├── action_schema_version
└── approval_reference (optional)
```

The exact implementation may use a different class name if the contract remains explicit and independently testable.

The request must be immutable.

The request must be constructed only after the execution gate has validated the Phase 10 policy decision.

---

## 10. Approved Execution Preconditions

Before an executor is invoked, all applicable conditions below must hold.

### Authorization

```text
policy_outcome == ALLOW
```

### Effective action

```text
effective_action != None
```

### Action consistency

The execution action must match the action authorized by Phase 10.

A caller must not pass:

```text
PolicyDecision → PAYMENT_LINK
```

and then request:

```text
execute(RETRY)
```

### Case binding

The case associated with the RecoveryAction must match the PolicyDecision case.

### Decision binding

The execution request must reference the PolicyDecision/decision that actually authorized it.

### Idempotency

A valid policy-provided idempotency identity must be present where required.

### Action state

The RecoveryAction must be in the appropriate approved state before execution.

### Case state

The RecoveryCase must be in the execution-eligible state defined by the existing domain lifecycle.

### Payment state

The final current payment state must still permit the action.

### Executor availability

The correct executor must be registered for the requested action and execution mode.

### Parameters

Execution parameters must satisfy the relevant executor contract.

### Mode

The execution mode must be explicit.

No implicit fallback from real provider mode to simulation mode is permitted.

---

## 11. Final Pre-Execution Safety Gate

A final state check must occur **immediately before externally meaningful dispatch**.

The framework must use the existing Phase 10 `StateGuard` contract.

Conceptually:

```text
PolicyDecision
      ↓
Execution Validation
      ↓
Idempotency Claim
      ↓
Final Current-State Recheck
      ↓
Executor Dispatch
```

If the payment is captured, or otherwise becomes ineligible, execution must not proceed.

A stale policy decision must not authorize execution against changed current state.

This final check exists specifically to protect against the race:

```text
policy approved
      ↓
payment state changes
      ↓
execution attempted
```

The execution layer must fail closed.

The APRO domain mandates that captured payments never enter recovery execution and that transition functions enforce this invariant. fileciteturn29file1L93-L100

---

## 12. Race-Condition Rule

A policy decision is a permission result for a particular decision context.

It is not a permanent authorization independent of current state.

Therefore:

```text
ALLOW at T1
```

does not imply:

```text
ALLOW forever
```

The executor must revalidate the current state before dispatch.

The technical architecture explicitly calls for payment eligibility to be checked immediately before externally meaningful action execution. fileciteturn31file0L368-L372

---

## 13. Execution State Lifecycle

The canonical execution lifecycle is:

```text
PENDING
   ↓
RUNNING
   ↓
SUCCEEDED

PENDING
   ↓
RUNNING
   ↓
FAILED

PENDING
   ↓
RUNNING
   ↓
UNKNOWN

PENDING
   ↓
CANCELLED

RUNNING
   ↓
CANCELLED
```

Terminal states:

```text
SUCCEEDED
FAILED
UNKNOWN
CANCELLED
```

No transition may originate from a terminal state.

Phase 11 must use the existing domain transition helper. The established domain contract confirms `PENDING -> RUNNING/CANCELLED` and `RUNNING -> SUCCEEDED/FAILED/UNKNOWN/CANCELLED`. fileciteturn29file0L43-L50

---

## 14. RecoveryAction Lifecycle Integration

For an approved action:

```text
RecoveryAction.APPROVED
        ↓
RecoveryAction.EXECUTING
        ↓
RecoveryAction.COMPLETED
```

or:

```text
RecoveryAction.APPROVED
        ↓
RecoveryAction.EXECUTING
        ↓
RecoveryAction.FAILED
```

or:

```text
RecoveryAction.APPROVED
        ↓
RecoveryAction.EXECUTING
        ↓
RecoveryAction.CANCELLED
```

The transition must occur through the established domain state-machine function.

Phase 11 must not mutate state by bypassing the domain contract. The domain audit confirms these exact RecoveryAction transitions. fileciteturn29file1L62-L76

---

## 15. RecoveryCase Lifecycle Integration

A normally executable action should correspond to the RecoveryCase lifecycle:

```text
POLICY_CHECK
      ↓
ACTION_APPROVED
      ↓
EXECUTING
      ↓
OBSERVING
```

The actual state transitions must be performed using the existing domain state-machine functions and any required payment safety invariants.

Phase 11 must not implement the post-execution observation loop beyond recording the execution result.

The established RecoveryCase lifecycle includes this exact primary path and its observation transitions. fileciteturn30file3L117-L131

---

## 16. Critical Semantic Distinction

An execution result does **not** necessarily mean revenue was recovered.

The framework must distinguish:

```text
execution succeeded
```

from:

```text
payment recovered
```

For example:

```text
Payment Link executor
       ↓
ExecutionStatus.SUCCEEDED
```

means the framework successfully performed the execution operation.

It does **not** mean:

```text
OutcomeType.RECOVERED
```

unless the appropriate observed evidence exists.

The technical architecture explicitly states that execution does not imply recovery and that outcome confirmation belongs to subsequent observation. fileciteturn31file0L262-L316

---

## 17. Executor Architecture

All executors must implement a provider-neutral interface.

Conceptually:

```text
Executor
├── can_execute(...)
├── validate(...)
└── execute(...)
```

The concrete API may vary, but the contract must remain:

```text
input:
    ApprovedExecutionRequest

output:
    ExecutionResult
```

Executors must not receive unrestricted access to Phase 9 intelligence inputs or simulator truth.

They receive only the execution context needed to perform their action.

---

## 18. Required Executor Interfaces

Phase 11 must provide:

```text
RetryExecutor
PaymentLinkExecutor
OutreachExecutor
EscalationExecutor
NoOpExecutor
```

These interfaces are required by the master plan and technical architecture. fileciteturn31file2L530-L644 fileciteturn31file3L1374-L1410

Each executor must explicitly identify its supported execution modes.

---

## 19. RetryExecutor

### Purpose

Perform an authorized retry action through a provider-neutral interface.

### Critical rule

APRO must **not** assume a generic provider endpoint such as:

```text
retry_payment()
```

The master architecture explicitly requires provider-capability awareness. fileciteturn31file3L1514-L1548

### Phase 11 behavior

Phase 11 should provide:

- abstract/provider-neutral Retry executor contract;
- simulation implementation;
- validation;
- deterministic execution-result mapping.

The real provider-specific retry mechanism is deferred to Phase 12 and must be selected only after validated provider capability evidence exists.

### Phase 11 must not

- invent a Razorpay retry endpoint;
- send a real request to Razorpay;
- assume retry is universally available;
- silently replace retry with Payment Link.

---

## 20. PaymentLinkExecutor

### Purpose

Represent execution of an authorized Payment Link recovery action.

### Phase 11 behavior

Provide:

- provider-neutral Payment Link executor contract;
- deterministic simulation implementation;
- duplicate protection through execution idempotency;
- structured simulated provider-reference output;
- explicit execution mode.

### Phase 11 must not

create a real Razorpay Payment Link.

Actual Razorpay Payment Link creation is Phase 12 scope.

The technical architecture identifies Payment Link recovery as an important real integration path and requires the created reference to be recorded. fileciteturn31file0L54-L100

---

## 21. OutreachExecutor

### Purpose

Represent an authorized customer-facing recovery intervention.

### Phase 11 behavior

The initial implementation is simulation-only.

It must record enough structured information to reproduce the simulated execution:

```text
case_id
message
channel
execution_id
timestamp
delivery_status
```

The message must come from approved execution parameters or an explicit simulation fixture.

The executor must not contact a real customer.

No email, SMS, WhatsApp, push, or other external messaging provider is to be invoked in Phase 11.

The product and technical specifications explicitly permit initial Outreach simulation. fileciteturn31file4L1738-L1772

---

## 22. EscalationExecutor

### Purpose

Execute an `ESCALATE` action as an internal human-review operation.

The escalation payload should contain:

```text
case_id
reason
recommended_action
confidence
evidence
previous_actions
amount
policy_decision_reference
```

The executor must not perform an automated financial recovery after escalation.

The internal execution can produce a human-review reference and the orchestration layer can transition the RecoveryCase to `ESCALATED` using the domain state machine.

The technical architecture requires these escalation fields and explicitly prohibits automated financial action after escalation without a human-approved workflow. fileciteturn31file0L184-L216

No external ticketing or messaging integration is required in Phase 11.

---

## 23. NoOpExecutor

### Purpose

Represent an intentional `STOP` action.

STOP is not an execution failure.

It means:

```text
do not intervene
```

The No-Op executor performs no external financial action.

It may produce an internal execution record containing:

```text
case_id
execution_id
decision_reference
stop_reason
timestamp
```

The RecoveryCase should transition to `STOPPED` through the existing domain state machine.

The technical architecture explicitly defines STOP as an intentional non-intervention and requires an internal record rather than a financial side effect. fileciteturn31file0L224-L254

---

## 24. Executor Registry

Phase 11 must provide a deterministic executor registry.

Conceptually:

```text
(action_type, execution_mode)
            ↓
       Executor
```

Example:

```text
(RETRY, SIMULATION)
    → SimulationRetryExecutor

(PAYMENT_LINK, SIMULATION)
    → SimulationPaymentLinkExecutor

(OUTREACH, SIMULATION)
    → SimulationOutreachExecutor

(ESCALATE, INTERNAL)
    → EscalationExecutor

(STOP, INTERNAL)
    → NoOpExecutor
```

The exact registration mechanism may vary.

The registry must reject:

- unsupported action;
- unsupported mode;
- missing executor;
- conflicting executor registration.

There must be no silent fallback.

---

## 25. ExecutionMode Semantics

### `SIMULATION`

Used for deterministic Phase 11 simulated execution.

It must have:

- no external side effects;
- deterministic behavior;
- explicit simulation configuration;
- no provider credentials.

### `INTERNAL`

Used for actions whose effect is internal to APRO, such as:

- STOP;
- ESCALATE.

### `RAZORPAY_TEST_MODE`

The enum already exists as part of APRO's domain vocabulary.

Phase 11 must provide the extension point but must not require a concrete Razorpay implementation.

If no registered provider executor exists for `RAZORPAY_TEST_MODE`:

```text
FAIL CLOSED
```

with an explicit unsupported-mode error.

No network call may occur as a fallback.

---

## 26. Simulation Executor Contract

Simulation must not be an alternate decision engine.

A simulation executor receives an already-authorized action.

It simulates the **execution**, not the decision.

The simulation layer must therefore not:

- choose a different action;
- recalculate ERV;
- rerun policy;
- access simulator latent truth;
- use future outcome labels;
- inspect `EvaluationTruthRecord`.

The simulator may receive an explicit simulation outcome fixture because Phase 11 is evaluating the execution framework itself.

That fixture must be clearly separated from live execution inputs.

---

## 27. Simulation Results

A simulation execution may return:

```text
ExecutionStatus.SUCCEEDED
ExecutionStatus.FAILED
ExecutionStatus.UNKNOWN
ExecutionStatus.CANCELLED
```

with structured fields:

```text
provider_reference
error_code
error_message
```

The simulation may also include safe metadata such as:

```text
simulated=true
executor_name
execution_mode
```

It must never imply that money moved or revenue was recovered unless a later outcome layer explicitly establishes that fact.

---

## 28. Deterministic Simulation

Where deterministic simulation is required, identical:

```text
ApprovedExecutionRequest
+
SimulationConfiguration
```

must produce the same canonical execution result.

The simulation should not use hidden randomness.

If randomness is explicitly part of a simulation fixture, it must be supplied through a controlled deterministic seed and must not enter the live execution authorization path.

---

## 29. Execution Idempotency

Execution idempotency is mandatory.

The framework must use the idempotency identity produced by Phase 10 wherever one is supplied.

The existing persistence layer already enforces a unique constraint on:

```text
executions.idempotency_key
```

and exposes lookup by idempotency key. fileciteturn33file6L542-L576

Therefore the architecture is:

```text
Execution Request
       ↓
Idempotency Lookup / Claim
       ↓
Existing execution?
   ┌───────┴────────┐
  YES              NO
   ↓                ↓
Return /            Persist PENDING
reuse existing      ↓
                  Dispatch
```

The implementation must handle concurrent duplicate claims safely.

A unique-constraint conflict must not result in a second executor invocation.

---

## 30. Idempotency Semantics

For the same authorization identity:

```text
same idempotency key
```

must not create two independent execution side effects.

Distinct attempts remain distinct only when Phase 10 supplies distinct identities.

Phase 11 must not modify or regenerate the policy identity.

---

## 31. Duplicate Execution Behavior

When an identical idempotency key already maps to an execution:

### Existing terminal execution

Do not dispatch again.

Return the existing execution result according to the public execution contract.

### Existing PENDING/RUNNING execution

Do not dispatch a second execution.

Return the existing execution state.

### Existing execution with conflicting authorization payload

Fail closed.

The conflict must be explicit.

Do not overwrite the existing authorization context.

---

## 32. Persistence Ordering

The safe default order is:

```text
Validate authorization
      ↓
Validate current state
      ↓
Resolve executor
      ↓
Claim idempotency / persist PENDING
      ↓
Transition action → EXECUTING
      ↓
Transition execution → RUNNING
      ↓
Dispatch executor
      ↓
Persist terminal execution state
```

The exact transaction boundaries must preserve the invariant:

> a second worker must not be allowed to dispatch the same idempotent execution.

Where database transactions are required, use the existing `UnitOfWork`.

The existing persistence layer already supplies an async Unit-of-Work and an ExecutionRepository. fileciteturn33file6L552-L576

Do not invent a parallel persistence transaction mechanism.

---

## 33. Concurrency

Phase 2 already provides database-level execution idempotency and state-dependent concurrency protections.

Phase 11 must build on those protections.

Required behavior under concurrent duplicate requests:

```text
Worker A ─┐
          ├─ same idempotency key
Worker B ─┘
          ↓
at most one new execution dispatch
```

One worker must win the durable idempotency claim.

The losing worker must observe the existing execution and must not invoke the executor again.

The Phase 2 implementation explicitly reports a unique execution idempotency constraint and concurrency-safe state-dependent updates. fileciteturn33file0L21-L33

---

## 34. Execution Error Taxonomy

Phase 11 must distinguish at minimum:

### Validation error

The execution request is invalid before dispatch.

Examples:

- blocked policy;
- missing effective action;
- action mismatch;
- invalid execution mode;
- unavailable executor;
- stale/captured state;
- invalid action state.

These must prevent dispatch.

### Terminal execution failure

The executor was invoked and definitively reports failure.

Result:

```text
FAILED
```

### Unknown execution result

The executor cannot establish whether the external operation completed.

Examples include:

- timeout after dispatch;
- ambiguous provider response;
- transport failure where completion cannot be determined.

Result:

```text
UNKNOWN
```

Never translate an ambiguous result into `FAILED` without evidence.

### Cancellation

An execution is explicitly cancelled under an allowed cancellation condition.

Result:

```text
CANCELLED
```

### Success

The executor definitively reports that the requested execution operation completed.

Result:

```text
SUCCEEDED
```

Again, `SUCCEEDED` does not mean revenue recovery.

---

## 35. Unknown State Is First-Class

`UNKNOWN` is a safety-relevant execution state.

The framework must never treat:

```text
timeout
```

as automatically equivalent to:

```text
payment failed
```

or:

```text
execution failed
```

An `UNKNOWN` result should preserve enough information for later reconciliation.

The existing APRO domain specification explicitly calls out `UNKNOWN` for ambiguous execution results such as API timeouts. fileciteturn30file4L343-L377

Reconciliation/outcome handling itself belongs to later phases.

---

## 36. No Blind Internal Retries

Phase 11 must not implement an automatic loop such as:

```text
FAILED
  ↓
execute same action again
  ↓
FAILED
  ↓
execute again
```

The adaptive strategy belongs to Phase 13.

Phase 11 performs an execution attempt.

Failure is reported.

A future re-evaluation may decide another action.

The product specification explicitly requires re-evaluation rather than blindly repeating a failed action. fileciteturn31file4L1916-L1970

---

## 37. ExecutionResult Contract

The framework should expose an immutable result equivalent to:

```text
ExecutionResult
├── execution_id
├── action_id
├── case_id
├── status
├── execution_mode
├── provider_reference (optional)
├── error_code (optional)
├── error_message (optional)
├── started_at
├── completed_at (optional)
├── executor_name
└── metadata
```

`metadata` must not contain secrets or simulator latent truth.

---

## 38. Secrets and Sensitive Data

Phase 11 must not persist:

- API secrets;
- authentication tokens;
- full customer credentials;
- raw payment instrument data;
- provider secrets;
- access tokens.

Provider references may be stored when appropriate.

Execution error messages must be sanitized if they originate from provider-facing layers.

No credentials should enter test fixtures.

---

## 39. Provider Adapter Boundary

The technical architecture requires Razorpay-specific HTTP details to remain behind an adapter.

The intended future structure is:

```text
Execution Framework
        ↓
Provider-neutral executor
        ↓
RazorpayGateway Interface
        ↓
Razorpay Adapter
        ↓
Razorpay API
```

Phase 11 establishes the contract.

Phase 12 supplies and validates the actual provider adapter.

The domain/application layers must not acquire direct dependency on Razorpay HTTP details. fileciteturn31file3L1418-L1454

---

## 40. Action Parameter Discipline

The existing `RecoveryAction.parameters` contract is:

```text
dict[str, Any] | None
```

Phase 11 may consume these parameters for execution.

However:

- executor-specific validation must be explicit;
- unsupported parameters must be rejected where required;
- parameters must not silently change the action type;
- parameters must not become a hidden decision mechanism;
- parameters must not contain credentials.

The domain specification establishes `RecoveryAction.parameters` as the generic parameter container for an action. fileciteturn29file2L137-L146

---

## 41. `ALTERNATE_RECOVERY`

The domain supports:

```text
ALTERNATE_RECOVERY
```

but the roadmap names concrete executor interfaces for:

```text
RETRY
PAYMENT_LINK
OUTREACH
ESCALATE
STOP
```

Therefore Phase 11 must not invent an arbitrary concrete executor semantics for `ALTERNATE_RECOVERY`.

The implementation must inspect the completed phase contracts and the authoritative action taxonomy.

If the architecture requires a concrete executor for `ALTERNATE_RECOVERY` and no contract exists, stop and report the ambiguity.

Do not silently map it to Payment Link, Retry, or Outreach.

---

## 42. API Surface

Phase 11 should expose a small application-level execution API equivalent to:

```text
execute(
    policy_decision,
    recovery_action,
    recovery_case,
    payment,
    execution_mode,
    current_time,
    parameters,
)
    → ExecutionResult
```

The exact signature may differ provided that the same authorization and safety contracts remain explicit.

The execution API must not accept a bare `RecoveryActionType` and execute it without the PolicyDecision authorization context.

---

## 43. What the Execution API Must Reject

The API must reject:

```text
BLOCK policy
```

```text
REQUIRE_HUMAN_APPROVAL policy
```

```text
missing effective action
```

```text
action mismatch
```

```text
case mismatch
```

```text
decision mismatch
```

```text
missing/invalid idempotency identity where required
```

```text
captured/ineligible payment
```

```text
stale current state
```

```text
terminal RecoveryAction
```

```text
terminal RecoveryCase
```

```text
unsupported executor
```

```text
unsupported execution mode
```

```text
invalid execution parameters
```

No executor invocation may occur for these requests.

---

## 44. STOP Semantics

STOP is a valid recovery decision.

When Phase 10 authorizes STOP:

```text
PolicyDecision
    ↓
NoOpExecutor
    ↓
Execution record
    ↓
RecoveryCase → STOPPED
```

No external financial action occurs.

STOP must not be reported as an execution error.

---

## 45. ESCALATE Semantics

When Phase 10 authorizes ESCALATE:

```text
PolicyDecision
    ↓
EscalationExecutor
    ↓
Internal human-review reference
    ↓
RecoveryCase → ESCALATED
```

No automatic financial action occurs as a consequence of the escalation.

---

## 46. Human Approval Boundary

Phase 11 must not create a new approval system.

Human approval is owned by Phase 10.

Phase 11 consumes the result of that process.

The execution request should preserve the Phase 10 approval reference where supplied so that the execution can be associated with the authorization that permitted it.

---

## 47. Execution Identity

Each execution attempt must have a unique `execution_id`.

This ID is different from:

```text
policy_decision_id
```

and:

```text
idempotency_key
```

Their semantics are:

```text
policy_decision_id
    = identity of the governance decision

idempotency_key
    = identity used to prevent duplicate execution

execution_id
    = identity of a persisted execution attempt
```

Do not conflate them.

---

## 48. Timestamps

Execution lifecycle timestamps must use timezone-aware UTC datetimes.

At minimum:

```text
started_at
completed_at
```

must correspond to the actual execution lifecycle.

If deterministic simulation tests require a frozen time, the time must be explicitly injected.

Do not introduce hidden time dependencies into deterministic test paths.

---

## 49. Trace / Audit Relationship

Full audit and observability are later-phase responsibilities.

Phase 11 nevertheless must preserve references needed for later reconstruction:

- execution ID;
- action ID;
- case ID;
- policy decision ID;
- idempotency key;
- executor name;
- execution mode;
- provider reference;
- status;
- error code.

Phase 11 must not build the entire Phase 14 observability subsystem.

---

## 50. Persistence Strategy

Phase 11 uses the existing persistence layer.

Expected infrastructure:

```text
ExecutionRepository
UnitOfWork
ExecutionModel
```

The execution framework should persist lifecycle state through those existing abstractions.

No duplicate repository hierarchy should be created.

---

## 51. Database Migration Rule

The existing persistence schema already contains an `executions` table and a unique `idempotency_key`.

Therefore:

```text
Expected:
No new migration required for Phase 11.
```

If implementation discovers that the approved Phase 11 contract genuinely cannot be represented by the existing persistence layer:

```text
STOP
```

Document the required schema change.

Do not silently add a migration.

The existing Phase 2 persistence contract already exposes Execution persistence and database-enforced idempotency. fileciteturn33file0L25-L33

---

## 52. Suggested Source Tree

Expected implementation package:

```text
src/apro/execution/
├── __init__.py
├── enums.py
├── models.py
├── exceptions.py
├── interfaces.py
├── registry.py
├── orchestrator.py
├── idempotency.py
├── validation.py
└── executors/
    ├── __init__.py
    ├── retry.py
    ├── payment_link.py
    ├── outreach.py
    ├── escalation.py
    └── noop.py
```

Simulation-specific behavior may be consolidated into those executor modules or an additional explicitly simulation-scoped module if contracts remain independently testable.

Modules may be consolidated if the public contracts remain explicit and testable.

Do not create a large service hierarchy without evidence that it is needed.

---

## 53. Suggested Tests

Expected tests:

```text
tests/execution/
├── __init__.py
├── test_taxonomy.py
├── test_models.py
├── test_validation.py
├── test_registry.py
├── test_orchestrator.py
├── test_idempotency.py
├── test_state_transitions.py
├── test_retry_executor.py
├── test_payment_link_executor.py
├── test_outreach_executor.py
├── test_escalation_executor.py
├── test_noop_executor.py
├── test_simulation.py
├── test_concurrency.py
├── test_unknown_handling.py
├── test_side_effect_guards.py
└── test_regression.py
```

Actual filenames may be consolidated if coverage remains explicit.

---

## 54. Testing Principles

Tests must prove behavior, not merely class existence.

Every executor requires tests for:

- valid authorization;
- wrong action;
- blocked policy;
- human-approval policy without authorization;
- invalid state;
- idempotency;
- success;
- failure;
- unknown;
- cancellation;
- unsupported mode;
- parameter validation.

---

## 55. Required Concurrency Test

A concurrency test must prove:

```text
same idempotency_key
+
two execution requests
        ↓
one durable execution claim
        ↓
at most one executor invocation
```

The test should exercise the actual persistence uniqueness mechanism and transaction behavior where feasible.

Do not replace the concurrency test with a single-threaded dictionary check.

---

## 56. Required Race Test

A race-condition test must prove:

```text
policy ALLOW
    +
payment changes to CAPTURED
    +
execution begins
```

cannot result in an unauthorized executor invocation.

The final state recheck must catch the change.

---

## 57. Required Block-Path Test

For every executor:

```text
PolicyOutcome.BLOCK
```

must result in:

```text
no executor invocation
```

The same must hold for:

```text
REQUIRE_HUMAN_APPROVAL
```

without a valid Phase 10 authorization result.

---

## 58. Required Side-Effect Test

Phase 11 simulation/internal implementations must be testable without:

- network;
- Razorpay;
- messaging providers;
- external ticketing;
- money movement.

The test suite should actively guard these boundaries.

---

## 59. Required Unknown Test

An executor simulation configured to return an ambiguous outcome must produce:

```text
ExecutionStatus.UNKNOWN
```

and must not silently produce:

```text
FAILED
```

The execution record must preserve the error context necessary for later reconciliation.

---

## 60. Required Determinism Test

For deterministic simulation:

```text
same request
+
same simulation configuration
```

must produce the same canonical execution result.

The test must not depend on wall-clock values where deterministic identity is being asserted.

---

## 61. Required Executor Routing Tests

The registry must route:

```text
RETRY
PAYMENT_LINK
OUTREACH
ESCALATE
STOP
```

to their correct executors.

Unknown or unsupported action types must fail closed.

Wrong mode/action combinations must fail closed.

---

## 62. Required State-Machine Tests

Phase 11 must verify the integration points against existing domain state machines.

At minimum:

```text
RecoveryAction.APPROVED → EXECUTING
RecoveryAction.EXECUTING → COMPLETED
RecoveryAction.EXECUTING → FAILED
RecoveryAction.EXECUTING → CANCELLED

Execution.PENDING → RUNNING
Execution.PENDING → CANCELLED
Execution.RUNNING → SUCCEEDED
Execution.RUNNING → FAILED
Execution.RUNNING → UNKNOWN
Execution.RUNNING → CANCELLED
```

Terminal-state transitions must fail.

Do not duplicate or weaken the existing state machine.

---

## 63. Acceptance Criteria

Phase 11 passes only when all mandatory execution-framework criteria below are genuinely verified.

### AC-01 — Explicit authorization boundary

An execution request must require a Phase 10 `PolicyDecision`.

### AC-02 — ALLOW-only dispatch

Only an authorized `ALLOW` decision may reach an executor.

### AC-03 — BLOCK rejection

A `BLOCK` decision never reaches any executor.

### AC-04 — Human approval rejection

`REQUIRE_HUMAN_APPROVAL` without a valid authorizing Phase 10 result never reaches an executor.

### AC-05 — Action binding

The executed action must equal the action authorized by Phase 10.

### AC-06 — Case binding

Execution action, case, and policy decision case must agree.

### AC-07 — Decision binding

The execution must retain the authorizing decision reference.

### AC-08 — Final state recheck

Current payment state is rechecked immediately before dispatch.

### AC-09 — Captured payment safety

A captured payment never reaches an executor.

### AC-10 — RecoveryAction lifecycle

Approved action transitions through the canonical domain lifecycle.

### AC-11 — Execution lifecycle

Execution transitions only through the canonical state machine.

### AC-12 — Correct executor routing

Each action reaches its correct executor.

### AC-13 — Unsupported executor rejection

Missing/unsupported executor fails closed without dispatch.

### AC-14 — Explicit execution mode

Every execution has an explicit execution mode.

### AC-15 — No implicit mode fallback

Unsupported real-provider mode does not silently downgrade to simulation.

### AC-16 — Retry abstraction

Retry exists as a provider-neutral contract without assuming a generic provider retry API.

### AC-17 — Payment Link abstraction

Payment Link exists as a provider-neutral contract without making live provider calls.

### AC-18 — Outreach simulation

Outreach execution is simulation-only in Phase 11.

### AC-19 — Escalation execution

Escalation creates an internal human-review execution result and no financial action.

### AC-20 — STOP execution

STOP is handled by the No-Op executor and is not treated as failure.

### AC-21 — Execution idempotency

Repeated identical authorization identities do not produce duplicate execution dispatch.

### AC-22 — Durable uniqueness

Database idempotency uniqueness is respected under duplicate requests.

### AC-23 — Concurrency safety

Concurrent duplicate claims result in at most one new execution dispatch.

### AC-24 — Success mapping

Definitive executor success maps to `SUCCEEDED`.

### AC-25 — Failure mapping

Definitive executor failure maps to `FAILED`.

### AC-26 — Unknown mapping

Ambiguous execution maps to `UNKNOWN`.

### AC-27 — Cancellation

Allowed cancellation maps to `CANCELLED`.

### AC-28 — No blind retry

Phase 11 never automatically repeats a failed action.

### AC-29 — Simulation determinism

Frozen identical simulation inputs produce identical canonical execution results.

### AC-30 — Zero external effects

Phase 11 simulation/internal acceptance path produces zero external financial effects.

### AC-31 — Zero outbound network effects

Phase 11 default acceptance path performs zero network calls.

### AC-32 — Secret isolation

Secrets and credentials never enter execution records or fixtures.

### AC-33 — Parameter validation

Invalid executor parameters are rejected before dispatch.

### AC-34 — Terminal state protection

Terminal executions/actions cannot be executed again.

### AC-35 — Provider adapter boundary

Provider-specific HTTP details do not leak into the domain layer.

### AC-36 — Persistence integration

Execution records persist and reload correctly through the existing persistence layer.

### AC-37 — Regression compatibility

All Phase 0–10 tests remain green.

### AC-38 — Code quality

Ruff, formatting, and mypy remain green.

### AC-39 — Acceptance runner

A dedicated Phase 11 acceptance runner validates all mandatory execution scenarios.

### AC-40 — Phase boundary integrity

Phase 11 contains no live Razorpay integration, no adaptive outcome loop, and no dashboard/observability implementation beyond required execution metadata.

---

## 64. Manual Acceptance Scenarios

At minimum implement and pass these scenarios.

### CASE 1 — Authorized Retry Simulation

```text
Policy = ALLOW
Action = RETRY
Mode = SIMULATION
→ RetryExecutor
→ PENDING
→ RUNNING
→ SUCCEEDED
```

Assert the action was dispatched exactly once.

### CASE 2 — Authorized Payment Link Simulation

```text
Policy = ALLOW
Action = PAYMENT_LINK
Mode = SIMULATION
→ PaymentLinkExecutor
→ valid simulated provider reference
→ SUCCEEDED
```

No real Payment Link is created.

### CASE 3 — Authorized Outreach Simulation

```text
Policy = ALLOW
Action = OUTREACH
Mode = SIMULATION
→ OutreachExecutor
→ simulated delivery result
```

No customer is contacted.

### CASE 4 — Authorized Escalation

```text
Policy = ALLOW
Action = ESCALATE
Mode = INTERNAL
→ EscalationExecutor
→ human-review reference
→ case escalated
```

No financial action occurs.

### CASE 5 — Authorized STOP

```text
Policy = ALLOW
Action = STOP
Mode = INTERNAL
→ NoOpExecutor
→ execution recorded
→ case stopped
```

No external action occurs.

### CASE 6 — BLOCK Cannot Execute

```text
Policy = BLOCK
→ executor must not be invoked
```

### CASE 7 — Approval Requirement Cannot Execute

```text
Policy = REQUIRE_HUMAN_APPROVAL
without authorizing approval result
→ executor must not be invoked
```

### CASE 8 — Action Mismatch

```text
Policy authorizes PAYMENT_LINK
request asks RETRY
→ reject before executor
```

### CASE 9 — Captured Payment Race

```text
Policy = ALLOW
payment becomes CAPTURED before final gate
→ reject
→ no executor invocation
```

### CASE 10 — Duplicate Idempotency

```text
same policy authorization
same idempotency key
two execution requests
→ one execution dispatch
→ duplicate prevented
```

### CASE 11 — Concurrent Duplicate Requests

Two workers submit the same idempotency key concurrently.

Assert:

```text
one durable execution
at most one executor invocation
```

### CASE 12 — Definitive Failure

Simulation executor returns definitive failure.

Assert:

```text
ExecutionStatus.FAILED
```

### CASE 13 — Ambiguous Result

Simulation executor returns ambiguous completion.

Assert:

```text
ExecutionStatus.UNKNOWN
```

### CASE 14 — Cancellation

A valid execution is cancelled through an allowed path.

Assert:

```text
ExecutionStatus.CANCELLED
```

### CASE 15 — Unsupported Real Mode

```text
Action = PAYMENT_LINK
Mode = RAZORPAY_TEST_MODE
No Phase 12 provider executor registered
→ fail closed
→ zero network calls
```

---

## 65. Acceptance Runner Requirements

Create:

```text
scripts/run_phase_11_acceptance.py
```

The runner must contain executable assertions.

It must report:

```text
manual scenarios
acceptance criteria
execution lifecycle
idempotency
concurrency
state safety
side-effect guarantees
simulation determinism
regression status
```

Do not hardcode PASS values.

Every reported pass must correspond to an observed assertion or measurement.

---

## 66. Acceptance Runner Safety Guard

The Phase 11 acceptance runner must actively guard:

```text
socket
HTTP
Razorpay adapters
customer messaging adapters
external ticketing adapters
```

and verify zero external calls in all Phase 11 simulation/internal scenarios.

The runner must fail if an unexpected outbound effect occurs.

---

## 67. Acceptance Evidence

Generated evidence may be written under:

```text
artifacts/execution/
```

for example:

```text
artifacts/execution/
├── execution_acceptance.json
├── execution_acceptance.md
├── execution_results.jsonl
├── idempotency_results.json
├── concurrency_results.json
└── execution_summary.json
```

These are generated evidence, not source code.

Do not automatically add generated evidence to the source commit unless explicitly approved.

---

## 68. Full Regression

The Phase 11 implementation must preserve all prior tests.

Required:

```powershell
.venv\Scripts\pytest.exe -v tests/
```

The final test count must include:

```text
Phase 0–10 baseline
+
Phase 11 execution tests
```

Any regression must be investigated.

Do not weaken earlier tests.

---

## 69. Quality Gates

Required:

```powershell
.venv\Scripts\pytest.exe -v tests/execution/
.venv\Scripts\pytest.exe -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\mypy.exe src
.venv\Scripts\python.exe .\scripts\run_phase_11_acceptance.py
```

All must pass before closure.

---

## 70. Git / Provenance Boundary

Phase 11 must not silently modify completed Phase 0–10 contracts.

Before staging:

```powershell
git status --short --untracked-files=all
git diff --name-only
git diff --stat
git diff --cached --name-only
```

Expected Phase 11 commit scope:

```text
docs/PHASE_11_EXECUTION_FRAMEWORK_SPECIFICATION.md
src/apro/execution/
tests/execution/
scripts/run_phase_11_acceptance.py
```

plus separately approved shared-file changes only.

Never stage:

```text
.venv/
artifacts/
local credentials
database files
temporary logs
scratch files
```

The project governance model requires explicit provenance review between phases and prohibits silently modifying completed-phase contracts. fileciteturn27file1L100-L162

---

## 71. Implementation Stop Conditions

Antigravity must stop and report if:

- a provider capability must be invented;
- a generic retry API must be assumed;
- a new external provider is required;
- the Phase 10 authorization contract must change;
- a completed Phase 0–10 domain state machine must change;
- a database schema change becomes necessary;
- an execution mode's semantics are ambiguous;
- `ALTERNATE_RECOVERY` cannot be mapped from an approved contract;
- a safety invariant cannot be preserved;
- an external call is required before Phase 12;
- a blocked action could reach an executor;
- concurrent idempotent requests cannot be made safe;
- an unknown provider result would have to be guessed as success or failure.

When any of these occurs:

```text
STOP
→ document
→ report
→ architecture decision
→ continue
```

---

## 72. Phase 11 Closure Requirements

Phase 11 may be declared complete only when:

```text
Implementation complete
        AND
Execution unit tests green
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
ALLOW-only dispatch verified
        AND
BLOCK path isolation verified
        AND
Human-approval path isolation verified
        AND
Final state gate verified
        AND
Execution idempotency verified
        AND
Concurrency protection verified
        AND
UNKNOWN handling verified
        AND
Zero outbound effects verified
        AND
Simulation determinism verified
        AND
No live provider integration
        AND
Git provenance clean
```

Only then may Phase 12 begin.

---

## 73. Phase 12 Handoff

Phase 11 ends at:

```text
Execution Framework
```

Phase 12 begins at:

```text
Provider-specific execution capability
```

The Phase 12 boundary is:

```text
Phase 11 Executor Contract
        ↓
Razorpay Gateway Interface
        ↓
Razorpay Adapter
        ↓
Razorpay Test Mode
```

Phase 12 must validate actual provider capabilities before enabling them.

The master plan explicitly defines Phase 12 as the Razorpay Test Mode integration phase and states that the exact integration path depends on validated capabilities. fileciteturn28file1L652-L744

---

## 74. Final Architectural Invariant

After Phase 11, the APRO chain is:

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
    ↓
Phase 12 — Razorpay Test Mode Integration
    ↓
Phase 13 — Outcome & Adaptive Recovery Loop
```

The critical separation remains:

```text
prediction
    ≠
decision
    ≠
permission
    ≠
execution
    ≠
recovery outcome
```

Every boundary must remain:

- independently testable;
- versioned;
- auditable;
- deterministic where required;
- fail-closed at safety boundaries.

---

## 75. Architecture Lead Decision

The Phase 11 specification is approved as the implementation target.

Antigravity must first perform repository/specification reconnaissance against:

- `PROJECT_CONSTITUTION.md`
- `PRODUCT_SPECIFICATION.md`
- `TECHNICAL_ARCHITECTURE.md`
- `DOMAIN_AND_DATA_MODEL.md`
- `POLICY_AND_SAFETY_SPECIFICATION.md`
- `IMPLEMENTATION_MASTER_PLAN.md`
- completed Phase 0–10 specifications and implementation

before writing code.

The reconnaissance must establish that the implementation plan matches the actual existing repository.

If a contradiction is found, stop rather than guessing.

# Phase 11 is ready for implementation reconnaissance.
