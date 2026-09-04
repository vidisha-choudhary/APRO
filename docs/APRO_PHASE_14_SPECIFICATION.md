# APRO — PHASE 14 SPECIFICATION
## Audit & Observability

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 14 — Audit & Observability  
**Architecture Leads:** Vidisha + GPT  
**Implementation Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation Planning  
**Baseline:** Phase 13 — Outcome & Adaptive Recovery Loop  
**Phase 13 Baseline Commit:** `2acaff0`  
**Repository:** `C:\APRO`  
**Branch:** `main`

---

# 1. Purpose

Phase 14 makes important APRO behavior **reconstructable after the fact**.

The authoritative Implementation Master Plan defines Phase 14 as:

> **Audit & Observability**

with the objective:

> **Make every important APRO decision reconstructable.**

The required scope is:

- structured logs;
- correlation IDs;
- audit records;
- decision traces;
- model version traces;
- policy version traces;
- execution traces;
- outcome traces.

The acceptance requirement is that a reviewer can inspect one case and reconstruct:

```text
what happened
why APRO interpreted it that way
what APRO considered
what APRO recommended
what policy allowed
what executed
what happened afterward
```

This is explicitly the Phase 14 responsibility in the master plan. fileciteturn83file0L12-L74

Phase 14 therefore turns the Phase 0–13 event/decision lifecycle into an **explainable, durable, correlated history**.

---

# 2. Architectural Position

The project architecture is a modular monolith with strict separation between:

```text
External Provider
Canonical Domain
Intelligence
Governance
Execution
Observation
Evaluation
```

The audit subsystem belongs to the cross-cutting observability boundary while preserving those domain boundaries.

The source architecture identifies `AuditEvent` as a canonical domain entity and requires an immutable audit trail containing facts, predictions, policy decisions, executed actions, and outcomes. fileciteturn87file0L5-L14 fileciteturn88file0L5-L10

The project decision loop is:

```text
DETECT
  ↓
DIAGNOSE
  ↓
EVALUATE
  ↓
DECIDE
  ↓
GATE
  ↓
ACT
  ↓
OBSERVE
  ↓
RECOVER / STOP / ESCALATE
```

Phase 14 observes and records this lifecycle; it does not alter the authority of any stage.

---

# 3. Authority Hierarchy

Implementation must follow this order:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. Completed Phase 0–13 specifications and verified implementation
10. This Phase 14 specification

Antigravity must not independently redesign APRO.

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
Update specification if required
↓
Continue
```

---

# 4. Phase 14 Source Contract

The master plan places Phase 14 immediately after Phase 13:

```text
Phase 12 — Razorpay Test Mode Integration
        ↓
Phase 13 — Outcome & Adaptive Recovery Loop
        ↓
Phase 14 — Audit & Observability
        ↓
Phase 15 — Full Benchmark & Evaluation
        ↓
Phase 16 — Dashboard
        ↓
Phase 17 — Adversarial Testing & Hardening
        ↓
Phase 18 — Demo, Deployment & Submission
```

The dependency graph is sequential for this tail of the system. fileciteturn81file0L49-L54

Phase 14 exists specifically so later phases can trust the history:

```text
Phase 15 → benchmark/evaluation
Phase 16 → dashboard
Phase 17 → adversarial reconstruction
Phase 18 → reviewer/demo evidence
```

---

# 5. Primary Objective

At the end of Phase 14, a reviewer must be able to select one `case_id` and reconstruct the lifecycle without guessing.

Minimum reconstruction:

```text
CASE
↓
payment / triggering fact
↓
canonical event
↓
diagnosis
↓
candidate predictions / considerations
↓
decision
↓
policy decision
↓
approved action
↓
execution request
↓
execution result
↓
provider reference where safe
↓
outcome
↓
adaptive re-evaluation
↓
subsequent decision/action if any
↓
terminal disposition
```

For each stage, the reviewer must be able to answer:

```text
WHEN?
WHAT?
WHY?
WHICH VERSION?
WHO / WHAT COMPONENT?
WHAT INPUT FACTS?
WHAT OUTPUT?
WHAT HAPPENED NEXT?
```

---

# 6. Scope

## 6.1 In Scope

Phase 14 implements:

1. Immutable audit-event persistence.
2. Structured application logs.
3. Correlation identifiers.
4. Case-level trace identity.
5. Decision-level trace identity.
6. Model version provenance.
7. Policy version / ruleset provenance.
8. Execution provenance.
9. Outcome provenance.
10. Recovery-loop cycle provenance.
11. Event/state-transition audit records.
12. Human-approval / escalation audit records where applicable.
13. Provider-reference recording with secret-safe sanitization.
14. Trace reconstruction for one case.
15. Deterministic audit ordering.
16. Audit integrity validation.
17. Secret/PII minimization in logs.
18. Failure-event auditability.
19. Duplicate/idempotent audit handling where required.
20. PostgreSQL-backed audit persistence using existing database infrastructure.
21. Case/audit retrieval service for later Dashboard use.
22. Executable audit reconstruction acceptance runner.
23. Regression tests preserving Phases 0–13.

## 6.2 Explicitly Out of Scope

Phase 14 MUST NOT implement:

- benchmark generation or the 1,000+ case evaluation from Phase 15;
- statistical reporting from Phase 15;
- dashboard UI from Phase 16;
- benchmark optimization;
- adaptive model retraining;
- new decision logic;
- new policy logic;
- new execution logic;
- new provider adapters;
- production money movement;
- a message queue or distributed tracing infrastructure unless specifically justified and approved;
- Kubernetes or microservices;
- a second audit truth store;
- business logic inside logging utilities.

---

# 7. Core Architectural Invariants

## 7.1 Audit must never become authority

Audit records observe decisions.

They do not authorize or override them.

```text
Audit
≠
Policy

Audit
≠
Decision

