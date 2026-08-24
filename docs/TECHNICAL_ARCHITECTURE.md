\# APRO — Technical Architecture Specification



\*\*Project:\*\* Adaptive Payment Recovery Orchestrator

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Owner:\*\* Vidisha

\*\*Status:\*\* Architecture Specification

\*\*Architecture Version:\*\* 1.0



\---



\# 1. Architecture Objective



APRO must be implemented as a reliable, explainable and testable adaptive revenue-recovery system.



The architecture must separate:



1\. payment facts,

2\. payment-state management,

3\. AI/ML intelligence,

4\. economic decisioning,

5\. policy enforcement,

6\. action execution,

7\. outcome observation,

8\. auditability,

9\. and evaluation.



The architecture must prevent an AI model from directly controlling unrestricted financial actions.



The mandatory decision flow is:



\*\*EVENT → STATE → DIAGNOSIS → EVALUATION → POLICY → EXECUTION → OUTCOME\*\*



\---



\# 2. Architectural Style



APRO v1 will use a:



\## Modular Monolith



The first production-quality prototype will not use microservices.



The system will have clear internal module boundaries while running as a single deployable backend application.



Primary reasons:



\* lower operational complexity,

\* faster development,

\* easier local testing,

\* simpler debugging,

\* simpler deployment,

\* clearer code ownership,

\* easier demonstration,

\* easier review by Razorpay engineers.



Microservices, message brokers and distributed infrastructure will only be introduced if a concrete requirement emerges.



Architecture complexity must be justified by a demonstrated need.



\---



\# 3. High-Level Architecture



```text

&#x20;                        ┌──────────────────────┐

&#x20;                        │  Razorpay Test Mode  │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                Webhooks

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │   Webhook Gateway    │

&#x20;                        │ Verify + Dedupe      │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │ Event Normalizer     │

&#x20;                        │ Razorpay → Canonical│

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │ Payment State Engine │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │ Recovery Case        │

&#x20;                        │ Manager              │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │ Diagnosis Engine     │

&#x20;                        │ AI / ML              │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │ Recovery Intelligence│

&#x20;                        │ AI / ML + Economics  │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                                   ▼

&#x20;                        ┌──────────────────────┐

&#x20;                        │ Policy / Constitution│

&#x20;                        │ Gate                 │

&#x20;                        └──────────┬───────────┘

&#x20;                                   │

&#x20;                        ┌──────────┴──────────┐

&#x20;                        │                     │

&#x20;                      ALLOW              HUMAN REVIEW

&#x20;                        │                     │

&#x20;                        ▼                     ▼

&#x20;                ┌────────────────┐     ┌───────────────┐

&#x20;                │ Action Executor│     │ Escalation    │

&#x20;                └───────┬────────┘     │ Queue         │

&#x20;                        │              └───────────────┘

&#x20;                ┌───────┴────────┐

&#x20;                │                │

&#x20;                ▼                ▼

&#x20;       ┌────────────────┐  ┌──────────────┐

&#x20;       │ Razorpay       │  │ Simulation   │

&#x20;       │ Adapter        │  │ Adapter      │

&#x20;       └───────┬────────┘  └──────┬───────┘

&#x20;               │                  │

&#x20;               └────────┬─────────┘

&#x20;                        ▼

&#x20;                ┌────────────────┐

&#x20;                │ Outcome        │

&#x20;                │ Processor      │

&#x20;                └───────┬────────┘

&#x20;                        │

&#x20;                ┌───────┴──────────┐

&#x20;                ▼                  ▼

&#x20;         ┌──────────────┐   ┌──────────────┐

&#x20;         │ Audit Trail  │   │ Metrics /    │

&#x20;         │              │   │ Evaluation   │

&#x20;         └──────────────┘   └──────────────┘

```



\---



\# 4. Core Architectural Boundaries



APRO will maintain the following boundaries:



\## Boundary A — External Payment Provider



Razorpay-specific APIs and webhook formats.



\## Boundary B — Canonical Payment Domain



Provider-independent payment events and states.



\## Boundary C — Intelligence



Diagnosis, prediction and recovery-value estimation.



\## Boundary D — Governance



Policy and Constitution enforcement.



\## Boundary E — Execution



Performing only approved actions.



\## Boundary F — Observation



Determining what actually happened after execution.



\## Boundary G — Evaluation



