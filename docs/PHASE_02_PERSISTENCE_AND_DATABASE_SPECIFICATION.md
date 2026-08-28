# APRO — Phase 2 Persistence & Database Specification

**Project:** Adaptive Payment Recovery Orchestrator

**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery

**Architecture Leads:** User + GPT

**Software Engineering / Coding Lead:** Antigravity

**Phase:** 2 — Persistence & Database

**Status:** Architecture Specification — Draft for Architecture Review

**Version:** 1.0

---

# 1. Purpose

Phase 2 gives APRO a durable persistence layer without implementing the next application workflow phases.

The objective is to persist the already-approved APRO domain state and historical evidence in a way that is:

- durable,
- transactionally safe,
- idempotent,
- concurrency-safe,
- auditable,
- database-agnostic at the domain layer,
- reproducible through migrations,
- and ready for Phase 3's canonical event pipeline.

Phase 2 is an infrastructure and persistence phase. It is **not** the event-orchestration phase and it must not silently absorb Phase 3 or later responsibilities.

---

# 2. Authority

This specification is subordinate to:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`

If an implementation detail conflicts with one of the above documents, the higher-level document wins and Antigravity must stop and report the conflict.

This document defines the Phase 2 implementation contract within those boundaries.

---

# 3. Locked Starting Point

The following are already implemented and formally closed:

- Phase 0 — Engineering Foundation
- Razorpay Webhook Validation milestone
- Phase 1 — Core Domain & State Machines

The Phase 1 domain layer is authoritative and must not be redesigned by Phase 2 implementation work.

Current domain records include:

```text
Customer
Payment
PaymentEvent
RecoveryCase
Diagnosis
RecoveryAction
ActionEvaluation
Decision
PolicyDecision
Execution
Outcome
AuditEvent
```

Phase 2 may add persistence-specific infrastructure models, but it must preserve the semantic contracts of the Phase 1 domain models.

---

# 4. Phase 2 Objective

Implement durable PostgreSQL persistence for the APRO domain and its historical evidence.

The phase must provide:

```text
PostgreSQL
    ↓
SQLAlchemy 2.x async persistence layer
    ↓
Repository boundaries
    ↓
Transaction/session abstraction
    ↓
Database-backed uniqueness and idempotency
    ↓
Raw provider-event storage
    ↓
Audit persistence
    ↓
Alembic migrations
```

The Phase 2 implementation must leave the Phase 1 domain layer independent of PostgreSQL and SQLAlchemy.

---

# 5. Scope

## 5.1 In Scope

Phase 2 includes:

- PostgreSQL database support.
- SQLAlchemy 2.x asynchronous persistence implementation.
- Persistence models for the approved domain entities.
- Repository interfaces and concrete persistence implementations.
- Database session / transaction management.
- Database-backed event identity and idempotency primitives.
- Raw provider-event storage.
- Audit-event persistence.
- Required indexes and uniqueness constraints.
- Migration management with Alembic.
- Persistence integration tests using a real PostgreSQL database.
- Transaction rollback tests.
- Concurrency/idempotency tests for persistence guarantees.
- Reproducible fresh-database initialization.

## 5.2 Out of Scope

Phase 2 must NOT implement:

- Canonical event normalization.
- Recovery-case orchestration.
- Diagnosis inference.
- Recovery prediction models.
- Economic decisioning.
- Runtime policy engine.
- Execution framework.
- Razorpay outbound recovery APIs.
- Adaptive outcome orchestration.
- Full simulation engine.
- Benchmarking.
- Dashboard/UI.
- AI/LLM/Gemini integration.
- Live-money execution.

Phase 3 and later phases own those behaviors.

---

# 6. Architectural Principles

Phase 2 must preserve the following principles.

## 6.1 Domain vs Infrastructure Separation

The Phase 1 Pydantic domain models are domain contracts. They must not import SQLAlchemy, async database sessions, or PostgreSQL-specific types.

The persistence layer maps between domain models and database persistence models.

Conceptually:

```text
Domain Model
      ↓
