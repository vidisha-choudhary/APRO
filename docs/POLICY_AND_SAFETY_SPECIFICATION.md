\# APRO — Policy \& Safety Specification



\*\*Project:\*\* Adaptive Payment Recovery Orchestrator

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Owner:\*\* Vidisha

\*\*Architecture Leads:\*\* Vidisha + GPT

\*\*Implementation Lead:\*\* Antigravity

\*\*Status:\*\* Policy \& Safety Specification

\*\*Version:\*\* 1.0



\---



\# 1. Purpose



This document defines the deterministic safety and governance layer of APRO.



Its purpose is to ensure that:



\* AI recommendations remain bounded,

\* financial actions are explicitly authorized,

\* recovery attempts have stopping conditions,

\* high-risk situations are escalated,

\* payment state changes are respected,

\* duplicate events cannot cause duplicate actions,

\* and model or infrastructure failures fail safely.



The Policy Engine is deterministic.



It does not learn.



It does not improvise.



It does not override the Constitution.



\---



\# 2. Authority Model



APRO follows this authority hierarchy:



```text

Project Constitution

&#x20;       ↓

Policy Specification

&#x20;       ↓

Policy Engine

&#x20;       ↓

Approved Action

&#x20;       ↓

Executor

```



The AI sits below policy:



```text

AI / ML

&#x20;  ↓

Recommendation

&#x20;  ↓

Policy Engine

```



The AI cannot modify policy.



\---



\# 3. Core Safety Principle



> \*\*Prediction does not equal permission.\*\*



A model may determine:



> "RETRY has the highest expected recovery value."



The Policy Engine independently determines:



> "Is RETRY permitted?"



Only if both conditions are satisfied may execution occur.



\---



\# 4. Policy Outcomes



Every policy evaluation produces exactly one of:



```text

ALLOW

BLOCK

REQUIRE\_HUMAN\_APPROVAL

```



There must never be an implicit policy result.



\---



\# 5. Policy Evaluation Order



Policy checks must occur in the following conceptual order:



```text

1\. Is the event trusted?

2\. Is the payment state current?

3\. Is the payment still recoverable?

4\. Is the action supported?

5\. Is the action within attempt limits?

6\. Is the transaction within automation limits?

7\. Is model confidence sufficient?

8\. Is expected recovery value sufficient?

9\. Are there repeated-intervention constraints?

10\. Does any human-approval rule apply?

11\. ALLOW / BLOCK / HUMAN APPROVAL

```



A hard safety block takes precedence over economic value.



\---



\# 6. Hard Safety Rules



The following conditions must always block automated recovery.



\## Rule H1 — Already Captured



```text

IF payment.status == CAPTURED

→ BLOCK

```



Reason:



```text

PAYMENT\_ALREADY\_RECOVERED

```



No recovery action may execute.



\---



\## Rule H2 — Invalid Event



```text

IF webhook signature invalid

→ REJECT EVENT

```



The event must not enter the recovery pipeline.



\---



\## Rule H3 — Duplicate Event



```text

IF event\_id already processed

→ IGNORE DUPLICATE

```



No new recovery action may be created.



\---



\## Rule H4 — Unsupported Action



```text

IF action has no valid executor

→ BLOCK

```



APRO must never simulate that a real action occurred when no executor exists.



\---



\## Rule H5 — Invalid Model Output



If model output contains:



\* NaN,

\* infinity,

\* probability < 0,

\* probability > 1,

\* unknown action,

\* missing required fields,



then:



```text

→ REJECT MODEL OUTPUT

```



No financial action may execute from invalid output.



\---



\# 7. Retry Policy



Retry is bounded.



The system must maintain:



```text

retry\_count

```



and compare it against:



```text

MAX\_RETRIES

```



Conceptual rule:



```text

IF retry\_count >= MAX\_RETRIES

→ BLOCK RETRY

```



The initial value must be configurable.



It must not be hardcoded throughout the codebase.



\---



\# 8. Retry Spacing



APRO must not execute repeated retries without respecting the configured retry timing policy.



Conceptually:



```text

IF current\_time < next\_retry\_allowed\_at

→ BLOCK / DEFER

```



This prevents immediate retry loops.



The actual timing policy will be selected using measured simulation results and Razorpay-supported capabilities.



\---



\# 9. Repeated Intervention Protection



APRO must prevent endless intervention cycles.



Maintain:



```text

total\_interventions

```



and:



```text

MAX\_TOTAL\_INTERVENTIONS

```



Conceptually:



```text

IF total\_interventions >= MAX\_TOTAL\_INTERVENTIONS

→ STOP or ESCALATE

```



\---



\# 10. Same-Action Repetition



The same recovery action must not be repeated indefinitely.



Example:



```text

RETRY

&#x20;↓

FAILED

&#x20;↓

RETRY

&#x20;↓

FAILED

&#x20;↓

RETRY

```



is prohibited beyond the configured action-specific limit.



The system must either:



\* choose another eligible action,

\* stop,

\* or escalate.



\---



\# 11. High-Value Transactions



High-value transactions require additional protection.



Define:



```text

HIGH\_VALUE\_THRESHOLD

```



If:



```text

payment.amount >= HIGH\_VALUE\_THRESHOLD

```



then automated execution may require:



```text

REQUIRE\_HUMAN\_APPROVAL

```



The exact threshold is configurable and will be determined during evaluation.



The system must not invent a threshold merely for demonstration.



\---



\# 12. Low-Confidence Decisions



If diagnosis or recovery prediction confidence falls below the configured threshold:



```text

MIN\_CONFIDENCE

```



then automated execution must not proceed.



Possible policy result:



```text

REQUIRE\_HUMAN\_APPROVAL

```



or:



```text

STOP

```



depending on the case.



\---



\# 13. Minimum Expected Value



Define:



```text

MIN\_EXPECTED\_RECOVERY\_VALUE

```



If:



```text

ERV(action) < MIN\_EXPECTED\_RECOVERY\_VALUE

```



then:



```text

STOP

```



This prevents interventions whose expected economic benefit is too small.



\---



\# 14. Negative Expected Value



If:



```text

ERV(action) <= 0

```



then the action must not execute automatically.



Policy:



```text

BLOCK

```



or:



```text

STOP

```



depending on context.



\---



\# 15. STOP as a First-Class Decision



STOP is a valid policy outcome.



It is not a system failure.



STOP may occur when:



\* expected value is insufficient,

\* recovery attempts are exhausted,

\* payment is already captured,

\* no supported action remains,

\* confidence is insufficient,

\* intervention limits are reached.



\---



\# 16. ESCALATE as a First-Class Decision



ESCALATE is used when the system should not make the final decision autonomously.



Examples:



\* high-value payment,

\* low model confidence,

\* conflicting evidence,

\* unknown failure type,

\* repeated recovery failure,

\* unsupported edge case,

\* policy exception.



\---



\# 17. Human Approval



If a case requires human approval:



```text

Policy

→ REQUIRE\_HUMAN\_APPROVAL

```



then:



```text

Recovery Case

→ ESCALATED

```



No external financial action executes until approval is explicitly recorded.



\---



\# 18. Human Approval Integrity



A human approval must reference:



```text

case\_id

decision\_id

approved\_action

approver\_reference

timestamp

policy\_version

```



An approval for one action must not automatically authorize another action.



Example:



```text

Human approves:

PAYMENT\_LINK



System cannot interpret this as:

RETRY

```



\---



\# 19. Race Condition Protection



The Policy Engine must re-check current payment state immediately before execution.



Example:



```text

10:00

payment.failed



10:01

AI recommends PAYMENT\_LINK



10:02

payment.captured



10:03

execution attempted

```



Policy result:



```text

BLOCK

```



Reason:



```text

PAYMENT\_ALREADY\_RECOVERED

```



No Payment Link should be created.



\---



\# 20. State Reconciliation



If current payment state is uncertain:



```text

UNKNOWN

```



the system must not assume:



```text

FAILED

```



or:



```text

CAPTURED

```



Instead:



```text

RECONCILE

```



or:



```text

ESCALATE

```



depending on the available recovery mechanism.



\---



\# 21. API Timeout Policy



If an external API call times out:



```text

EXECUTION = UNKNOWN

```



It must not automatically become:



```text

EXECUTION = FAILED

```



The system must determine whether the action may actually have succeeded.



For example:



```text

Payment Link creation request

&#x20;       ↓

HTTP timeout

&#x20;       ↓

UNKNOWN

&#x20;       ↓

reconcile provider state

```



This prevents duplicate external actions.



\---



\# 22. External Action Idempotency



Every externally meaningful action must have an internal idempotency key.



Conceptually:



```text

case\_id + action\_id + execution\_attempt

```



or another deterministic unique identifier.



Repeated processing must not create duplicate external actions.



\---



\# 23. Payment Link Protection



Because Test Mode has documented Payment Link limits, APRO must track:



```text

payment\_link\_creation\_count

```



and prevent the simulator or integration demo from exceeding configured limits.



The system must fail safely when the configured capacity is reached.



\---



\# 24. Payment Link Duplication Rule



For the same approved Payment Link recovery action:



```text

IF existing valid Payment Link already exists

→ reuse existing reference

```



rather than blindly creating another link.



\---



\# 25. Captured-Payment Rule



This is one of APRO's highest-priority invariants.



Before creating or executing any recovery action:



```text

CHECK PAYMENT STATE

```



If:



```text

CAPTURED

```



then:



```text

STOP

```



This rule overrides:



\* model confidence,

\* expected recovery value,

\* customer history,

\* action ranking.



\---



\# 26. Webhook Ordering



Webhook events may arrive out of order.



APRO must not assume that event arrival order equals event occurrence order.



Where timestamps and state information permit, the state engine must reconcile events appropriately.



\---



\# 27. Stale Event Handling



An event that is older than the current known state must not blindly overwrite newer state.



Example:



```text

10:02 payment.captured

10:05 payment.failed

```



If the second event is stale or inconsistent with the current payment state, it must be handled according to reconciliation rules rather than blindly changing:



```text

CAPTURED → FAILED

```



\---



\# 28. Duplicate Recovery Case Protection



Before opening a new Recovery Case:



```text

CHECK:

Is there already an active case for this payment?

```



If yes:



```text

UPDATE EXISTING CASE

```



rather than opening another active case.



\---



\# 29. Model Failure Fallback



If the diagnosis model fails:



```text

MODEL ERROR

```



APRO must not invent a diagnosis.



Fallback options:



```text

DETERMINISTIC BASELINE

STOP

ESCALATE

```



The selected fallback will be finalized through evaluation.



\---



\# 30. Recovery Model Failure



If the recovery probability model fails:



```text

MODEL ERROR

```



APRO must not execute based on missing probabilities.



Fallback options:



```text

STATIC BASELINE

STOP

ESCALATE

```



The fallback must still pass through the Policy Engine.



\---



\# 31. Invalid Configuration



If critical policy configuration is missing or invalid:



```text

MAX\_RETRIES missing

HIGH\_VALUE\_THRESHOLD invalid

MIN\_CONFIDENCE invalid

```



the system must fail closed.



It must not silently use arbitrary defaults.



\---



\# 32. Environment Separation



APRO must explicitly distinguish:



```text

SIMULATION

TEST\_MODE

```



No real-money environment is permitted in v1.



The environment must be visible in logs and execution records.



\---



\# 33. Test Mode Only



APRO v1 must not use live Razorpay credentials.



Only Test Mode credentials may be configured.



The system should make it difficult to accidentally run against a live environment.



\---



\# 34. Secrets



The following must never be committed:



```text

RAZORPAY\_KEY\_SECRET

RAZORPAY\_WEBHOOK\_SECRET

DATABASE\_PASSWORD

API\_KEYS

```



Secrets must come from environment configuration.



\---



\# 35. Audit Requirement



Every policy decision must produce an audit record containing:



```text

case\_id

decision\_id

recommended\_action

policy\_result

policy\_reason

policy\_version

timestamp

```



\---