Measuring recovery and comparing strategies.



No module should bypass these boundaries without an explicit architectural reason.



\---



\# 5. Webhook Gateway



\## Responsibility



The Webhook Gateway is responsible for receiving and validating Razorpay webhook requests.



It must:



\* receive webhook requests,

\* preserve the original request body,

\* verify the Razorpay webhook signature,

\* extract event identity,

\* identify the event type,

\* perform duplicate detection,

\* pass valid events to the normalization layer.



It must not:



\* diagnose failures,

\* select recovery actions,

\* execute recovery actions,

\* modify financial state based solely on an unverified event.



\---



\# 6. Webhook Security



Webhook signature verification must occur before the event is trusted.



The verification layer must use the exact raw request body required for signature verification.



The system must reject invalid signatures.



The raw payload should be retained for debugging/audit purposes according to the project's data-retention policy.



\---



\# 7. Event Idempotency



Webhook delivery must be treated as potentially duplicated.



The system must maintain an idempotency mechanism using the appropriate event identity.



Processing the same event multiple times must not result in:



\* duplicate Recovery Cases,

\* duplicate decisions,

\* duplicate Payment Links,

\* duplicate outreach,

\* duplicate execution.



Idempotency must be enforced at the application/data layer rather than relying solely on the sender.



\---



\# 8. Event Normalizer



The Event Normalizer converts provider-specific Razorpay payloads into APRO's canonical event model.



Architecture:



```text

Razorpay Webhook

&#x20;     ↓

Webhook Verification

&#x20;     ↓

Razorpay Adapter

&#x20;     ↓

Canonical PaymentEvent

```



The rest of APRO must operate primarily on the canonical model rather than directly reading Razorpay-specific nested payload structures.



\---



\# 9. Canonical Payment Event



The canonical event model should contain fields such as:



```text

event\_id

event\_type

provider

payment\_id

order\_id

amount

currency

method

status

failure\_code

failure\_source

failure\_step

failure\_reason

failure\_description

timestamp

raw\_event\_reference

```



The model may be extended as implementation requirements become clearer.



Provider-specific fields should not leak unnecessarily into the domain layer.



\---



\# 10. Payment State Engine



The Payment State Engine determines the current known state of a payment.



The initial state vocabulary includes:



```text

CREATED

AUTHORIZED

CAPTURED

FAILED

PENDING

```



APRO recovery-specific states are separate from the underlying payment state.



The state engine must enforce valid transitions.



Example:



```text

CREATED

&#x20;  ↓

AUTHORIZED

&#x20;  ↓

CAPTURED

```



Failure path:



```text

CREATED

&#x20;  ↓

FAILED

&#x20;  ↓

RECOVERY\_PENDING

&#x20;  ↓

RECOVERING

&#x20;  ↓

CAPTURED

```



A payment state transition must be determined by payment evidence, not by an AI prediction.



\---



\# 11. Recovery Case Manager



A Recovery Case represents APRO's recovery workflow around a payment.



It is distinct from the payment itself.



Conceptually:



```text

Payment

&#x20;  │

&#x20;  └── Recovery Case

&#x20;         ├── Diagnosis

&#x20;         ├── Candidate Actions

&#x20;         ├── Decision

&#x20;         ├── Policy Result

&#x20;         ├── Execution

&#x20;         └── Outcome

```



The Recovery Case Manager is responsible for:



\* creating cases,

\* updating cases,

\* maintaining case state,

\* associating decisions with cases,

\* associating actions with cases,

\* preventing duplicate recovery workflows.



\---



\# 12. Recovery Case States



Initial recovery workflow states:



```text

NEW

DIAGNOSING

EVALUATING

DECISION\_PENDING

POLICY\_CHECK

ACTION\_APPROVED

EXECUTING

OBSERVING

RECOVERED

STOPPED

ESCALATED

```



The exact transition graph will be enforced by the domain layer.



\---



\# 13. Diagnosis Engine



The Diagnosis Engine answers:



> \*\*Why is this payment currently failing?\*\*



Input:



```text

Canonical PaymentEvent

\+

Payment History

\+

Recovery History

\+

Context

```



Output:



```text

DiagnosisResult

```



containing:



```text

failure\_category

confidence

evidence

model\_version

```



Initial failure categories:



```text

TRANSIENT

BANK\_SIDE

CUSTOMER\_SIDE

AUTHENTICATION

PAYMENT\_METHOD

GATEWAY

TIMEOUT

UNKNOWN

```



\---



\# 14. Diagnosis Architecture



```text

Payment Context

&#x20;     ↓

Feature Builder

&#x20;     ↓

Diagnosis Model

&#x20;     ↓

Probability / Confidence

&#x20;     ↓

DiagnosisResult

```



The model may initially be a supervised classification model.



Candidate technologies include:



\* scikit-learn,

\* XGBoost,

\* LightGBM,

\* calibrated probabilistic classifiers.



The final model must be selected through evaluation.



The most complex model is not automatically the preferred model.



\---



\# 15. Recovery Intelligence Engine



The Recovery Intelligence Engine answers:



> \*\*What should happen next?\*\*



It receives:



```text

Payment Context

\+

DiagnosisResult

\+

Recovery History

\+

Candidate Actions

```



and produces an evaluation for each eligible action.



Example:



```text

RETRY

P(success) = 0.72

Expected Value = ₹503



PAYMENT\_LINK

P(success) = 0.51

Expected Value = ₹357



OUTREACH

P(success) = 0.31

Expected Value = ₹217

```



\---



\# 16. Recovery Probability Model



For action `a`:



```text

P(success | context, action)

```



represents the predicted probability that the action will recover the payment.



The model must be evaluated on held-out data.



Probability calibration should be evaluated because expected-value calculations depend on meaningful probabilities.



\---



\# 17. Expected Recovery Value



The initial formulation is:



```text

ERV(a)

=

P(success | context, action)

×

Recoverable Amount

−

Action Cost

```



Additional factors may later be introduced if supported by evidence, such as:



\* customer friction,

\* expected delay,

\* operational cost,

\* action-specific constraints.



Any additional factor must be documented and measurable.



\---



\# 18. Candidate Action Generator



The Candidate Action Generator determines which actions are technically and contextually eligible.



Initial action vocabulary:



```text

RETRY

ALTERNATE\_RECOVERY

OUTREACH

ESCALATE

STOP

```



Candidate generation must not itself execute actions.



\---



\# 19. Decision Engine



The Decision Engine compares eligible actions.



Conceptually:



```text

Eligible Actions

&#x20;     ↓

Recovery Probability

&#x20;     ↓

Expected Recovery Value

&#x20;     ↓

Ranking

&#x20;     ↓

Recommendation

```



The output must include:



```text

recommended\_action

candidate\_evaluations

expected\_value

confidence

reason

```



The Decision Engine does not have execution authority.



\---



\# 20. Policy / Constitution Gate



The Policy Gate is deterministic.



Its purpose is to ensure that optimization does not bypass safety.



Input:



```text

Recommendation

\+

Current Payment State

\+

Recovery Case

\+

Policy Configuration

```



Output:



```text

ALLOW

BLOCK

REQUIRE\_HUMAN\_APPROVAL

```



\---



\# 21. Example Policy Rules



Initial rules may include:



```text

IF payment.status == CAPTURED

→ BLOCK ALL RECOVERY ACTIONS



IF retry\_count >= MAX\_RETRIES

→ BLOCK RETRY



IF diagnosis\_confidence < MIN\_CONFIDENCE

→ REQUIRE\_HUMAN\_APPROVAL



IF amount >= HIGH\_VALUE\_THRESHOLD

→ REQUIRE\_HUMAN\_APPROVAL



IF action is unsupported

→ BLOCK



IF expected\_value < MIN\_EXPECTED\_VALUE

→ STOP

```



These values must be configurable and documented.



\---



\# 22. Constitution Enforcement



The project Constitution is the source of architectural principles.



The Policy Engine is the executable implementation of relevant operational rules.



Therefore:



```text

PROJECT CONSTITUTION

&#x20;       ↓

Policy Definitions

&#x20;       ↓

Policy Engine

&#x20;       ↓

Decision Gate

```



The Constitution itself must not be treated as executable code.



\---



\# 23. Execution Layer



The Execution Layer performs only actions approved by the Policy Gate.



It must not independently optimize or select actions.



Architecture:



```text

Decision

&#x20;  ↓

Policy Gate

&#x20;  ↓

ApprovedAction

&#x20;  ↓

Executor

```



\---



\# 24. Executor Types



Initial executor interfaces:



```text

RetryExecutor

PaymentLinkExecutor

OutreachExecutor

EscalationExecutor

NoOpExecutor

```



Not all executors must initially perform real external actions.



Each executor must clearly identify whether it is:



\* real Test Mode,

\* simulated,

\* or internal-only.



\---



\# 25. Razorpay Adapter



Razorpay-specific API calls must be isolated behind an adapter.



The domain/application layer should not directly depend on Razorpay HTTP details.



Example:



```text

APRO Application

&#x20;     ↓

RazorpayGateway Interface

&#x20;     ↓

Razorpay Adapter

&#x20;     ↓

Razorpay API

```



This makes testing and simulation easier.



\---



\# 26. Payment Link Executor



The Payment Link Executor will initially be the primary real recovery-action demonstration.



Flow:



```text

Approved Payment Link Action

&#x20;         ↓

PaymentLinkExecutor

&#x20;         ↓

Razorpay Adapter

&#x20;         ↓

Create Test Payment Link

&#x20;         ↓

Await Payment Result

&#x20;         ↓

Webhook / Outcome

```



The executor must record the created Payment Link reference.



It must not create duplicate links if the same action is retried due to duplicate events.



\---



\# 27. Retry Executor



Retry must remain provider-capability-aware.



The architecture must not assume a generic payment retry endpoint.



The Retry Executor will initially expose an internal interface.



Its concrete implementation will be selected only after validating the supported Razorpay Test Mode workflow.



Possible initial modes:



```text

REAL\_TEST\_MODE

SIMULATED

```



The mode must be explicit.



\---



\# 28. Outreach Executor



The Outreach Executor initially operates in simulation mode.



It records:



```text

message

channel

timestamp

case\_id

delivery\_status

```



Synthetic outcome generation may later determine whether the outreach resulted in recovery.



\---



\# 29. Escalation Executor



The Escalation Executor creates a human-review case.



It must include:



```text

case\_id

reason

recommended\_action

confidence

evidence

previous\_actions

amount

```



No automated financial action occurs after escalation unless a human-approved workflow is explicitly introduced.



\---



\# 30. No-Op / Stop Executor



STOP does not represent an error.



It represents an intentional decision not to intervene.



The No-Op Executor records:



```text

case\_id

stop\_reason

timestamp

decision\_reference

```



and performs no external financial action.



\---



\# 31. Outcome Processor



After execution, APRO observes subsequent evidence.



The Outcome Processor converts observed events into a recovery outcome.



Possible outcomes:



```text

RECOVERED

FAILED

PENDING

EXPIRED

STOPPED

ESCALATED

```



The system must distinguish:



\*\*Action executed\*\*



from



\*\*Revenue recovered\*\*



Execution does not imply success.



\---



\# 32. Re-Evaluation Loop



If an action fails and recovery remains possible:



```text

Action Failed

&#x20;    ↓

Update Recovery History

&#x20;    ↓

Recalculate Context

&#x20;    ↓

Recalculate Diagnosis if necessary

&#x20;    ↓

Recalculate Candidate Actions

&#x20;    ↓

Recalculate Expected Values

&#x20;    ↓

Policy Gate

```



APRO must not blindly repeat a failed action.



\---



\# 33. Race-Condition Protection



Before any externally meaningful action executes, APRO must verify that the payment is still eligible.



Example:



```text

payment.failed

&#x20;     ↓

Decision made

&#x20;     ↓

payment.captured

&#x20;     ↓

Execution attempted

&#x20;     ↓

STATE CHECK

&#x20;     ↓

BLOCK

```



This is a critical safety mechanism.



\---



\# 34. Database



The primary persistence layer will use PostgreSQL.



The database will store at minimum:



```text

payments

payment\_events

recovery\_cases

recovery\_actions

decisions

policy\_decisions

executions

outcomes

audit\_events

model\_predictions

```



The schema will be designed around the domain model rather than directly mirroring Razorpay payloads.



\---



\# 35. Raw Event Storage



Raw provider events should be stored separately from normalized domain data.



Conceptually:



```text

raw\_events

&#x20;   ↓

normalized payment\_events

&#x20;   ↓

domain state

```



This allows:



\* debugging,

\* replay,

\* audit investigation,

\* parser improvements,

\* integration testing.



\---



\# 36. Audit Trail



The audit layer records the decision history.



It should be append-oriented.



An audit record should capture:



```text

timestamp

case\_id

event\_id

payment\_state

diagnosis

diagnosis\_confidence

candidate\_actions

expected\_values

recommendation

policy\_result

execution\_result

outcome

model\_version

policy\_version

```



The audit trail must make a case reconstructable.



\---



\# 37. Model Versioning



Every AI-generated decision must reference the model version used.



Example:



```text

diagnosis\_model\_version = diagnosis-v1

recovery\_model\_version = recovery-v1

```



If a model changes, historical decisions must remain attributable to the model that generated them.



\---



\# 38. Policy Versioning



Policy decisions must also record a policy version.



Example:



```text

policy\_version = policy-v1

```



This makes historical behavior explainable even after policy changes.



\---



\# 39. Simulation Architecture



The simulator must produce canonical events rather than Razorpay-specific payloads.



Architecture:



```text

Scenario Generator

&#x20;      ↓

Synthetic Payment Context

&#x20;      ↓

Synthetic Event Generator

&#x20;      ↓

Canonical PaymentEvent

&#x20;      ↓

APRO

```



The simulator must be able to generate:



\* different failure types,

\* different payment amounts,

\* different histories,

\* different attempt counts,

\* different recovery outcomes,

\* race conditions,

\* duplicate events,

\* API failures,

\* successful recovery,

\* unsuccessful recovery.



\---



\# 40. Deterministic Scenario Seeds



Simulation experiments must be reproducible.



Each benchmark run should support a fixed random seed.



Example:



```text

seed = 42

```



The same seed and configuration should reproduce the same scenario set.



\---



\# 41. Synthetic Customer/Payment History



The simulator may generate:



```text

customer\_id

historical\_success\_rate

historical\_failure\_rate

previous\_methods

previous\_recovery\_results

payment\_frequency

```



Synthetic attributes must be clearly labeled as synthetic.



\---



\# 42. Simulation Outcome Engine



The simulator will determine whether an action succeeds based on controlled scenario parameters.



Example:



```text

Transient failure

\+

Retry

→

high probability of success

```



versus:



```text

Repeated authentication failure

\+

Retry

→

low probability of success

```



The outcome engine must be separate from the model making the decision.



This prevents the evaluation model from secretly controlling the ground truth.



\---



\# 43. Avoiding Evaluation Leakage



The recovery model must not receive the ground-truth outcome as an input.



Example:



The model may receive:



```text

failure\_reason

amount

history

attempt\_count

```



but must not receive:



```text

future\_success = true

```



Ground truth is used only after the decision to evaluate the decision.



\---



\# 44. Benchmark Architecture



Benchmark runner:



```text

Scenario Dataset

&#x20;     │

&#x20;     ├──────────────┐

&#x20;     ▼              ▼

Baseline A       Baseline B

&#x20;     │              │

&#x20;     └──────┬───────┘

&#x20;            ▼

&#x20;       Baseline C

&#x20;            │

&#x20;            ▼

&#x20;          APRO

&#x20;            │

&#x20;            ▼

&#x20;      Outcome Engine

&#x20;            │

&#x20;            ▼

&#x20;       Metrics Engine

```



All strategies must receive equivalent cases.



\---



\# 45. Baseline Strategies



At minimum:



\## Baseline A — No Intervention



Always stop.



\## Baseline B — Always Retry



Retry according to a fixed maximum.



\## Baseline C — Static Rules



Use deterministic rules without learned economic optimization.



\## APRO



Use diagnosis, recovery probability, expected value and policy constraints.



\---



\# 46. Evaluation Metrics



The Metrics Engine will calculate:



```text

Revenue at Risk

Revenue Recovered

Recovery Rate

Incremental Recovery

Intervention Count

Intervention Efficiency

Unnecessary Intervention Rate

Escalation Rate

Stop Rate

Average Decision Latency

```



Additional model metrics:



```text

Diagnosis Accuracy

Precision

Recall

F1

Calibration

```



Model metrics support the system evaluation but do not replace economic metrics.



\---



\# 47. API Layer



FastAPI will expose endpoints for:



```text

POST /webhooks/razorpay



GET /health



GET /cases

GET /cases/{case\_id}



GET /payments/{payment\_id}



GET /decisions/{decision\_id}



GET /audit/{case\_id}



GET /metrics



POST /simulation/runs

GET /simulation/runs/{run\_id}

```