Audit
≠
Execution
```

---

## 7.2 Historical records are immutable

Historical audit events must not be edited in place to rewrite history.

Corrections are represented by new audit records if necessary.

The original record remains preserved.

---

## 7.3 Audit is derived from authoritative events

The source of truth remains:

```text
PaymentEvent
RecoveryCase
Diagnosis
Decision
RecoveryAction
PolicyDecision
Execution
Outcome
```

Audit records must correlate these authoritative entities rather than invent conflicting business facts.

---

## 7.4 Logs are not the authoritative audit store

Structured logs are useful operational telemetry.

The durable audit trail must live in the persistent audit mechanism/domain record.

Do not make stdout or log files the only historical source.

---

## 7.5 Secrets never enter telemetry

No audit event or structured log may contain:

```text
API keys
API secrets
Authorization headers
database passwords
tokens
card data
raw secret-bearing provider payloads
```

Secrets must be removed, masked, hashed, or otherwise protected before telemetry emission.

OWASP's current logging guidance specifically recommends not directly recording authentication passwords, database connection strings, encryption keys, access tokens, and payment-card data; it recommends removal, masking, hashing, encryption, or equivalent protection where applicable. citeturn406011search8

---

# 8. Existing AuditEvent Contract

The existing domain model includes `AuditEvent`.

Before adding any fields, the implementation must inspect the current Phase 1–13 domain definition and persistence model.

Do not duplicate the entity.

Do not create:

```text
AuditEvent
+
ObservabilityEvent
+
TraceRecord
```

as competing authoritative stores.

If the current `AuditEvent` contract can represent Phase 14 requirements, extend usage before extending schema.

If schema modification is genuinely required:

1. document the exact gap;
2. follow existing SQLAlchemy/Alembic conventions;
3. add migration tests;
4. preserve all prior phases;
5. report the migration explicitly.

---

# 9. Required Audit Event Semantics

Every important lifecycle transition should emit a structured audit record.

At minimum support these event categories:

```text
CASE_CREATED
CASE_STATE_CHANGED

PAYMENT_EVENT_OBSERVED
PAYMENT_STATE_CHANGED

DIAGNOSIS_CREATED
DIAGNOSIS_USED

PREDICTION_CREATED
PREDICTION_USED

DECISION_CREATED
POLICY_DECISION_CREATED

ACTION_APPROVED
EXECUTION_STARTED
EXECUTION_COMPLETED
EXECUTION_FAILED
EXECUTION_UNKNOWN

OUTCOME_OBSERVED
OUTCOME_PROCESSED

RE_EVALUATION_STARTED
RE_EVALUATION_COMPLETED

HUMAN_APPROVAL_REQUESTED
HUMAN_APPROVAL_GRANTED
HUMAN_APPROVAL_REJECTED

ESCALATION_CREATED
STOP_DECIDED
RECOVERY_CONFIRMED

ERROR_OBSERVED
```

Exact enum names may follow repository conventions.

Do not add redundant events merely to increase event counts.

---

# 10. Audit Event Identity

Every audit event must have a deterministic or authoritative identity.

Prefer:

```text
existing AuditEvent ID
```

or an identity derived from:

```text
case_id
event_type
source_entity_id
event sequence/version
```

Do not use random identifiers as the only deduplication mechanism where deterministic identity is possible.

Duplicate delivery of the same source event must not create uncontrolled duplicate audit history.

---

# 11. Correlation Model

Phase 14 needs a consistent correlation hierarchy.

Recommended conceptual IDs:

```text
case_id
trace_id
cycle_id
event_id
decision_id
policy_decision_id
action_id
execution_id
outcome_id
provider_reference
```

The implementation may reuse existing IDs rather than create duplicates.

Minimum requirements:

### `case_id`

Groups all history for one recovery case.

### `trace_id`

Groups one end-to-end operational trace, including a re-evaluation cycle where applicable.

### `cycle_id`

Identifies one adaptive decision/execution cycle.

### entity IDs

Link to authoritative historical records.

The reviewer must be able to navigate from:

```text
case
→ trace
→ cycle
→ decision
→ policy
→ execution
→ outcome
```

without ambiguous joins.

---

# 12. Trace Propagation

Correlation identifiers must propagate through:

```text
webhook/event handling
→ case orchestration
→ diagnosis
→ prediction
→ decision
→ policy
→ execution
→ provider adapter
→ outcome
→ recovery loop
```

The observability layer must not introduce new business decisions merely to create traces.

The simplest implementation consistent with the existing modular-monolith architecture is preferred.

---

# 13. Structured Logging Contract

Logs emitted by APRO must be structured.

At minimum include safe fields such as:

```text
timestamp
log level
service/module
event name
case_id
trace_id
cycle_id
entity identifier
phase/component
status
reason code where applicable
duration where applicable
exception type where applicable
software/version identifier where applicable
```

Do not log:

```text
raw request body
raw authentication headers
provider secrets
database credentials
full customer PII
full payment instrument data
```

Use identifiers or redacted summaries instead.

---

# 14. Logging vs Audit Responsibilities

Use logs for:

```text
operational diagnostics
latency
component lifecycle
errors
debugging
runtime health
```

Use audit records for:

```text
business lifecycle
important decisions
policy outcomes
authorizations
executions
outcomes
state transitions
human review
```

An event may produce both a log and an audit record, but they are not interchangeable.

---

# 15. Decision Trace

A decision trace must answer:

```text
What facts entered the decision?
What diagnosis was available?
What predictions were available?
What actions were considered?
What recovery values were produced?
Which action was selected?
Which decision/model version generated it?
```

Phase 14 must reference existing Phase 8/9 artifacts.

It must not reimplement economic decision calculations merely to log them.

---

# 16. Candidate Action Trace

Where Phase 9 exposes candidate actions/predictions, record enough information to reconstruct:

```text
candidate action
prediction
expected recovery value
relevant model version
decision ordering/ranking if already part of the existing contract
```

Do not invent candidate scores that Phase 9 did not produce.

Do not recalculate ERV in Phase 14.

---

# 17. Model Version Trace

Every AI-derived artifact used by the recovery decision path must retain its version provenance.

At minimum:

```text
diagnosis model version
outcome prediction model version
decision/model version
```

If the repository already defines version fields, reference them directly.

Historical version metadata must never be overwritten.

Example:

```text
Cycle 1:
diagnosis = diag-v1
prediction = out-v1
decision = dec-v1

Cycle 2:
diagnosis = diag-v2
prediction = out-v2
decision = dec-v2
```

Audit reconstruction must distinguish these cycles.

---

# 18. Policy Version Trace

Every PolicyDecision must be traceable to:

```text
policy version
ruleset version
decision timestamp
policy outcome
reason code
rules triggered
```

The audit layer must consume the existing Phase 10 contract.

Do not copy H1–H10 logic into the audit subsystem.

---

# 19. Execution Trace

Every execution must be reconstructable.

At minimum:

```text
execution_id
case_id
action_id
execution_mode
executor name
status
started_at
completed_at where available
error code where applicable
provider_reference where safe
```

Do not store provider credentials.

Do not store authentication headers.

Do not store raw provider responses unless they have already been normalized/sanitized and the architecture explicitly permits retention.

---

# 20. Outcome Trace

Every processed Outcome must connect to:

```text
case_id
execution_id
outcome_id
outcome type
amount recovered
evidence reference
observed_at
provenance
```

The audit trail must preserve the distinction between:

```text
ExecutionStatus
```

and:

```text
OutcomeType
```

For example:

```text
Execution SUCCEEDED
+
no payment recovery evidence
→
PENDING outcome
```

The audit layer must record the actual values rather than infer a different outcome.

---

# 21. Recovery Loop Trace

Phase 13 introduced adaptive cycles.

Phase 14 must make them reconstructable.

A multi-cycle case should be auditable as:

```text
Cycle 1
  Decision 1
  Policy 1
  Execution 1
  Outcome 1 = FAILED