\# 36. Policy Reason Codes



Policy results should use structured reason codes.



Examples:



```text

PAYMENT\_ALREADY\_RECOVERED

INVALID\_EVENT

DUPLICATE\_EVENT

RETRY\_LIMIT\_REACHED

INTERVENTION\_LIMIT\_REACHED

LOW\_CONFIDENCE

NEGATIVE\_EXPECTED\_VALUE

LOW\_EXPECTED\_VALUE

HIGH\_VALUE\_APPROVAL\_REQUIRED

UNSUPPORTED\_ACTION

INVALID\_MODEL\_OUTPUT

UNKNOWN\_PAYMENT\_STATE

EXTERNAL\_STATE\_UNCERTAIN

```



Human-readable explanations may accompany these codes.



\---



\# 37. Policy Precedence



When multiple rules apply, hard safety rules take precedence.



Priority:



```text

1\. Invalid / untrusted event

2\. Payment already recovered

3\. Unknown / inconsistent state

4\. Unsupported action

5\. Execution/idempotency protection

6\. Intervention limits

7\. Human-approval requirements

8\. Confidence requirements

9\. Economic thresholds

10\. ALLOW

```



The exact implementation may encode this as an ordered rule engine.



\---



\# 38. Example Decision



Input:



```text

Payment:

₹699



Diagnosis:

TRANSIENT

confidence = 0.87



Recommendation:

RETRY



ERV:

₹503



Retry Count:

1



Maximum:

3

```



Policy:



```text

Payment captured?

NO



Retry limit reached?

NO



High value?

NO



Confidence sufficient?

YES



ERV sufficient?

YES

```



Result:



```text

ALLOW

```



\---



\# 39. Example Block



Input:



```text

Payment:

₹699



Recommendation:

RETRY



Retry Count:

3



Maximum:

3

```



Policy:



```text

RETRY\_LIMIT\_REACHED

```



Result:



```text

BLOCK

```



Final case:



```text

STOPPED

```



\---



\# 40. Example Human Approval



Input:



```text

Payment:

₹50,000



Recommendation:

PAYMENT\_LINK



Confidence:

0.91

```



Even though confidence is high:



```text

amount >= HIGH\_VALUE\_THRESHOLD

```



Policy:



```text

REQUIRE\_HUMAN\_APPROVAL

```



\---



\# 41. Example Race Condition



```text

payment.failed

&#x20;       ↓

Decision:

PAYMENT\_LINK

&#x20;       ↓

payment.captured

&#x20;       ↓

Policy Re-check

&#x20;       ↓

BLOCK

```



No external action occurs.



\---



\# 42. Example API Timeout



```text

Payment Link creation

&#x20;       ↓

API timeout

&#x20;       ↓

Execution = UNKNOWN

&#x20;       ↓

No duplicate creation

&#x20;       ↓

Reconciliation

```



\---



\# 43. Example Model Failure



```text

Recovery Model

&#x20;     ↓

ERROR

&#x20;     ↓

Fallback Strategy

&#x20;     ↓

Policy Gate

&#x20;     ↓

SAFE ACTION / STOP / ESCALATE

```



The system must never skip the Policy Gate because the model failed.



\---



\# 44. Simulation Safety



The simulator must obey the same policy rules as Test Mode.



The simulator must not allow scenarios to bypass policy simply because they are synthetic.



This ensures benchmark behavior reflects actual APRO behavior.



\---



\# 45. Policy Configuration



Initial policy parameters should be configurable:



```text

MAX\_RETRIES

MAX\_TOTAL\_INTERVENTIONS

HIGH\_VALUE\_THRESHOLD

MIN\_CONFIDENCE

MIN\_EXPECTED\_RECOVERY\_VALUE

RETRY\_COOLDOWN

MAX\_CASE\_DURATION

```



The values will be selected using evaluation rather than arbitrary assumptions.



\---



\# 46. Configuration Versioning



Policy configuration must have a version.



Example:



```text

policy-v1

```



Every policy decision must record the version used.



\---



\# 47. Policy Testing



Every policy rule must have explicit tests.



Examples:



```text

captured payment → blocked

duplicate event → ignored

retry limit → blocked

high-value → human approval

low confidence → human approval/stop

negative ERV → blocked

unsupported action → blocked

valid action → allowed

```



\---



\# 48. Adversarial Testing



The system must deliberately test:



\* duplicate webhooks,

\* stale events,

\* out-of-order events,

\* payment captured during decisioning,

\* model returning invalid probabilities,

\* API timeouts,

\* duplicate execution requests,

\* retry-limit bypass attempts,

\* missing configuration,

\* malformed events,

\* unknown failure categories.



\---



\# 49. Safety vs Optimization



APRO must always prefer:



> \*\*A safe missed opportunity\*\*



over:



> \*\*An unsafe automated financial action.\*\*



Therefore:



```text

Safety Constraint

>

Economic Optimization

```



when the two conflict.



\---



\# 50. Policy Engine Non-Responsibilities



The Policy Engine does not:



\* diagnose failures,

\* predict recovery,

\* rank actions economically,

\* execute actions,

\* determine actual payment outcomes.



It only determines:



> \*\*Whether the proposed action is permitted.\*\*



\---



\# 51. Executor Non-Responsibilities



Executors do not:



\* choose actions,

\* modify policy,

\* override approval,

\* invent missing payment states.



Executors perform approved actions.



\---



\# 52. Final Safety Architecture



```text

&#x20;                   OBSERVED EVENT

&#x20;                         │

&#x20;                         ▼

&#x20;                 STATE VALIDATION

&#x20;                         │

&#x20;                         ▼

&#x20;                 AI RECOMMENDATION

&#x20;                         │

&#x20;                         ▼

&#x20;                 ECONOMIC EVALUATION

&#x20;                         │

&#x20;                         ▼

&#x20;                  POLICY ENGINE

&#x20;                         │

&#x20;            ┌────────────┼────────────┐

&#x20;            │            │            │

&#x20;            ▼            ▼            ▼

&#x20;          ALLOW        BLOCK       HUMAN

&#x20;            │            │        APPROVAL

&#x20;            ▼            ▼            │

&#x20;         EXECUTE        STOP ◄───────┘

&#x20;            │

&#x20;            ▼

&#x20;          OUTCOME

&#x20;            │

&#x20;            ▼

&#x20;      AUDIT + METRICS

```



\---



\# 53. Safety Invariants



The following invariants are mandatory:



\### S1



A captured payment cannot receive a new recovery action.



\### S2



An unverified event cannot affect recovery state.



\### S3



A duplicate event cannot trigger duplicate execution.



\### S4



A blocked action cannot execute.



\### S5



A model cannot bypass policy.



\### S6



An executor cannot select its own action.



\### S7



An API timeout cannot automatically be interpreted as failure.



\### S8



An unknown payment state cannot trigger an unsafe action.



\### S9



Recovery attempts are bounded.



\### S10



Every automated financial action is auditable.



\### S11



Only Test Mode is permitted in v1.



\### S12



Synthetic outcomes cannot be represented as real merchant revenue.



\---



\# 54. Safety Success Criteria



The policy/safety layer is successful when:



1\. Every executable action passes deterministic policy.

2\. Every hard safety rule is enforced.

3\. Race conditions are handled safely.

4\. Duplicate events are idempotent.

5\. Model failures fail safely.

6\. External uncertainty does not create duplicate actions.

7\. Recovery attempts are bounded.

8\. High-value cases can be escalated.

9\. All policy decisions are auditable.

10\. No live-money execution is possible in v1.



\---



\# 55. Final Principle



APRO is intentionally not:



> \*\*AI decides and executes.\*\*



It is:



> \*\*AI predicts → economics evaluates → policy authorizes → executor acts → outcome proves.\*\*



The Policy Engine is the authority boundary between intelligence and financial action.



\---



\# 56. Status



\*\*Version:\*\* 1.0



\*\*Status:\*\* Ready for Simulation \& Evaluation Design.



Any modification to a safety invariant, policy precedence rule, execution authority or financial-action boundary must be documented before implementation.