Exact endpoints may change during implementation.



\---



\# 48. API Responsibility



The API layer should remain thin.



It should:



\* validate requests,

\* authenticate where necessary,

\* call application services,

\* return structured responses.



Business logic should not be embedded inside route handlers.



\---



\# 49. Application Layer



The application layer orchestrates use cases.



Examples:



```text

ProcessPaymentEvent

CreateRecoveryCase

DiagnoseRecoveryCase

EvaluateRecoveryActions

ApplyPolicy

ExecuteRecoveryAction

ProcessOutcome

RunSimulation

RunBenchmark

```



\---



\# 50. Domain Layer



The domain layer contains core concepts and rules.



Examples:



```text

Payment

PaymentEvent

RecoveryCase

RecoveryAction

Decision

PolicyDecision

Outcome

```



The domain layer should not depend on:



\* FastAPI,

\* PostgreSQL,

\* Razorpay SDKs,

\* LLM providers,

\* UI frameworks.



\---



\# 51. Infrastructure Layer



Infrastructure contains:



\* PostgreSQL repositories,

\* Razorpay API client,

\* webhook adapter,

\* model persistence,

\* external services,

\* configuration,

\* logging.



This keeps external dependencies isolated.



\---



\# 52. Intelligence Layer



The intelligence layer contains:



```text

features/

diagnosis/

recovery/

training/

evaluation/

```



It should not directly execute actions.



Its outputs must be passed through application and policy layers.



\---



\# 53. LLM Boundary



An LLM is not required for the core financial decision.



If an LLM is later introduced, it may be used for:



\* operator explanations,

\* contextual message generation,

\* case summarization,

\* natural-language investigation.



The LLM must not bypass the Policy Gate.



Architecture:



```text

LLM

&#x20;↓

Explanation / Recommendation

&#x20;↓

Structured validation

&#x20;↓

Policy Gate

```



Never:



```text

LLM

&#x20;↓

Direct financial action

```



\---



\# 54. Frontend Architecture



The dashboard will be implemented after the backend and intelligence pipeline are functional.



Technology:



\*\*React + TypeScript\*\*



Initial screens:



```text

Overview

Recovery Queue

Case Inspector

Decision Inspector

Benchmark

Audit Trail

```



The frontend is a visualization/control surface, not the source of business truth.



\---



\# 55. Observability



The system should provide structured logs for:



\* webhook reception,

\* verification result,

\* event normalization,

\* state transitions,

\* diagnosis,

\* decision,

\* policy result,

\* execution,

\* outcome,

\* errors.



Every important operation should have a correlation identifier.



Example:



```text

case\_id = rc\_00182

```



\---



\# 56. Error Handling



External failures must not automatically become financial decisions.



Examples:



```text

Razorpay API unavailable

&#x20;       ↓

Execution state = UNKNOWN

&#x20;       ↓

Do not assume failure

&#x20;       ↓

Reconcile / retry safely / escalate

```



An API timeout must not be interpreted as:



> “Payment definitely failed.”



\---



\# 57. Security



Initial security requirements:



\* secrets stored in environment variables,

\* `.env` excluded from Git,

\* webhook signature verification,

\* no real payment credentials committed,

\* no real customer data,

\* safe Test Mode only,

\* structured access controls for sensitive operations.



\---



\# 58. Configuration



Configuration must be externalized.



Examples:



```text

DATABASE\_URL

RAZORPAY\_KEY\_ID

RAZORPAY\_KEY\_SECRET

RAZORPAY\_WEBHOOK\_SECRET

MAX\_RETRIES

HIGH\_VALUE\_THRESHOLD

MIN\_CONFIDENCE

MIN\_EXPECTED\_VALUE

ENVIRONMENT

```



No secrets or environment-specific values should be hardcoded.



\---



\# 59. Testing Architecture



Testing will exist at multiple levels.



\## Unit Tests



Test individual domain/intelligence functions.



\## Integration Tests



Test database, API and Razorpay adapters.



\## Simulation Tests



Test full recovery scenarios.



\## Adversarial Tests



Deliberately trigger:



\* duplicate events,

\* stale events,

\* race conditions,

\* API failures,

\* model uncertainty,

\* repeated failures,

\* invalid actions.



\## Regression Tests



Ensure fixes remain fixed.



\---



\# 60. Core Safety Invariants