Cycle 2
  Re-evaluation 2
  Decision 2
  Policy 2
  Execution 2
  Outcome 2 = RECOVERED
```

The trace must show:

```text
why Cycle 2 happened
what evidence triggered it
what history was available
which versions were used
what Action 2 was
```

Do not add a second adaptive controller.

---

# 22. State Transition Audit

Important RecoveryCase transitions must be auditable.

At minimum:

```text
NEW
→ DIAGNOSING
→ EVALUATING
→ DECISION_PENDING
→ POLICY_CHECK
→ ACTION_APPROVED
→ EXECUTING
→ OBSERVING
→ RECOVERED / STOPPED / ESCALATED
```

The actual repository may have additional Phase 13 states.

Record:

```text
old state
new state
reason/context
event time
case_id
actor/component
correlation identifiers
```

Do not mutate the historical state-transition record.

---

# 23. Human Decision Audit

Whenever human approval or escalation occurs, audit:

```text
approval requested
approval requirement reason
approval granted/rejected where applicable
human-review reference
escalation reason
case state before/after
```

Do not store unnecessary personal information about the human reviewer.

Use existing human-approval entities/contracts.

---

# 24. Error Audit

Important failures should produce structured telemetry.

Examples:

```text
invalid model output
policy block
executor failure
provider timeout
unknown provider result
duplicate event
duplicate execution
stale policy decision
capture race
database transaction conflict
```

Each error event should contain:

```text
error category
safe error code
component
case_id where known
correlation IDs
entity ID where applicable
```

Never expose secrets through exception strings or audit fields.

---

# 25. Exception Handling

Audit/observability code must not swallow business errors.

Incorrect:

```python
try:
    execute_business_operation()
except Exception:
    log_only()
    return_success()
```

Correct:

```text
business error occurs
↓
safe audit/log emitted
↓
original error semantics preserved
```

Observability must be fail-safe with respect to business behavior.

---

# 26. Observability Failure Policy

A telemetry failure must not silently authorize or deny a financial action.

Preferred rule:

```text
business operation
    ↓
business result
    ↓
best-effort operational log
    +
durable audit write according to transaction policy
```

If the architecture requires audit persistence as a compliance-critical atomic operation, that requirement must be explicitly documented and implemented transactionally.

Do not invent stronger semantics without approval.

---

# 27. Transaction Boundary

Where a business state transition and its audit event must remain consistent, prefer:

```text
business state mutation
+
audit record
=
same transaction
```

for database-backed operations.

This prevents:

```text
database says RECOVERED
audit says nothing happened
```

from becoming a normal state.

However, telemetry-only logs may remain best-effort.

Clearly distinguish:

```text
durable audit
```

from:

```text
operational log
```

---

# 28. Audit Ordering

Audit events for one case must have an unambiguous ordering.

Use a combination of:

```text
event timestamp
sequence number / database ordering
source entity ordering
```

Do not rely solely on timestamps because concurrent events may share close timestamps.

For deterministic reconstruction, prefer an explicit monotonically increasing per-case sequence or equivalent authoritative ordering mechanism when compatible with the existing schema.

---

# 29. Concurrency

Phase 13 is concurrency-sensitive.

Phase 14 must remain safe under:

```text
duplicate webhook
concurrent outcome workers
concurrent state transitions
retry
provider callback
```

Requirements:

```text
duplicate source event
→ no contradictory audit history

concurrent valid events
→ deterministic ordering or explicit causal links

same business event
→ no uncontrolled duplicate durable audit records
```

Use PostgreSQL transaction/uniqueness semantics where appropriate.

---

# 30. Idempotent Audit Emission

Repeated handling of the same authoritative business event should not create misleading audit noise.

For example:

```text
same execution completion
→ same logical audit event identity
```

not:

```text
EXECUTION_COMPLETED
EXECUTION_COMPLETED
EXECUTION_COMPLETED
EXECUTION_COMPLETED
```

unless the source system genuinely generated distinct events.

The audit trail must distinguish:

```text
duplicate delivery
```

from:

```text
real repeated business events
```

---

# 31. Secret Sanitization

Implement a single reusable telemetry sanitization boundary.

Potential sensitive fields include:

```text
Authorization
authorization
api_key
key_id
key_secret
password
token
access_token
refresh_token
database_url
connection_string
secret
credential
cookie
card_number
cvv
```

The actual repository vocabulary may be broader.

Sanitization must cover:

```text
structured log dictionaries
audit payloads
exception metadata
provider references where necessary
nested dictionaries/lists
stringified structures
```

Do not rely on developers remembering to redact fields individually.

---

# 32. PII Minimization

Telemetry should retain only what is necessary for:

```text
case reconstruction
debugging
safety investigation
benchmark/evaluation provenance
```

Avoid logging:

```text
full email
full phone number
full address
full payment instrument details
```

Prefer:

```text
customer_id
hashed/pseudonymized identifier where appropriate
truncated/non-sensitive reference
```

The exact PII policy must remain consistent with project requirements.

---

# 33. Provider Data Sanitization

Raw provider responses must not be copied wholesale into audit logs.

For Razorpay:

```text
provider reference
event identity
safe status
safe error code
safe normalized evidence
```

are preferred over raw authenticated HTTP payloads.

Provider-specific normalization remains Phase 12 responsibility.

Phase 14 consumes the normalized result.

---

# 34. Structured Log Format

Use a stable schema.

Conceptually:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "event_name": "POLICY_DECISION_CREATED",
  "case_id": "...",
  "trace_id": "...",
  "cycle_id": "...",
  "entity_id": "...",
  "phase": "policy",
  "status": "ALLOW",
  "policy_version": "...",
  "reason_code": "...",
  "rules_triggered": [...]
}
```

This is an example only.

Use actual repository conventions.

---