Repository Port / Interface
      ↓
Persistence Implementation
      ↓
SQLAlchemy Model
      ↓
PostgreSQL
```

## 6.2 Database as Consistency Boundary

Application checks are not sufficient for correctness where two workers may race.

Database constraints and transactions must enforce:

- uniqueness,
- idempotency,
- atomic persistence,
- and required concurrency protection.

## 6.3 Historical Evidence Is Append-Oriented

Historical records must not be treated as freely mutable CRUD resources.

At minimum, the persistence design must treat these as append-oriented records:

```text
PaymentEvent
Diagnosis
ActionEvaluation
Decision
PolicyDecision
Outcome
AuditEvent
```

## 6.4 Short Transactions

Database transactions must be short and bounded.

They must never hold a transaction open while performing:

- AI inference,
- arbitrary long-running computation,
- external HTTP calls,
- Razorpay API calls,
- user interaction,
- or waiting for asynchronous external outcomes.

## 6.5 No Silent Defaults for Financially Material Configuration

Persistence configuration errors must fail clearly.

A missing or invalid database URL, credentials, or required migration state must not silently select an unsafe production fallback.

---

# 7. Persistence Entities

The initial relational schema must support the approved domain entities.

The required tables are:

```text
customers
payments
payment_events
recovery_cases
recovery_actions
diagnoses
action_evaluations
decisions
policy_decisions
executions
outcomes
audit_events
raw_events
```

`model_predictions` is a future architectural concern noted by the technical architecture, but it is not required for Phase 2 unless the Architecture Leads explicitly add it to scope. Phase 2 must not introduce speculative persistence only because a later phase may need it.

Supporting tables are permitted only when needed to enforce a concrete Phase 2 requirement.

---

# 8. Identity Model

APRO must distinguish internal persistence identity from provider identity.

## 8.1 Internal Identity

Every domain entity that is persisted receives an APRO-controlled unique identifier.

The internal identifier is the database/application identity.

## 8.2 Provider Identity

Provider references are separate fields.

Examples:

```text
razorpay_payment_id
razorpay_order_id
razorpay_payment_link_id
razorpay_event_id
```

Provider IDs must not be used as APRO's general internal primary-key abstraction.

## 8.3 Event Identity

A provider event must be uniquely identifiable for idempotent processing.

The Phase 2 persistence layer must support a uniqueness guarantee equivalent to:

```text
(provider, provider_event_id)
```

The exact column names may follow the existing repository conventions, but the semantic uniqueness requirement is mandatory.

## 8.4 Execution Idempotency Identity

Phase 2 must provide persistence primitives for an idempotency key associated with an externally meaningful recovery action/execution.

The exact final action/execution workflow belongs to later phases, but the database must be capable of enforcing a single logical execution for a single idempotency key.

---

# 9. Raw Provider Event Storage

Raw Razorpay events must be stored separately from normalized domain data.

Conceptual flow:

```text
Verified Provider Event
        ↓
raw_events
        ↓
Phase 3 Normalizer
        ↓