The following must always remain true:



\### Invariant 1



A payment that is already captured cannot receive a new recovery action.



\### Invariant 2



The same webhook cannot create duplicate execution.



\### Invariant 3



An unapproved action cannot execute.



\### Invariant 4



The AI cannot bypass policy.



\### Invariant 5



Execution does not imply recovery.



\### Invariant 6



A failed action cannot be repeated indefinitely.



\### Invariant 7



Every automated decision must be auditable.



\### Invariant 8



Synthetic results cannot be represented as real merchant revenue.



\---



\# 61. Technology Stack



Initial planned stack:



\## Backend



Python



FastAPI



Pydantic



SQLAlchemy



\## Database



PostgreSQL



\## AI / ML



Python



pandas



scikit-learn



XGBoost or LightGBM if justified by evaluation



\## Testing



pytest



\## Frontend



React



TypeScript



\## Infrastructure



Docker



Docker Compose for local development



\## External Integration



Razorpay Test Mode APIs and Webhooks



The exact dependency versions will be frozen during implementation.



\---



\# 62. Planned Repository Structure



The eventual repository should follow:



```text

APRO/

│

├── docs/

│   ├── PROJECT\_CONSTITUTION.md

│   ├── PROBLEM\_DEFINITION.md

│   ├── COMPETITIVE\_ANALYSIS.md

│   ├── RAZORPAY\_CAPABILITY\_MAP.md

│   ├── PRODUCT\_SPECIFICATION.md

│   └── TECHNICAL\_ARCHITECTURE.md

│

├── backend/

│   ├── api/

│   ├── domain/

│   ├── application/

│   ├── infrastructure/

│   └── main.py

│

├── intelligence/

│   ├── diagnosis/

│   ├── recovery/

│   ├── features/

│   ├── training/

│   └── evaluation/

│

├── simulator/

│   ├── generators/

│   ├── scenarios/

│   ├── outcomes/

│   └── runner/

│

├── dashboard/

│

├── tests/

│   ├── unit/

│   ├── integration/

│   ├── simulation/

│   └── adversarial/

│

├── scripts/

│

├── .env.example

├── .gitignore

├── docker-compose.yml

├── requirements.txt

└── README.md

```



This is the target structure. Directories should be created incrementally as their implementation begins rather than creating empty directories unnecessarily.



\---



\# 63. Architectural Decision Rules



When a new technical requirement appears:



1\. Check the Constitution.

2\. Check the Product Specification.

3\. Check this Architecture Specification.

4\. Prefer the simplest solution that satisfies all three.

5\. Measure before adding complexity.

6\. Document any architectural change.

7\. Never silently bypass a safety boundary.



\---



\# 64. What Is Explicitly Not in the Architecture



The following are intentionally excluded from v1:



\* microservices,

\* Kubernetes,

\* Kafka,

\* distributed event buses,

\* reinforcement learning,

\* autonomous unrestricted financial agents,

\* real-money transactions,

\* unnecessary LLM dependencies,

\* premature optimization.



These may only be reconsidered if a concrete requirement emerges.



\---



\# 65. Architecture Success Criteria



The architecture is successful if it allows APRO to:



1\. receive Razorpay events,

2\. normalize them,

3\. maintain correct payment state,

4\. create recovery cases,

5\. diagnose failures,

6\. evaluate recovery actions,

7\. calculate expected recovery value,

8\. enforce policy,

9\. execute bounded actions,

10\. observe outcomes,

11\. adapt or stop,

12\. maintain an audit trail,

13\. run large simulations,

14\. compare against baselines,

15\. demonstrate real Razorpay Test Mode integration.



\---



\# 66. Final Architecture Principle



APRO must remain a system where:



\*\*Facts are observed.\*\*



\*\*AI interprets uncertainty.\*\*



\*\*Economics rank possibilities.\*\*



\*\*Policy controls authority.\*\*



\*\*Executors perform approved actions.\*\*



\*\*Outcomes determine what actually happened.\*\*



\*\*Metrics determine whether the system was useful.\*\*



No single AI component should control the entire loop.



\---



\# 67. Architecture Status



\*\*Architecture Version:\*\* 1.0



\*\*Status:\*\* Ready for implementation planning.



Any future architectural change must be documented with:



\* problem,

\* proposed change,

\* reason,

\* alternatives considered,

\* impact,

\* decision.