# 35. OpenTelemetry Compatibility

External observability research recommends standardized semantic conventions for traces, logs, and events.

OpenTelemetry currently defines common semantic conventions across spans, metrics, logs, events, and resources, and OpenTelemetry Python supports manual instrumentation for traces and logs. citeturn406011search1turn406011search0turn406011search10

Phase 14 should therefore:

- use stable field names;
- keep trace/correlation context explicit;
- separate logs from durable business audit;
- avoid vendor-specific telemetry assumptions.

**Important:** OpenTelemetry is an optional implementation mechanism, not a license to introduce distributed infrastructure.

Do not add an OpenTelemetry collector, Jaeger, Kubernetes, or cloud-specific telemetry stack merely for Phase 14.

A lightweight Python logging/tracing abstraction that is compatible with OTel concepts is preferred unless the repository already has OTel dependencies.

---

# 36. Event Naming

Audit/log event names should be:

```text
stable
specific
machine-readable
human-understandable
```

Prefer:

```text
POLICY_DECISION_CREATED
EXECUTION_COMPLETED
OUTCOME_OBSERVED
```

over vague:

```text
THING_HAPPENED
PROCESS_UPDATE
```

Do not produce duplicate event names for the same semantic occurrence.

---

# 37. Audit Retrieval API / Service

Phase 14 should provide a backend retrieval abstraction such as:

```text
get_case_audit(case_id)
get_trace(trace_id)
get_cycle_audit(case_id, cycle_id)
```

Exact API names are implementation details.

The retrieval service must return chronologically/causally reconstructable audit information.

This service is backend truth for future Phase 16 Dashboard work.

Phase 16 will visualize it later; Phase 14 should not build the UI.

---

# 38. Reviewer Reconstruction Contract

Given:

```text
case_id = X
```

the retrieval layer must expose enough information to answer:

```text
1. What payment/event initiated the case?
2. What diagnosis was produced?
3. What confidence/evidence existed?
4. What recovery actions were considered?
5. What did Phase 9 select?
6. Which policy rules ran?
7. What did Phase 10 allow/block?
8. What was executed?
9. What did the provider/executor return?
10. What outcome followed?
11. Did APRO re-evaluate?
12. What changed in the next cycle?
13. Did the case recover, stop, or escalate?
14. Which model/policy versions were used?
15. When did each event occur?
```

This is the central user-facing success condition of Phase 14.

---

# 39. Reconstruction Must Preserve Truth vs Prediction

Audit records must distinguish:

```text
Observed Fact
Prediction
Decision
Policy Decision
Execution Result
Outcome
```

Do not write a prediction as though it were an observed fact.

For example:

```text
P(recovery | payment_link) = 0.72
```

is a prediction.

It is not:

```text
payment recovered = TRUE
```

The actual outcome must remain separate.

---

# 40. Decision Explainability Without Recalculation

The audit subsystem should preserve decision artifacts that already exist.

It must not silently recompute:

```text
ERV
probabilities
ranking
policy score
```

during audit retrieval.

If recomputation is required for a future evaluation report, that belongs to Phase 15.

Phase 14 is responsible for **capturing and reconstructing what actually happened**.

---

# 41. Audit Integrity

The implementation should detect obvious integrity failures such as:

```text
missing case ID
missing entity ID
impossible event ordering
unknown event type
invalid source entity reference
duplicate primary audit identity
```

An integrity checker may report:

```text
VALID
or
CORRUPT / INCOMPLETE
```

It must not modify historical truth automatically.

---

# 42. Trace Completeness

For a successful end-to-end recovery case, the audit trail should contain at least:

```text
Case created
Payment failure observed
Diagnosis
Prediction
Decision
Policy decision
Action approval
Execution start
Execution result
Outcome
Case state transition
Recovery confirmation
```

For an adaptive case:

```text
Cycle 1 events
Failure outcome
Re-evaluation
Cycle 2 events
Recovery
```

For STOP:

```text
decision/policy evidence
STOP disposition
case STOPPED
```

For ESCALATE:

```text
reason
escalation
case ESCALATED
```

---

# 43. Model and Policy Provenance

Audit retrieval must preserve historical provenance even if current versions change.

Example:

```text
Today:
model = v3

Historical case:
model = v1
```

The audit trail must still show:

```text
v1
```

Do not resolve historical events against "current" configuration.

---

# 44. Duration / Latency Observability

Where useful, structured logs may include:

```text
diagnosis_duration_ms
prediction_duration_ms
decision_duration_ms
policy_duration_ms
execution_duration_ms
outcome_processing_duration_ms
```

Only record durations actually measured.

Do not infer synthetic performance numbers.

This prepares later operational investigation without becoming Phase 15 benchmarking.

---

# 45. Operational Metrics

Phase 14 may expose lightweight runtime counters for:

```text
audit events emitted
audit persistence failures
structured log events
trace reconstruction errors
duplicate audit suppression
```

Do not implement the full KPI/benchmark metric suite here.

Phase 15 owns:

```text
Recovery Rate
Intervention Rate
Intervention Efficiency
Escalation Rate
Safety Violations
Baseline Comparisons
```

as explicitly defined by the master plan. fileciteturn83file0L82-L156

---

# 46. Storage Design

Prefer the existing PostgreSQL persistence layer.

Likely components:

```text
AuditEvent ORM
AuditEvent repository
audit service
audit retrieval service
transaction integration
```

Do not introduce a second database.

Do not introduce Elasticsearch, ClickHouse, Kafka, or another telemetry database without architectural approval.

---

# 47. Migration Policy

If no schema migration is required, prefer no migration.

If migration is necessary:

```text
migration
+
upgrade test
+
existing regression
+
rollback/compatibility reasoning
```

must be provided.

Never silently modify existing Phase 0–13 tables in incompatible ways.

---

# 48. Testing Architecture

Tests must cover:

## 48.1 Unit

```text
event construction
field normalization
sanitization
event naming
correlation propagation
version capture
serialization
ordering
```

## 48.2 Persistence

```text
create/read AuditEvent
uniqueness
immutability
transaction behavior
concurrent insertion
duplicate suppression
```

## 48.3 Integration

```text
decision → audit
policy → audit
execution → audit
outcome → audit
recovery loop → audit
```

## 48.4 Reconstruction

```text
case → complete timeline
case → multi-cycle timeline
case → stop timeline
case → escalation timeline
```

## 48.5 Security

```text
secret redaction
PII minimization
raw provider payload exclusion
exception sanitization
```

## 48.6 Failure