payment_events
```

## 9.1 Raw Event Responsibilities

`raw_events` must retain enough information to support:

- debugging,
- audit investigation,
- replay in a future controlled workflow,
- parser/normalizer improvements,
- and integration testing.

## 9.2 Raw Payload Representation

For the current prototype, storing the raw payload in PostgreSQL using an appropriate structured JSON type is preferred for simplicity and reproducibility.

The schema may additionally retain a payload/reference field so that a future object-storage implementation can be introduced without changing the domain model.

The implementation must not duplicate the raw provider payload into every domain entity.

## 9.3 Trust Boundary

Persisting a raw event does **not** make it a trusted canonical event.

Only verified inbound events may proceed through the trusted application pipeline defined by later phases.

Phase 2 stores evidence; it does not implement canonical event trust/normalization.

---

# 10. Money Semantics

All persisted financial amounts must use integer minor units.

Examples:

```text
₹699 → 69900 paise
```

Every monetary value must retain its currency context.

Required semantics:

```text
amount_minor = integer
currency = explicit ISO-style currency code
```

Floating-point database fields must not be used for APRO financial amounts.

This applies to:

- payment amount,
- recovery amount,
- recoverable amount,
- action cost,
- expected recovery value,
- recovered amount,
- and equivalent financial fields introduced within this phase.

---

# 11. Time Semantics

All persisted timestamps must be timezone-aware UTC timestamps.

The application may convert to local time only at presentation boundaries.

Naive timestamps are not permitted in persisted APRO records.

The implementation must preserve timezone semantics through SQLAlchemy and PostgreSQL rather than relying only on application convention.

---

# 12. Relational Schema Requirements

The exact column names may follow a consistent implementation convention, but the following semantic structure is mandatory.

## 12.1 `customers`

Purpose: durable customer context and historical aggregates already defined by the domain model.

Requirements:

- internal primary key / customer ID,
- external reference where present,
- timestamps,
- historical counters,
- uniqueness appropriate to the internal customer identity.

No speculative personally identifiable data fields should be added merely for future functionality.

## 12.2 `payments`

Purpose: durable current payment state and provider references.

Requirements:

- internal payment ID,
- customer relationship,
- provider,
- provider payment reference where available,
- provider order reference where available,
- amount in minor units,
- currency,
- payment method,
- payment status,
- created/updated timestamps,
- captured/failed timestamps where applicable.

Provider identity constraints must prevent ambiguous duplicate provider payment records.

## 12.3 `raw_events`

Purpose: immutable provider evidence.

Requirements:

- internal raw-event identifier,
- provider,
- provider event ID,
- event type where available,
- received timestamp,
- raw payload,
- verification/trust metadata needed to explain ingestion state,
- uniqueness on provider event identity.

The raw payload is evidence, not normalized domain truth.

## 12.4 `payment_events`

Purpose: canonicalized historical payment events.

Requirements:

- internal event identifier,
- provider information,
- event type,
- payment reference,
- amount/currency/method,
- status,
- failure fields,
- event timestamp,
- received timestamp,
- raw payload reference.

The Phase 2 layer stores the record but does not implement the Phase 3 normalizer that constructs it.

## 12.5 `recovery_cases`

Purpose: durable recovery workflow state.

Requirements:

- case ID,
- payment ID,
- customer ID,
- lifecycle status,
- opened/updated/closed timestamps,
- recovery amount where applicable,
- attempt count,
- stop/escalation reasons.

## 12.6 `recovery_actions`

Purpose: durable action lifecycle record.

Requirements:

- action ID,
- case ID,
- action type,
- action status,
- timestamps,
- provider reference where applicable,
- execution mode,
- action parameters where required by the domain contract,
- support for later idempotency association.

## 12.7 `diagnoses`

Purpose: immutable historical diagnosis records.

Requirements:

- diagnosis ID,
- case ID,
- failure category,
- confidence,
- evidence,
- model name/version,
- creation timestamp.

The table is historical and append-oriented.

## 12.8 `action_evaluations`

Purpose: immutable per-action evaluation history.

Requirements:

- evaluation ID,
- case ID,
- action type,
- success probability,
- recoverable amount,
- action cost,
- expected recovery value,
- model name/version,
- creation timestamp.

Financial values are integer minor units.

## 12.9 `decisions`

Purpose: immutable decision history.

Requirements:

- decision ID,
- case ID,
- recommended action,
- confidence,
- expected recovery value,
- reason,
- model name/version,
- creation timestamp.

## 12.10 `policy_decisions`

Purpose: immutable policy authorization history.

Requirements:

- policy decision ID,
- decision ID,
- case ID,
- policy result,
- reason/reason code,
- policy version,
- creation timestamp.

The table must support later audit reconstruction.

## 12.11 `executions`

Purpose: durable execution attempt record.

Requirements:

- execution ID,
- action ID,
- case ID,
- execution type,
- execution mode,
- execution status,
- provider reference where applicable,
- timestamps,
- error information where applicable,
- idempotency key or equivalent uniqueness mechanism.

Phase 2 does not execute anything; it only establishes durable persistence for execution records.

## 12.12 `outcomes`

Purpose: immutable observed result of an execution.

Requirements:

- outcome ID,
- case ID,
- execution ID,
- outcome type,
- amount recovered,
- evidence reference,
- observed timestamp.

## 12.13 `audit_events`

Purpose: append-oriented reconstruction of material APRO decisions and actions.

Requirements:

- audit event ID,
- case ID where applicable,
- event type,
- actor,
- timestamp,
- payload,
- correlation ID where available.

Audit events must be insert-oriented and must not be silently overwritten.

---

# 13. Relationships and Referential Integrity

Foreign-key relationships must preserve the domain relationships already defined.

At minimum:

```text
customers
   ↓
