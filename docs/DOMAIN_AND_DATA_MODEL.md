\# APRO — Domain \& Data Model Specification



\*\*Project:\*\* Adaptive Payment Recovery Orchestrator

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Owner:\*\* Vidisha

\*\*Status:\*\* Domain/Data Specification

\*\*Version:\*\* 1.0



\---



\# 1. Purpose



This document defines the core domain entities, their relationships, state machines and persistence requirements for APRO.



The purpose is to establish a stable domain model before backend implementation begins.



The model must distinguish:



\* what actually happened,

\* what APRO inferred,

\* what APRO decided,

\* what policy permitted,

\* what APRO executed,

\* and what ultimately happened.



\---



\# 2. Domain Model



The core domain consists of:



```text id="t7pkq8"

Customer

Payment

PaymentEvent

RecoveryCase

Diagnosis

Decision

RecoveryAction

PolicyDecision

Execution

Outcome

AuditEvent

```



The primary relationship is:



```text id="3nqf3v"

Customer

&#x20;  │

&#x20;  └── Payment

&#x20;         │

&#x20;         ├── PaymentEvent\[]

&#x20;         │

&#x20;         └── RecoveryCase

&#x20;                │

&#x20;                ├── Diagnosis

&#x20;                ├── Decision

&#x20;                ├── RecoveryAction\[]

&#x20;                ├── PolicyDecision

&#x20;                ├── Execution

&#x20;                └── Outcome



All important transitions

&#x20;       │

&#x20;       └── AuditEvent\[]

```



\---



\# 3. Domain Principles



\## 3.1 Facts vs Predictions



Facts must be stored separately from model predictions.



Example:



```text

payment.status = FAILED

```



is an observed state.



Whereas:



```text

diagnosis.category = TRANSIENT

confidence = 0.87

```



is an AI-generated prediction.



\---



\## 3.2 Immutable Events



Payment events received from the provider should be preserved.



The system should not overwrite historical events to represent current state.



Current state is derived/maintained from the event history.



\---



\## 3.3 Decisions Are Historical Records



Once a decision has been made, the system must preserve:



\* what the model saw,

\* what it predicted,

\* what actions it considered,

\* what it recommended,

\* which model version produced the result.



A later model version must not rewrite historical decisions.



\---



\## 3.4 Policy Decisions Are Separate



The recommendation and the policy decision must be separate records.



Example:



```text id="gl3v98"

AI:

RETRY



Policy:

BLOCK



Final:

STOP

```



This allows us to distinguish:



> What the AI wanted to do



from:



> What the system allowed.



\---



\# 4. Customer



\## Purpose



Represents the synthetic/test customer associated with payments.



Customer information is used primarily as historical context for recovery decisions.



\## Fields



```text id="1wq5dz"

customer\_id

external\_reference

created\_at

updated\_at

```



Optional derived attributes:



```text id="z93q6s"

historical\_payment\_count

historical\_success\_count

historical\_failure\_count

historical\_recovery\_count

```



Derived attributes should be calculated from historical payment records where practical rather than treated as authoritative facts.



\---



\# 5. Payment



\## Purpose



Represents the payment being processed.



A Payment is an external financial object.



APRO does not own the payment lifecycle; Razorpay/Test Mode or the simulator is the source of payment events.



\## Fields



```text id="m8mb7v"

payment\_id

customer\_id

order\_id

provider

amount

currency

method

status

created\_at

updated\_at

```



Optional:



```text id="a1ppkk"

captured\_at

failed\_at

```



\## Status



Initial payment status vocabulary:



```text id="1v5v2s"

CREATED

AUTHORIZED

CAPTURED

FAILED

PENDING

```



Additional provider states may be added if required.



\---



\# 6. PaymentEvent



\## Purpose



Represents an observed payment-related event.



This is the historical record of what happened.



\## Fields



```text id="j3qz2m"

event\_id

provider

event\_type

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

event\_timestamp

received\_at

raw\_payload\_reference

```



\## Properties



PaymentEvent records should be append-oriented.



Events must not be overwritten.



Duplicate events must be detectable using the provider event identity.