```text
audit persistence failure
malformed audit payload
unknown entity
duplicate event
transaction conflict
```

The business result must remain correct under telemetry problems according to the defined transaction policy.

---

# 49. Required Test Modules

Recommended:

```text
tests/audit/
    __init__.py
    test_event_models.py
    test_event_types.py
    test_sanitization.py
    test_correlation.py
    test_version_provenance.py
    test_ordering.py
    test_immutability.py
    test_persistence.py
    test_concurrency.py
    test_idempotency.py
    test_decision_trace.py
    test_policy_trace.py
    test_execution_trace.py
    test_outcome_trace.py
    test_recovery_loop_trace.py
    test_reconstruction.py
    test_error_audit.py
    test_logging.py
    test_secret_leakage.py
    test_phase_boundaries.py
```

Adapt to repository conventions and avoid duplicate test concepts already present.

---

# 50. Acceptance Criteria

Phase 14 must use genuine executable acceptance checks.

## Audit Persistence

**AC-01** — Important lifecycle events create durable audit records.

**AC-02** — Audit records are persisted through PostgreSQL-backed infrastructure.

**AC-03** — Audit records preserve authoritative source entity IDs.

**AC-04** — Historical audit records cannot be mutated.

**AC-05** — Duplicate logical audit events are idempotently handled.

## Correlation

**AC-06** — Every audited case is traceable by `case_id`.

**AC-07** — Trace/cycle identifiers propagate across the recovery lifecycle.

**AC-08** — Decision, policy, execution, and outcome records can be joined through authoritative identifiers.

**AC-09** — Concurrent events have deterministic or causally explainable ordering.

## Decision Explainability

**AC-10** — Diagnosis provenance is recorded.

**AC-11** — Prediction provenance is recorded.

**AC-12** — Decision provenance is recorded.

**AC-13** — Candidate/action evidence produced by Phase 9 is reconstructable.

**AC-14** — Phase 9 action selection is recorded without recomputing it.

## Policy Explainability

**AC-15** — Policy outcome is recorded.

**AC-16** — Policy reason code is recorded.

**AC-17** — Triggered safety rules are recorded.

**AC-18** — Policy version/ruleset version is recorded.

**AC-19** — Human-approval requirements are reconstructable.

## Execution Explainability

**AC-20** — Execution start/end/status is reconstructable.

**AC-21** — Execution mode and executor identity are recorded.

**AC-22** — Provider reference is recorded only when safe.

**AC-23** — Provider credentials never enter audit/log payloads.

## Outcome Explainability

**AC-24** — Outcome records link to the triggering execution.

**AC-25** — Outcome type is recorded exactly.

**AC-26** — Execution status and OutcomeType remain distinct in audit history.

**AC-27** — Outcome evidence reference/provenance is reconstructable.

**AC-28** — Recovered amount is traceable to the Outcome artifact.

## Recovery Loop

**AC-29** — Adaptive cycle identity is reconstructable.

**AC-30** — Re-evaluation reason/evidence is reconstructable.

**AC-31** — Previous action/outcome history is reconstructable.

**AC-32** — Multi-cycle cases can be reconstructed in causal order.

**AC-33** — Terminal RECOVERED cases show no later automated action.

**AC-34** — STOP cases show the reason and terminal transition.

**AC-35** — ESCALATE cases show the reason and terminal transition.

## State Transitions

**AC-36** — Important RecoveryCase state transitions are audited.

**AC-37** — State transitions reference case/entity/correlation identifiers.

**AC-38** — Audit history does not rewrite prior state facts.

## Structured Logging

**AC-39** — Core application logs use structured fields.

**AC-40** — Logs include case/trace correlation where applicable.

**AC-41** — Operational errors produce safe structured logs.

**AC-42** — Logging does not change business success/failure semantics.

## Security

**AC-43** — API credentials are absent from audit records.

**AC-44** — Authorization headers are absent from logs.

**AC-45** — Database credentials/connection strings are absent from telemetry.

**AC-46** — Sensitive payment data is absent or properly minimized.

**AC-47** — Raw secret-bearing provider payloads are not stored in audit records.

**AC-48** — Exception telemetry is sanitized.

## Provenance

**AC-49** — Diagnosis model version is preserved.

**AC-50** — Outcome prediction model version is preserved.

**AC-51** — Decision/model version is preserved.

**AC-52** — Policy/ruleset version is preserved.

**AC-53** — Historical versions remain immutable after later deployments.

## Reconstruction

**AC-54** — A reviewer can reconstruct one complete successful case.

**AC-55** — A reviewer can reconstruct one failed case.

**AC-56** — A reviewer can reconstruct one adaptive multi-cycle case.

**AC-57** — A reviewer can reconstruct one STOP case.

**AC-58** — A reviewer can reconstruct one ESCALATE case.

**AC-59** — Reconstruction identifies what happened.

**AC-60** — Reconstruction identifies why APRO interpreted the case that way.

**AC-61** — Reconstruction identifies what APRO considered.

**AC-62** — Reconstruction identifies what APRO recommended.

**AC-63** — Reconstruction identifies what policy allowed.

**AC-64** — Reconstruction identifies what executed.

**AC-65** — Reconstruction identifies what happened afterward.

## Integrity / Failure

**AC-66** — Corrupt/incomplete audit references are detected.

**AC-67** — Duplicate/concurrent audit writes do not create contradictory business history.

**AC-68** — Audit persistence failure follows the documented transaction policy.

**AC-69** — Audit failures do not silently authorize prohibited actions.

## Phase Boundaries

**AC-70** — Audit subsystem contains no action-selection engine.

**AC-71** — Audit subsystem contains no policy engine.

**AC-72** — Audit subsystem contains no execution engine.

**AC-73** — Provider-specific parsing remains outside Phase 14.

**AC-74** — Phase 15 benchmark logic is not duplicated in Phase 14.

**AC-75** — Phase 16 dashboard UI is not implemented in Phase 14.

## Compatibility

**AC-76** — Phase 10 behavior remains unchanged.

**AC-77** — Phase 11 behavior remains unchanged.

**AC-78** — Phase 12 provider boundary remains unchanged.

**AC-79** — Phase 13 adaptive-loop behavior remains unchanged.

**AC-80** — Full Phase 0–13 regression passes.

## Acceptance / Quality

**AC-81** — Acceptance runner genuinely checks all mandatory criteria.

**AC-82** — Acceptance runner fails when a mandatory criterion is false.

**AC-83** — Manual reconstruction scenarios are executable.

**AC-84** — Ruff passes.