payments
   ↓
recovery_cases
   ↓
recovery_actions
   ↓
executions
   ↓
outcomes
```

and:

```text
payments
   ↓
payment_events
```

and:

```text
recovery_cases
   ├── diagnoses
   ├── action_evaluations
   ├── decisions
   ├── policy_decisions
   ├── recovery_actions
   ├── executions
   ├── outcomes
   └── audit_events
```

The implementation must choose foreign-key behavior that does not accidentally erase audit/history when mutable parent state changes.

Historical records must not be casually deleted through cascading deletes.

---

# 14. Index and Constraint Requirements

The schema must create indexes for high-value operational access paths and constraints for correctness.

At minimum consider and implement the following where appropriate:

- provider + provider event ID uniqueness,
- provider + provider payment ID uniqueness,
- foreign-key access paths,
- recovery-case lookup by payment,
- recovery-action lookup by case,
- execution lookup by case/action,
- audit lookup by case and timestamp,
- event lookup by payment and event timestamp.

Indexes must be justified by actual Phase 2 access patterns rather than added indiscriminately.

---

# 15. Repository Architecture

Repositories are application-facing persistence ports.

They must not expose raw SQLAlchemy internals to the domain layer.

The exact repository set should be the minimum needed to express real APRO workflows and persistence tests.

At minimum, the architecture must support repositories equivalent to:

```text
CustomerRepository
PaymentRepository
PaymentEventRepository
RawEventRepository
RecoveryCaseRepository
RecoveryActionRepository
DiagnosisRepository
ActionEvaluationRepository
DecisionRepository
PolicyDecisionRepository
ExecutionRepository
OutcomeRepository
AuditEventRepository
```

A repository is not required merely because a table exists. Antigravity may combine tightly coupled persistence responsibilities where doing so preserves clear transactional semantics and does not create a generic “god repository.”

Repositories should expose domain-oriented operations such as:

```text
get_by_id
save
update_state
find_by_provider_identity
find_by_case_id
find_by_payment_id
append
```

only where the operation has real workflow value.

Generic unrestricted CRUD methods are not required.

---

# 16. Session and Transaction Architecture

The persistence layer must provide a clear transaction/session abstraction.

The domain must not create or commit database transactions directly.

## 16.1 Transaction Ownership

The application/service layer that coordinates a logical persistence operation owns the transaction boundary.

Repositories participate in that transaction.

Conceptually:

```text
Application operation
      ↓
BEGIN transaction
      ↓
repository calls
      ↓
validation / constraint checks
      ↓