\---



\# 7. RecoveryCase



\## Purpose



Represents APRO's attempt to recover revenue associated with a payment.



A payment may have at most one active Recovery Case at a time unless a future version explicitly supports multiple independent recovery campaigns.



\## Fields



```text id="iq6u0s"

case\_id

payment\_id

customer\_id

status

opened\_at

updated\_at

closed\_at

```



Optional:



```text id="5n3i1c"

recovery\_amount

current\_attempt\_count

stop\_reason

escalation\_reason

```



\---



\# 8. RecoveryCase States



Initial state vocabulary:



```text id="xx89p8"

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



\## Terminal states



```text id="k6y0dr"

RECOVERED

STOPPED

ESCALATED

```



\## Non-terminal states



```text id="d4r3u1"

NEW

DIAGNOSING

EVALUATING

DECISION\_PENDING

POLICY\_CHECK

ACTION\_APPROVED

EXECUTING

OBSERVING

```



\---



\# 9. Recovery Case State Transitions



Primary path:



```text id="5t8qk4"

NEW

&#x20;↓

DIAGNOSING

&#x20;↓

EVALUATING

&#x20;↓

DECISION\_PENDING

&#x20;↓

POLICY\_CHECK

&#x20;↓

ACTION\_APPROVED

&#x20;↓

EXECUTING

&#x20;↓

OBSERVING

&#x20;↓

RECOVERED

```



Failure path:



```text id="t9gq4y"

OBSERVING

&#x20;↓

FAILED OUTCOME

&#x20;↓

EVALUATING

```



if another recovery action remains eligible.



Otherwise:



```text id="f4v5gc"

OBSERVING

&#x20;↓

STOPPED

```



or:



```text id="q2khz9"

OBSERVING

&#x20;↓

ESCALATED

```



\---



\# 10. Diagnosis



\## Purpose



Stores APRO's assessment of why the payment is failing.



\## Fields



```text id="kz9w2f"

diagnosis\_id

case\_id

category

confidence

evidence

model\_name

model\_version

created\_at

```



\## Initial Categories



```text id="0k0v9j"

TRANSIENT

BANK\_SIDE

CUSTOMER\_SIDE

AUTHENTICATION

PAYMENT\_METHOD

GATEWAY

TIMEOUT

UNKNOWN

```



A case may receive multiple diagnosis records over time.



The latest valid diagnosis is used for the current decision.



Historical diagnoses remain preserved.



\---



\# 11. RecoveryAction



\## Purpose



Represents a possible or actual recovery action.



\## Initial action vocabulary



```text id="3a6e4u"

RETRY

ALTERNATE\_RECOVERY

OUTREACH

ESCALATE

STOP

```



\## Fields



```text id="q3v9s6"

action\_id

case\_id

action\_type

status

created\_at

updated\_at

```



Optional:



```text id="y3v0w8"

provider\_reference

execution\_mode

parameters

```



\---



\# 12. RecoveryAction Status



Initial vocabulary:



```text id="j3c2g4"

CANDIDATE

RECOMMENDED

APPROVED

BLOCKED

EXECUTING

COMPLETED

FAILED

CANCELLED

```



\---



\# 13. Action Evaluation



Each candidate action may have an evaluation.



\## Fields



```text id="9a8f3z"

evaluation\_id

case\_id

action\_type

success\_probability

recoverable\_amount

action\_cost

expected\_recovery\_value

model\_name

model\_version

created\_at

```



Conceptual calculation:



```text id="7o2jqp"

ERV

=

success\_probability

×

recoverable\_amount

−

action\_cost

```



These values represent model estimates, not guaranteed outcomes.



\---



\# 14. Decision



\## Purpose



Represents APRO's recommendation after evaluating candidate actions.



\## Fields



```text id="r8v3m5"

decision\_id

case\_id

recommended\_action

confidence

expected\_recovery\_value

reason

model\_name

model\_version

created\_at

```



The decision must reference the action evaluations used to produce it.



\---



\# 15. PolicyDecision



\## Purpose



Represents the deterministic governance decision applied after the AI recommendation.



\## Fields



```text id="7z3m8n"