**AC-85** — Formatter check passes.

**AC-86** — Mypy passes.

**AC-87** — No hardcoded secrets exist in telemetry code.

**AC-88** — Git scope contains only intended Phase 14 changes.

---

# 51. Manual Acceptance Scenarios

## Scenario 1 — Successful Recovery Reconstruction

Create or use one deterministic successful case and reconstruct:

```text
Case
→ Diagnosis
→ Prediction
→ Decision
→ Policy ALLOW
→ Action
→ Execution
→ Recovery evidence
→ Outcome RECOVERED
→ Case RECOVERED
```

The reconstructed history must show the complete chain.

---

## Scenario 2 — Failed Recovery Reconstruction

Verify:

```text
Action
→ Execution
→ Outcome FAILED
→ Case remains eligible / next disposition
```

The history must show why recovery was not confirmed.

---

## Scenario 3 — Adaptive Multi-Cycle Reconstruction

Verify:

```text
Action 1
→ FAILED
→ Re-evaluation
→ Decision 2
→ Policy 2
→ Action 2
→ Execution 2
→ RECOVERED
```

The reviewer must be able to distinguish Cycle 1 from Cycle 2.

---

## Scenario 4 — STOP Reconstruction

Verify:

```text
continuation denied
→ STOP disposition
→ case STOPPED
```

The reason must be reconstructable.

---

## Scenario 5 — ESCALATE Reconstruction

Verify:

```text
human-review condition
→ ESCALATE
→ case ESCALATED
```

The escalation reason must be reconstructable.

---

## Scenario 6 — Capture Race Reconstruction

Verify that an adaptive execution blocked by the Phase 11 final StateGuard is recorded as:

```text
new decision
→ policy
→ execution attempt
→ StateGuard rejection
→ no prohibited provider execution
```

The audit trail must not falsely report money movement.

---

## Scenario 7 — Duplicate Event Reconstruction

Send the same source event twice.

Verify:

```text
one logical business occurrence
one coherent audit trail
duplicate delivery identifiable
no contradictory case history
```

---

## Scenario 8 — Provider Timeout Reconstruction

Use the Phase 12 deterministic timeout stub.

Verify:

```text
execution UNKNOWN
→ pending/ambiguous observation
→ no false recovery
→ no false definitive failure
```

and ensure the audit trail reflects that ambiguity.

---

## Scenario 9 — Secret Leakage Attempt

Inject a sentinel secret into:

```text
logs
audit payload
provider metadata
exception metadata
```

Verify the sentinel is absent from persisted audit records and captured logs.

---

## Scenario 10 — Full Reviewer Reconstruction

Given only:

```text
case_id
```

retrieve the audit timeline and answer all seven reviewer questions:

```text
what happened?
why was it interpreted that way?
what was considered?
what was recommended?
what did policy allow?
what executed?
what happened afterward?
```

No hidden test fixture information may be needed to fill missing facts.

---

# 52. Acceptance Runner

Create:

```text
scripts/run_phase_14_acceptance.py
```

The runner must:

1. Execute all 10 manual scenarios.
2. Execute all 88 acceptance criteria.
3. Use genuine executable assertions.
4. Verify persistent audit retrieval.
5. Verify correlation propagation.
6. Verify model/policy/execution/outcome provenance.
7. Verify one complete adaptive reconstruction.
8. Verify STOP and ESCALATE reconstruction.
9. Verify secret/PII sanitization.
10. Verify duplicate/concurrent audit handling.
11. Verify trace ordering.
12. Verify historical immutability.
13. Verify Phase 10–13 compatibility.
14. Run full Phase 0–13 regression.
15. Run Ruff.
16. Run format check.
17. Run Mypy.
18. Exit non-zero on any mandatory failure.
19. Print exact PASS/FAIL evidence.

No:

```text
unconditional PASS
placeholder counter increments
fake reconstruction
hard-coded reviewer answers
```

---

# 53. Anti-Cheating Acceptance Rule

A test does not prove auditability merely because an `AuditEvent` exists.

It must prove that the data can reconstruct the real historical chain.

Invalid:

```text
audit_event_count > 0
```

Valid:

```text
query case_id
→ recover ordered event records
→ join authoritative entity IDs
→ verify actual decision
→ verify actual policy
→ verify actual execution
→ verify actual outcome
→ verify actual case transition
```

The acceptance test must use actual persisted data.

---

# 54. Trace Reconstruction Contract

Provide a deterministic reconstruction representation.

Conceptually:

```python
CaseAuditTrace(
    case_id=...,
    trace_id=...,
    events=[...],
    cycles=[...],
    final_case_status=...,
)
```

Each event should expose safe fields required for review.

The retrieval result must not mutate underlying historical records.

---

# 55. Audit Ordering Contract

The reconstruction output should be deterministically ordered.

Recommended order:

```text
event_sequence
then
observed_at
then
stable event identity
```

Do not sort solely by timestamp.

Concurrent events should remain causally distinguishable.

---

# 56. Audit Completeness Rules

A case is:

```text
AUDIT_COMPLETE
```

only when all expected mandatory lifecycle artifacts exist.

For example a successful recovery case should contain:

```text
case created
decision
policy
execution
outcome
terminal state
```

An adaptive case must contain at least:

```text
cycle 1
outcome
re-evaluation
cycle 2
terminal outcome
```

Missing records should produce:

```text
AUDIT_INCOMPLETE
```

rather than silently filling gaps.

---

# 57. Failure Reconstruction

If execution fails:

```text
EXECUTION_FAILED
```

the audit history must preserve:

```text
failure status
safe error code
execution identity
policy identity
action identity
```

Do not rewrite it as a successful action merely because later recovery succeeded.

---

# 58. Unknown/Timeout Reconstruction

If execution is:

```text
UNKNOWN
```

the trace must show ambiguity.

It must not become:

```text
FAILED
```

unless a later trustworthy outcome establishes definitive failure.

This preserves the Phase 11/12 semantics.

---

# 59. Historical Immutability Test

Attempting:

```text
audit_event.reason = "changed"
```

or equivalent mutation must fail according to the model's immutability contract.

If the persistent ORM allows mutation, the repository must enforce the immutable audit policy through controlled update restrictions.

Do not rely only on a Pydantic object being frozen if the database record can still be rewritten.

---

# 60. Database Constraints

Where possible use database constraints for:

```text
audit identity uniqueness
case/event correlation validity
foreign-key integrity
```

The database should reject impossible duplicate identities rather than relying only on application checks.

---

# 61. Logging Context Propagation