COMMIT
```

or:

```text
ROLLBACK
```

on failure.

## 16.2 No Long-Lived Transactions

Do not hold database transactions across:

- AI inference,
- external API requests,
- webhook waiting,
- sleep/cooldown intervals,
- human approval,
- or asynchronous observation windows.

## 16.3 Atomicity

Operations that must either all persist or all disappear must be executed in one transaction.

Phase 2 must provide the primitive required for later phases to perform atomic combinations such as:

```text
persist event identity
+
persist related event record
+
persist related state mutation
```

when the later application workflow requires that atomicity.

Phase 2 does not itself implement the Phase 3 event-processing workflow.

---

# 17. Idempotency Architecture

Idempotency has two distinct layers.

## 17.1 Provider Event Idempotency

A repeated provider event must not create duplicate logical event identity.

Database uniqueness must enforce:

```text
(provider, provider_event_id)
```

The application must interpret the uniqueness conflict as a duplicate condition rather than an unhandled system corruption.

## 17.2 Execution Idempotency

An externally meaningful action must have a durable idempotency key.

A repeated attempt using the same logical idempotency key must resolve to the existing execution state or an equivalent safe outcome rather than creating a second logical execution.

Phase 2 must provide:

- a unique constraint,
- repository lookup,
- transaction-safe insertion,
- and deterministic duplicate handling support.

The actual external side-effect workflow belongs to later phases.

---

# 18. Concurrency Model

Phase 2 must explicitly protect against common races.

## 18.1 Same Event, Two Workers

Two workers processing the same provider event must not create two logical event identities.

Primary protection:

- unique database constraint,
- transactional insertion,
- duplicate conflict handling.

## 18.2 Same Mutable Record, Two Workers

For mutable payment/case/action/execution state, the implementation must prevent two concurrent writes from silently overwriting each other when a state transition depends on the previous state.

Use the simplest reliable technique for each operation, such as:

- conditional update based on expected current state,
- row-level locking for tightly coupled state transitions,
- or another explicit concurrency strategy.

Do not default to global `SERIALIZABLE` isolation for everything without evidence that it is required.

## 18.3 Payment Becomes Captured During Recovery Work

Persistence must support re-checking durable payment state before a later phase performs an externally meaningful recovery action.

Phase 2 must not assume that a previously read state remains current forever.

The database must make the authoritative current state observable to the policy/execution workflow in later phases.

---

# 19. State Transition Persistence

Phase 1 state transition functions remain the source of domain legality.

Persistence must not create a second competing state machine.

The intended pattern is:

```text
Load durable entity
        ↓
Phase 1 domain transition function
        ↓
resulting domain entity
        ↓
transactional persistence
```

Persistence is responsible for storing a legal domain result and protecting concurrent updates.

It must not independently invent alternate legal transitions.

---

# 20. Historical Record Immutability

The application must treat the following as append-only historical facts:

```text
PaymentEvent
Diagnosis
ActionEvaluation
Decision
PolicyDecision
Outcome
AuditEvent
```

Phase 2 must prevent normal repository operations from silently turning these into update-in-place records.

A repository may expose append/create operations and retrieval operations without exposing arbitrary mutation methods.

Delete behavior must be deliberately restricted and must not be used as normal business workflow.

---

# 21. Audit Persistence

Audit persistence is required in Phase 2 but audit generation logic belongs to later workflows.

The audit store must be able to persist:

```text
case_id
case/event context where available
event_type
actor
timestamp
payload
correlation_id
```

Later policy/decision workflows must be able to reconstruct why a financial action was considered, authorized, blocked, or executed.

Audit records should be append-oriented and queryable by case and time.

---

# 22. ORM Boundary

SQLAlchemy ORM models must be persistence representations, not the canonical APRO domain models.

A mapping layer must translate:

```text
Pydantic domain model
        ↕
SQLAlchemy persistence model
```

The domain layer must not depend on SQLAlchemy types or session objects.

This separation is mandatory because:

- domain tests must remain database-independent,
- persistence can evolve without redefining domain semantics,
- and infrastructure details must not leak into business logic.

---

# 23. Async Architecture

The planned backend stack uses FastAPI and SQLAlchemy.

Phase 2 should use SQLAlchemy 2.x's async API in the infrastructure layer.

The async boundary belongs in persistence/application infrastructure, not in the pure domain state machines.

Conceptually:

```text
FastAPI / application
        ↓ async
Repository implementation
        ↓ async
SQLAlchemy AsyncSession
        ↓