policy\_decision\_id

decision\_id

case\_id

result

reason

policy\_version

created\_at

```



\## Result



```text id="1a7v6h"

ALLOW

BLOCK

REQUIRE\_HUMAN\_APPROVAL

```



\---



\# 16. Execution



\## Purpose



Represents an attempt to perform an approved recovery action.



\## Fields



```text id="k7f3j9"

execution\_id

action\_id

case\_id

execution\_type

execution\_mode

status

provider\_reference

started\_at

completed\_at

error\_code

error\_message

```



\## Execution Mode



```text id="9p8b4t"

RAZORPAY\_TEST\_MODE

SIMULATION

INTERNAL

```



This is important because the project must clearly distinguish real Test Mode actions from simulated actions.



\---



\# 17. Execution Status



```text id="4m8q2z"

PENDING

RUNNING

SUCCEEDED

FAILED

UNKNOWN

CANCELLED

```



`UNKNOWN` is important.



An API timeout must not automatically be interpreted as:



> Payment failed.



The system may need reconciliation.



\---



\# 18. Outcome



\## Purpose



Represents the observed result after an action.



\## Fields



```text id="p7k3z1"

outcome\_id

case\_id

execution\_id

type

amount\_recovered

evidence\_reference

observed\_at

```



\## Outcome Types



```text id="4q1n6v"

RECOVERED

FAILED

PENDING

EXPIRED

STOPPED

ESCALATED

```



\---



\# 19. AuditEvent



\## Purpose



Provides a chronological reconstruction of important system events.



\## Fields



```text id="d6k4v8"

audit\_event\_id

case\_id

event\_type

actor

timestamp

payload

correlation\_id

```



\## Actor



Initial vocabulary:



```text id="f7q2s1"

SYSTEM

MODEL

POLICY

EXECUTOR

HUMAN

RAZORPAY

SIMULATOR

```



\---



\# 20. Audit Event Examples



```text id="7j2r8q"

CASE\_CREATED

DIAGNOSIS\_CREATED

DECISION\_CREATED

POLICY\_ALLOWED

POLICY\_BLOCKED

EXECUTION\_STARTED

EXECUTION\_COMPLETED

EXECUTION\_FAILED

PAYMENT\_STATE\_CHANGED

OUTCOME\_RECORDED

CASE\_STOPPED

CASE\_ESCALATED

CASE\_RECOVERED

```



\---



\# 21. Payment → Event Relationship



One Payment can have many PaymentEvents.



```text id="4n9kq7"

Payment

&#x20;  │

&#x20;  ├── Event 1

&#x20;  ├── Event 2

&#x20;  ├── Event 3

&#x20;  └── Event N

```



Payment current state is maintained from observed events.



\---



\# 22. Payment → Recovery Case Relationship



A Payment may have one active Recovery Case.



```text id="f8d3x2"

Payment

&#x20;  │

&#x20;  └── RecoveryCase

```



A future version may support multiple historical recovery cases.



\---



\# 23. Recovery Case → Diagnosis Relationship



A Recovery Case can have multiple diagnosis records over time.



```text id="c8r4y2"

RecoveryCase

&#x20;  │

&#x20;  ├── Diagnosis v1

&#x20;  ├── Diagnosis v2

&#x20;  └── Diagnosis v3

```



This allows the system to update its understanding after failed recovery attempts.



\---



\# 24. Recovery Case → Decision Relationship



A Recovery Case can have multiple decisions over its lifetime.



Example:



```text id="5y8q2m"

Decision 1

RETRY

&#x20;  ↓

FAILED



Decision 2

PAYMENT\_LINK

&#x20;  ↓

RECOVERED

```



Historical decisions must remain immutable.



\---



\# 25. Recovery Case → Action Relationship



A Recovery Case may contain multiple candidate and executed actions.



```text id="9q6w4e"

RecoveryCase

&#x20;  │

&#x20;  ├── RETRY

&#x20;  ├── PAYMENT\_LINK

&#x20;  └── OUTREACH