The implementation should provide a safe request/operation context for:

```text
case_id
trace_id
cycle_id
```

so downstream structured logs automatically inherit correlation metadata.

Do not require every developer call site to manually duplicate the same logging dictionary when a lightweight context mechanism can safely propagate it.

---

# 62. Context Isolation

Concurrent requests/cases must not leak correlation identifiers between one another.

For example:

```text
Case A trace_id
≠
Case B trace_id
```

even when operations execute concurrently in async code.

Add an explicit test for context isolation.

---

# 63. Async Safety

Because APRO uses asynchronous execution/persistence, logging and audit context must not rely on process-global mutable state that can cross-contaminate concurrent tasks.

Prefer task/context-local propagation.

Test:

```text
async Case A
async Case B
```

and verify their traces remain independent.

---

# 64. Performance Boundary

Phase 14 observability should be lightweight enough that it does not create an uncontrolled performance bottleneck.

Do not introduce:

```text
large synchronous network exports
blocking external telemetry calls
heavy serialization of raw provider payloads
```

in the critical execution path.

Persistent audit writes must follow the approved transaction semantics.

---

# 65. OpenTelemetry Implementation Boundary

OpenTelemetry may be used for:

```text
trace IDs
spans
structured telemetry
```

but must not become a replacement for APRO's durable business audit trail.

The current OpenTelemetry documentation defines traces/spans, logs, and events as distinct telemetry concepts and provides Python manual instrumentation support. citeturn406011search0turn406011search3

Recommended Phase 14 distinction:

```text
APRO AuditEvent
    = durable business-history record

Structured application log
    = operational record

Optional OTel span/event
    = runtime telemetry
```

Keep these concepts separate even if one implementation layer emits more than one.

---

# 66. Security and Compliance Boundary

Telemetry must follow the project's existing security model.

Never emit:

```text
provider secret
database password
authorization header
raw card information
raw sensitive payload
```

OWASP also recommends protecting log confidentiality/integrity and treating logs themselves as security-sensitive data. citeturn406011search8

Audit storage therefore needs appropriate application/database access controls consistent with the existing development environment.

Do not introduce a production IAM architecture in Phase 14.

---

# 67. Phase 15 Boundary

Phase 15 will consume the audit/history substrate.

It will handle:

```text
1,000+ cases
multiple seeds
baselines
economic metrics
model metrics
decision metrics
safety metrics
failure analysis
statistical reporting
```

Phase 14 must not precompute those benchmark results merely to make audit retrieval convenient. fileciteturn83file0L82-L156

---

# 68. Phase 16 Boundary

Phase 16's reviewer-facing interface will consume Phase 14's retrieval contracts.

Phase 14 does not build:

```text
React UI
dashboard pages
charts
case inspector frontend
```

The Phase 14 backend should simply provide clean, reconstructable truth.

---

# 69. Phase 17 Boundary

Phase 17 will use Phase 14 traces to investigate:

```text
duplicate webhooks
stale events
out-of-order events
capture races
AI failures
execution failures
policy bypasses
```

Phase 14 itself should not create a full adversarial-testing framework.

---

# 70. Phase 18 Boundary

Phase 18 needs:

```text
audit trail
failure history
architecture evidence
demo reconstruction
```

Phase 14 should make these available.

It must not write the final pitch/deployment package.

The master plan explicitly expects a later reviewer to inspect the audit trail and understand AI decisions. fileciteturn83file0L372-L394

---

# 71. Suggested Logical Package

A possible structure:

```text
src/apro/audit/
    __init__.py
    enums.py
    models.py
    repository.py
    service.py
    logging.py
    correlation.py
    sanitization.py
    tracing.py
    reconstruction.py
    integrity.py
    exceptions.py
```

Adapt to existing repository conventions.

Do not blindly create every file.

Reuse existing infrastructure.

---

# 72. Suggested Logical Contracts

Conceptually:

```python
class AuditEventRecord:
    audit_event_id
    case_id
    trace_id
    cycle_id
    event_type
    source_entity_type
    source_entity_id
    event_sequence
    occurred_at
    component
    payload
```

And:

```python
class CaseAuditTrace:
    case_id
    trace_id
    cycles
    events
    final_case_status
    completeness
```

These are conceptual examples.

Use existing repository patterns and the actual `AuditEvent` domain contract.

---

# 73. Audit Service Responsibilities

The Audit Service should:

```text
emit()
persist()
deduplicate()
retrieve()
reconstruct()
validate_integrity()
```

It should not:

```text
decide()
authorize()
execute()
```

---

# 74. Correlation Service Responsibilities

Correlation utilities should:

```text
start/attach trace context
attach case_id
attach cycle_id
propagate context through async operations
```

They must not become business-state managers.

---

# 75. Sanitization Service Responsibilities

Central sanitizer should:

```text
sanitize dicts
sanitize nested structures
sanitize strings where necessary
remove credentials
remove authorization headers
minimize PII
```

Tests must verify sentinel secrets never reach:

```text
logs
audit DB
retrieval output
exceptions
```

---

# 76. Reconstruction Service Responsibilities

The reconstruction service should:

```text
load authoritative entities
load audit events
join by safe identifiers
order events
group cycles
detect missing artifacts
return CaseAuditTrace
```

It must not mutate the database.

---

# 77. Audit Integrity Rules

At minimum detect:

```text
event references unknown case
event references unknown execution
duplicate logical event identity
missing required lifecycle artifact
event sequence reversal
terminal case followed by impossible business event
```

Some apparent anomalies may be valid concurrent behavior.

Do not reject legitimate history merely because timestamps are close.

---

# 78. Audit Versioning

Define explicit versions for the audit schema/format if needed:

```text
audit-schema-v1
trace-schema-v1
```

The version must be recorded safely so Phase 18 evidence can be interpreted later.

Do not create versioning complexity that is not required.

---

# 79. Observability Configuration

Configuration may include:

```text
log level
structured logging enabled
audit persistence enabled
sampling only for non-audit telemetry
```

Critical audit records must not be accidentally disabled by a debug/logging setting.

A lower log level may reduce operational logs, but must not disable mandatory durable business audit events.

---

# 80. No Silent Telemetry Loss

The system should be able to detect:

```text
audit persistence failure
```

through:

```text error log
safe counter
health signal
exception where transactional semantics require it
```

Do not silently ignore audit write failures.

---

# 81. Testing the Telemetry Boundary

Create tests that deliberately inject:

```text
audit write failure
logger handler failure
malformed event payload
serialization error
database constraint conflict
```