PostgreSQL
```

Phase 1 domain functions remain synchronous and deterministic.

---

# 24. Migrations

Alembic must manage schema evolution.

Requirements:

- an initial migration creates the Phase 2 schema,
- a fresh PostgreSQL database can be migrated to the current schema deterministically,
- migration history is committed to Git,
- schema changes are not performed manually as part of the normal workflow,
- application startup must not silently mutate schema in place unless explicitly designed and approved.

Downgrade behavior should be tested where practical, but a safe forward migration path is the primary requirement.

---

# 25. Configuration

The database connection must be configured through environment-backed configuration.

At minimum:

```text
DATABASE_URL
```

must be supported through the project's existing configuration strategy.

Credentials must never be hardcoded or committed.

Phase 2 must remain compatible with the project's explicit environment separation:

```text
SIMULATION
TEST_MODE
```

No live-money environment is introduced by Phase 2.

---

# 26. Testing Architecture

Phase 2 testing must be divided into layers.

## 26.1 Existing Unit Tests

Phase 1 domain tests must continue to pass unchanged.

Domain unit tests must remain free of database dependencies.

## 26.2 Persistence Unit Tests

Test pure mapping/translation behavior where practical without requiring a full database.

## 26.3 PostgreSQL Integration Tests

Real PostgreSQL must be used to prove:

- migrations,
- schema constraints,
- repository round trips,
- foreign-key behavior,
- timestamp semantics,
- monetary persistence,
- uniqueness constraints,
- transaction behavior,
- and concurrency/idempotency guarantees.

Mocks alone are insufficient evidence for database correctness.

## 26.4 Migration Tests

A fresh empty database must be migratable from zero to the current schema.

The resulting schema must be usable by the repository layer.

## 26.5 Transaction Tests

At minimum prove:

```text
successful transaction → all intended writes persist
failed transaction → intended writes rollback
```

## 26.6 Idempotency Tests

At minimum prove:

```text
duplicate provider event identity → no duplicate logical event record
same execution idempotency key → no duplicate execution record
```

## 26.7 Concurrency Tests

At minimum prove a representative race where two concurrent workers attempt the same protected operation.

The result must preserve the invariant rather than silently duplicating or corrupting state.

---

# 27. Required Phase 2 Acceptance Criteria

Phase 2 is complete only when all of the following are true.

## Database

1. PostgreSQL is the primary persistence database.
2. A fresh database can be initialized reproducibly through Alembic.
3. Schema creation does not depend on manual SQL steps.

## Domain Persistence

4. All in-scope Phase 1 domain entities have durable persistence support.
5. Domain models remain database-agnostic.
6. Repository boundaries are explicit.

## Correctness

7. Provider event identity is protected by a database uniqueness constraint.
8. Execution idempotency has durable uniqueness support.
9. Historical records are append-oriented.
10. Foreign-key relationships preserve domain integrity.
11. Money is stored as integer minor units with explicit currency.
12. Persisted timestamps are timezone-aware UTC.

## Transactions

13. Critical multi-write operations have transaction support.
14. A representative failure test proves rollback.
15. Transactions are not held across AI or external network operations.

## Concurrency

16. A representative same-event race cannot create duplicate logical event identity.
17. A representative mutable-state race cannot silently overwrite a required state-dependent update.

## Raw Evidence

18. Raw provider events are stored separately from normalized domain entities.
19. Raw event identity and payload/reference remain queryable.

## Audit

20. Audit records can be persisted and queried by case/time context.

## Quality

21. Existing Phase 1 tests continue to pass.
22. PostgreSQL integration tests pass against a real PostgreSQL environment.
23. Ruff passes.
24. Mypy passes.
25. No secrets are committed.
26. No Phase 3+ business workflow has been introduced under the label of persistence.

---

# 28. Explicit Non-Goals / Boundary Protection

The following are deliberately deferred:

```text
Raw event
    ↓
canonical event normalization       ← Phase 3
    ↓
payment state application          ← Phase 3
    ↓