```



The system must distinguish:



\* candidate actions,

\* recommended actions,

\* approved actions,

\* executed actions.



\---



\# 26. Decision → Policy Relationship



Every executable decision must have a corresponding PolicyDecision.



```text id="1v8c6z"

Decision

&#x20;  ↓

PolicyDecision

&#x20;  ↓

Execution

```



A blocked decision must not result in execution.



\---



\# 27. Action → Execution Relationship



An action may have one or more execution attempts if the system explicitly permits re-execution.



Execution attempts must be separately recorded.



This prevents overwriting historical execution attempts.



\---



\# 28. Execution → Outcome Relationship



Execution and Outcome are separate.



Example:



```text id="3r7m1p"

Execution:

SUCCEEDED



Outcome:

FAILED

```



This can happen if an external action was accepted but the payment did not ultimately recover.



Conversely:



```text id="m8q2x4"

Execution:

UNKNOWN



Outcome:

RECOVERED

```



may occur after later reconciliation.



\---



\# 29. Customer History



The intelligence layer may derive historical features from:



```text id="x4j9w6"

Payments

PaymentEvents

RecoveryCases

Outcomes

```



Examples:



```text

payment\_success\_rate

failure\_rate

recovery\_rate

average\_payment\_amount

previous\_recovery\_success

preferred\_payment\_method

```



Derived features must be calculated using information available before the decision being evaluated.



\---



\# 30. Temporal Integrity



The system must avoid future-information leakage.



For a decision made at time `T`, model features must not contain information that became available after `T`.



For example:



Invalid:



```text id="5k4p8s"

Decision time: 10:00



Feature:

payment eventually succeeded at 10:05

```



Valid:



```text id="1w8n4j"

Decision time: 10:00



Feature:

previous recovery success rate before 10:00

```



This is mandatory for trustworthy evaluation.



\---



\# 31. Database Tables



Initial relational tables:



```text id="7w2k8x"

customers

payments

payment\_events

recovery\_cases

diagnoses

action\_evaluations

decisions

policy\_decisions

executions

outcomes

audit\_events

```



The final schema may add supporting tables where required.



\---



\# 32. Primary Keys



Each domain entity receives an internal unique identifier.



External identifiers must be stored separately.



Example:



```text id="2q7w5m"

internal case\_id

external payment\_id

```



This avoids coupling internal database identity to provider identifiers.



\---



\# 33. External References



Provider references should be retained where relevant.



Examples:



```text id="7x2p9k"

razorpay\_payment\_id

razorpay\_order\_id

razorpay\_payment\_link\_id

razorpay\_event\_id

```



Provider-specific fields should remain isolated from the domain logic as much as possible.



\---



\# 34. Monetary Values



Monetary amounts must never be represented using floating-point values in financial calculations.



Amounts should use integer minor units.



Example:



```text id="7x1m4v"

₹699

=

69900 paise

```



The currency must always be stored alongside the amount.



Example:



```text id="4q8y2m"

amount\_minor = 69900

currency = INR

```



Expected recovery values should follow the same monetary representation.



\---



\# 35. Timestamps



All persisted timestamps should use timezone-aware UTC timestamps.



The system may convert timestamps to local time only at presentation boundaries.



\---



\# 36. Raw Payloads



Raw Razorpay webhook payloads should not be stored directly inside every domain entity.



Instead:



```text id="8p3k5v"

Raw Event

&#x20;  ↓

raw\_events / object storage reference

&#x20;  ↓

PaymentEvent

```



This keeps the domain schema clean.



\---



\# 37. Data Retention



The prototype should retain enough information to reproduce and audit decisions.



Synthetic/test data may be retained for the duration of development and evaluation.



No real customer personal data should be introduced into the benchmark.



\---



\# 38. Data Ownership



| Data                    | Authority                             |

| ----------------------- | ------------------------------------- |

| Payment event           | Razorpay / Simulator                  |

| Payment state           | APRO state engine derived from events |

| Diagnosis               | APRO model                            |

| Action probability      | APRO model                            |

| Expected recovery value | APRO decision engine                  |

| Policy result           | APRO policy engine                    |

| Execution result        | Executor                              |

| Recovery outcome        | Observed event/result                 |

| Audit record            | APRO                                  |



\---



\# 39. Example Complete Case



A complete case might look like:



```text id="5x9q2m"