Verify the documented failure policy.

The critical requirement is:

> **Observability failures must never silently change a prohibited business result into an allowed result.**

---

# 82. Full Acceptance Runner Requirements

Create:

```text
scripts/run_phase_14_acceptance.py
```

It should execute:

```text
10 Manual Scenarios
88 Acceptance Criteria
```

and report:

```text
Manual Scenarios: X/10
Acceptance Criteria: X/88
```

The runner must:

- use genuine assertions;
- fail non-zero on mandatory failure;
- use PostgreSQL for persistence-specific criteria;
- reconstruct actual cases from persisted data;
- verify secrets are absent;
- verify correlation isolation;
- verify deterministic ordering;
- run full Phase 0–13 regression;
- run Ruff;
- run formatter check;
- run Mypy.

No copied test counts.

No unconditional PASS values.

---

# 83. Required Evidence Output

The strongest acceptance evidence should look conceptually like:

```text
CASE: case_demo_001

TRACE: trace_demo_001

CYCLE 1
  CASE STATE: EVALUATING
  DIAGNOSIS: diag-v1
  PREDICTIONS: out-v1
  DECISION: dec-v1
  SELECTED ACTION: RETRY
  POLICY: ALLOW / policy-v1
  EXECUTION: exec-1 / SUCCEEDED
  OUTCOME: FAILED

CYCLE 2
  RE-EVALUATION: reevaluate-2
  HISTORY: RETRY / FAILED
  DIAGNOSIS: diag-v2
  PREDICTIONS: out-v2
  DECISION: dec-v2
  SELECTED ACTION: ALTERNATE_RECOVERY
  POLICY: ALLOW / policy-v1
  EXECUTION: exec-2 / SUCCEEDED
  OUTCOME: RECOVERED

FINAL CASE: RECOVERED
AUDIT COMPLETE: YES
```

Actual IDs and values must come from the real repository/test fixture.

---

# 84. Anti-Cheating Rules

The acceptance suite must NOT claim reconstruction using only:

```text
number of audit events
symbol existence
string search
enum inequality
manually constructed expected output
```

It must query actual persisted audit data and compare it against authoritative business entities.

A valid reconstruction test must break if:

```text
decision audit disappears
policy audit disappears
execution audit disappears
outcome audit disappears
cycle correlation disappears
```

---

# 85. Required Regression Protection

Phase 14 must prove:

```text
Phase 10 policy behavior unchanged
Phase 11 execution behavior unchanged
Phase 12 provider behavior unchanged
Phase 13 adaptive behavior unchanged
```

Audit instrumentation must not change:

```text
decision result
policy result
execution result
outcome result
case state
```

except for explicit architectural handling of telemetry persistence failure where already approved.

---

# 86. Completion Definition

Phase 14 is complete only when:

```text
[ ] Durable audit trail exists.
[ ] Structured logs exist.
[ ] Correlation IDs propagate.
[ ] Decision traces exist.
[ ] Model versions are traceable.
[ ] Policy versions/rulesets are traceable.
[ ] Execution traces exist.
[ ] Outcome traces exist.
[ ] Adaptive cycles are reconstructable.
[ ] State transitions are auditable.
[ ] Human approval/escalation is auditable.
[ ] Duplicate audit delivery is controlled.
[ ] Concurrent audit processing is safe.
[ ] Ordering is deterministic/causal.
[ ] Historical audit records are immutable.
[ ] Secrets never enter telemetry.
[ ] PII is minimized.
[ ] Raw secret-bearing provider payloads are excluded.
[ ] Case reconstruction works from case_id.
[ ] Successful case reconstruction works.
[ ] Failed case reconstruction works.
[ ] Adaptive case reconstruction works.
[ ] STOP case reconstruction works.
[ ] ESCALATE case reconstruction works.
[ ] Capture race reconstruction works.
[ ] UNKNOWN execution reconstruction works.
[ ] Audit integrity failures are detected.
[ ] Telemetry failure behavior is documented/tested.
[ ] Phase 10 behavior unchanged.
[ ] Phase 11 behavior unchanged.
[ ] Phase 12 behavior unchanged.
[ ] Phase 13 behavior unchanged.
[ ] Full Phase 0–13 regression passes.
[ ] Acceptance runner genuinely passes.
[ ] Manual scenarios genuinely pass.
[ ] Ruff passes.
[ ] Formatter passes.
[ ] Mypy passes.
[ ] Git diff reviewed.
[ ] No Phase 15/16/17/18 functionality absorbed.
[ ] Working tree ready for Vidisha's commit.
```

---

# 87. Architecture Sign-Off Checklist

Before Phase 14 closure:

```text
[ ] One case can be reconstructed end-to-end.
[ ] Facts and predictions remain separate.
[ ] Decisions remain immutable historical artifacts.
[ ] Policy decisions remain immutable historical artifacts.
[ ] Executions remain immutable historical artifacts.
[ ] Outcomes remain immutable historical artifacts.
[ ] Audit events do not override domain truth.
[ ] Logs do not replace durable audit.
[ ] Correlation IDs remain case/cycle safe under concurrency.
[ ] Model provenance is historical, not current-version lookup.
[ ] Policy provenance is historical, not current-rules lookup.
[ ] Provider secrets are absent.
[ ] PII is minimized.
[ ] No second policy/decision/execution engine exists.
[ ] No dashboard exists in Phase 14.
[ ] No benchmark engine exists in Phase 14.
[ ] Audit retrieval is suitable for Phase 16.
[ ] Evidence is suitable for Phase 15.
[ ] Full regression is green.
[ ] Acceptance evidence is genuine.
[ ] Git provenance is clean.
```

---

# 88. Final Architectural Statement

Phase 14 transforms APRO from:

```text
a system that acted
```

into:

```text
a system whose important actions can be explained and reconstructed.
```

The reconstruction chain is:

```text
FACT
 ↓
DIAGNOSIS
 ↓
PREDICTION
 ↓
DECISION
 ↓
POLICY
 ↓
EXECUTION
 ↓
OUTCOME
 ↓
ADAPTIVE LOOP
 ↓
AUDIT TRAIL
```

The central invariant is:

> **Audit records what APRO did and why its existing authorities produced that result; audit does not become a new authority.**

Phase 15 may then measure the resulting behavior.

Phase 16 may visualize it.

Phase 17 may attack it.

Phase 18 may present it.

Phase 14's job is to make the underlying history trustworthy enough for all three.

# PHASE 14 SPECIFICATION — READY FOR IMPLEMENTATION PLANNING