recovery case orchestration         ← Phase 4
    ↓
AI diagnosis                       ← Phase 7
    ↓
AI recovery prediction             ← Phase 8
    ↓
economic selection                ← Phase 9
    ↓
policy authorization               ← Phase 10
    ↓
execution                          ← Phase 11+
```

Phase 2 may create the persistence capabilities those phases depend on, but it must not implement their business logic.

---

# 29. Expected Implementation Shape

The target implementation should fit the existing repository incrementally.

A reasonable conceptual shape is:

```text
src/apro/
├── domain/
├── persistence/
│   ├── models/
│   ├── repositories/
│   ├── mappings/
│   ├── session.py
│   └── unit_of_work.py
├── config.py
└── main.py

migrations/
├── env.py
└── versions/

tests/
├── domain/
└── persistence/
```

This is a target concept, not a mandate to create every directory regardless of need.

Antigravity may choose an equivalent structure if it preserves all architectural boundaries and acceptance criteria.

---

# 30. Architecture Lead Review Gate

Before implementation begins, the Architecture Leads must explicitly confirm this specification is locked.

Once locked:

1. Antigravity receives the separate Phase 2 implementation plan.
2. Antigravity implements only the approved scope.
3. Antigravity runs the required test/quality gates.
4. Architecture Leads review implementation against this specification.
5. Only after a PASS may Phase 2 be committed and closed.

Any conflict or missing requirement discovered during implementation must trigger:

```text
STOP
↓
REPORT
↓
ARCHITECTURE DECISION
↓
SPECIFICATION UPDATE IF NEEDED
↓
CONTINUE
```

---

# 31. Architecture Decisions Captured by This Specification

The following decisions are the intended Phase 2 baseline:

| Decision | Locked Direction |
|---|---|
| Primary database | PostgreSQL |
| ORM/persistence toolkit | SQLAlchemy 2.x |
| Persistence API | Async infrastructure layer |
| Migration tool | Alembic |
| Domain/ORM separation | Mandatory |
| Provider event uniqueness | Database-enforced |
| Execution idempotency | Durable, database-enforced |
| Historical record behavior | Append-oriented |
| Raw provider event storage | Separate `raw_events` persistence |
| Money representation | Integer minor units + currency |
| Time representation | UTC-aware timestamps |
| Transaction style | Short, explicit, operation-scoped |
| Concurrency | Explicit protection; simplest mechanism satisfying invariant |
| Database test requirement | Real PostgreSQL integration tests |
| Live-money support | Prohibited in v1 |

---

# 32. Open Questions for Architecture Review

The following questions must be explicitly settled before the specification is locked if they are not already accepted by the Architecture Leads:

1. Whether internal primary identifiers should be UUIDs/UUIDv4 or another APRO-controlled identifier form.
2. Whether PostgreSQL JSONB is the approved Phase 2 representation for raw payload storage, with optional future object-storage references.
3. The preferred concurrency mechanism for mutable payment/case state when the concrete repository operations are defined: conditional updates, row-level locking, or a narrowly-scoped combination.
4. The exact repository/unit-of-work API surface, provided it remains consistent with this architecture.

These are implementation-facing details, but they are sufficiently consequential to lock before coding rather than allowing them to emerge accidentally during implementation.

---

# 33. Definition of Done

Phase 2 is formally complete only when:

```text
Specification LOCKED
        ↓
Implementation PLAN approved
        ↓
PostgreSQL persistence implemented
        ↓
Migrations verified
        ↓
Repositories verified
        ↓
Transactions verified
        ↓
Idempotency verified
        ↓
Concurrency verified
        ↓
Real PostgreSQL tests passing
        ↓
Ruff + Mypy passing
        ↓
Architecture review PASS
        ↓
Approved Git commit(s)
        ↓
Working tree clean except explicitly pre-existing excluded work
        ↓
PHASE 2 CLOSED
```

**Status:** This document is an Architecture Lead proposal and must be reviewed/locked before implementation.