Customer

customer\_001



Payment

pay\_test\_001

₹699

FAILED



Payment Events

├── payment.created

└── payment.failed



Recovery Case

case\_001

NEW

↓

DIAGNOSING

↓

EVALUATING



Diagnosis

TRANSIENT

confidence = 0.87



Action Evaluations

RETRY

probability = 0.72

ERV = ₹503



PAYMENT\_LINK

probability = 0.51

ERV = ₹357



OUTREACH

probability = 0.31

ERV = ₹217



Decision

RETRY



Policy

ALLOW



Execution

SIMULATION

SUCCEEDED



Outcome

RECOVERED



Amount Recovered

₹699



Case

RECOVERED

```



\---



\# 40. Race Condition Example



```text id="7v4k8n"

Payment

pay\_test\_002



Event 1

payment.failed



Recovery Case

EVALUATING



Decision

PAYMENT\_LINK



Before Execution

payment.captured



Policy Re-check

BLOCK



Reason

Payment already captured



Final Case

STOPPED



Stop Reason

PAYMENT\_ALREADY\_RECOVERED

```



No Payment Link should be created.



\---



\# 41. Duplicate Event Example



```text id="3k8m1q"

payment.failed

event\_id = evt\_123



Received again

event\_id = evt\_123

```



The second event must be recognized as duplicate.



Expected behavior:



```text id="5y7p2r"

No duplicate case

No duplicate decision

No duplicate execution

Audit:

DUPLICATE\_EVENT\_IGNORED

```



\---



\# 42. Failed Recovery Example



```text id="9q2x5m"

Decision 1

RETRY



Execution

SUCCEEDED



Outcome

FAILED



Recovery Case

EVALUATING



Decision 2

PAYMENT\_LINK



Policy

ALLOW



Execution

SUCCEEDED



Outcome

RECOVERED

```



This demonstrates adaptive recovery rather than blind repetition.



\---



\# 43. High-Value Escalation Example



```text id="4m8x2q"

Payment

₹50,000



Diagnosis

UNKNOWN

confidence = 0.41



Decision

PAYMENT\_LINK



Policy

REQUIRE\_HUMAN\_APPROVAL



Final

ESCALATED

```



No automated financial action occurs.



\---



\# 44. Stop Example



```text id="7q3n5m"

Payment

₹299



Previous Attempts

3



Policy

MAX\_RETRIES = 3



Recommendation

RETRY



Policy

BLOCK



Final

STOPPED



Reason

RETRY\_LIMIT\_REACHED

```



\---



\# 45. Schema Evolution



The database schema must be version-controlled through migrations.



Schema changes must not be performed manually in production/test environments.



Migration tooling will be selected during backend implementation.



\---



\# 46. Domain Invariants



The following invariants must always hold:



1\. A captured payment cannot receive a new recovery execution.

2\. A blocked action cannot execute.

3\. Every execution must reference an approved action.

4\. Every decision must reference the case context used to make it.

5\. Every model prediction must reference a model version.

6\. Every policy decision must reference a policy version.

7\. Monetary values must use integer minor units.

8\. Historical events and decisions must not be overwritten.

9\. Duplicate events must not create duplicate execution.

10\. Future outcomes must not leak into historical model features.



\---



\# 47. Domain/Data Design Success Criteria



The domain model is considered ready for implementation when:



\* every major product concept has a defined entity,

\* state transitions are explicit,

\* relationships are explicit,

\* source-of-truth boundaries are clear,

\* model outputs are separated from observed facts,

\* policy decisions are separated from AI recommendations,

\* executions are separated from outcomes,

\* auditability is possible,

\* benchmark data can be represented,

\* and race/duplicate cases can be represented correctly.



\---



\# 48. Status



\*\*Version:\*\* 1.0



\*\*Status:\*\* Ready for implementation.



Any future modification to a core entity, state machine or invariant must be documented before implementation.



