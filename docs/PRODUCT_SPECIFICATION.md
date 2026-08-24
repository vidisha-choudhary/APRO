\# APRO — Product Specification



\*\*Project:\*\* Adaptive Payment Recovery Orchestrator

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Status:\*\* Product behavior specification

\*\*Owner:\*\* Vidisha



\---



\# 1. Product Definition



APRO is an adaptive revenue-recovery agent that determines the safest, highest-value next action after a payment enters a recoverable failure state.



APRO does not treat every failed payment identically.



It evaluates the current payment state, failure characteristics, historical context, available recovery actions, expected recovery value, and policy constraints before deciding what should happen next.



The product loop is:



\*\*DETECT → DIAGNOSE → EVALUATE → DECIDE → GATE → ACT → OBSERVE → RECOVER / ADAPT / STOP / ESCALATE\*\*



\---



\# 2. Primary User



The primary user is a merchant/payment operations team responsible for recovering revenue from failed payment attempts.



APRO should reduce:



\* unnecessary manual investigation,

\* blind retries,

\* ineffective recovery attempts,

\* customer friction,

\* and revenue lost because the wrong recovery action was chosen.



\---



\# 3. Primary Input



APRO begins when it receives a payment-related event indicating that a payment may require recovery.



The primary initial trigger is:



`payment.failed`



The system must also process subsequent payment-state events that can change whether recovery is still appropriate.



Examples:



\* `payment.authorized`

\* `payment.captured`

\* other relevant payment/payment-link/order events



\---



\# 4. Canonical Payment Case



Every payment being evaluated for recovery becomes a \*\*Recovery Case\*\*.



A Recovery Case contains at minimum:



```text

case\_id

payment\_id

order\_id

amount

currency

payment\_method

current\_status

failure\_information

attempt\_count

created\_at

updated\_at

recovery\_status

```



Additional context may include:



```text

customer\_history

previous\_successes

previous\_failures

time\_since\_failure

previous\_recovery\_actions

previous\_recovery\_outcomes

```



\---



\# 5. Recovery Case Lifecycle



A Recovery Case follows a controlled lifecycle.



```text

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

&#x20;├───────────────┐

&#x20;↓               ↓

RECOVERED      FAILED

&#x20;                 │

&#x20;         ┌───────┴────────┐

&#x20;         ↓                ↓

&#x20;      RE-EVALUATE       STOP / ESCALATE

```



A case may also transition directly to:



```text

STOPPED

ESCALATED

```



when appropriate.



\---



\# 6. Step 1 — Detect



When a recoverable payment event arrives, APRO creates or updates the corresponding Recovery Case.



Before creating a new case, APRO must determine whether the event belongs to an existing case.



Duplicate events must not create duplicate recovery workflows.



\---



\# 7. Step 2 — Verify Current State



Before making a recovery decision, APRO must establish the current known payment state.



This is critical because payment state may change after the original failure.



Example:



```text

payment.failed

&#x20;     ↓

APRO begins evaluation

&#x20;     ↓

payment.captured

&#x20;     ↓

Recovery Case → STOPPED

```



If the payment is already successfully captured, APRO must not initiate a recovery action.



\---



\# 8. Step 3 — Diagnose



APRO determines the most likely failure category.



The initial diagnosis taxonomy should include:



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



The diagnosis system produces:



```text

failure\_category

confidence

evidence

```



Example:



```text

Category:

TRANSIENT



Confidence:

0.87



Evidence:

\- gateway-origin failure

\- low attempt count

\- previously successful customer

\- recent similar failures recovered after retry

```



The diagnosis must remain probabilistic when evidence is uncertain.



\---



\# 9. Step 4 — Generate Candidate Actions



APRO generates the set of actions that are potentially appropriate for the current case.



Initial conceptual action set:



```text

RETRY

ALTERNATE\_RECOVERY

OUTREACH

ESCALATE

STOP

```



Not every action will be available for every case.



Candidate generation must consider:



\* failure category,

\* current payment state,

\* amount,

\* attempt history,

\* customer context,

\* previous actions,

\* policy constraints,

\* available execution mechanisms.



\---



\# 10. Step 5 — Estimate Recovery Probability



For each eligible recovery action, APRO estimates:



> \*\*How likely is this action to successfully recover the payment?\*\*



Conceptually:



```text

P(success | payment context, action)

```



Example:



```text

RETRY

0.72



ALTERNATE\_RECOVERY

0.51



OUTREACH

0.31

```



The model used to generate these estimates will be selected based on measured performance.



APRO must not use an LLM merely because the project is an AI project.



\---



\# 11. Step 6 — Estimate Economic Value



For each candidate action, APRO estimates its expected recovery value.



Initial conceptual formulation:



```text

Expected Recovery Value

=

Probability of Successful Recovery

×

Recoverable Amount

−

Action Cost / Friction

```



Example:



```text

Amount: ₹699



RETRY

0.72 × ₹699 = ₹503.28



ALTERNATE\_RECOVERY

0.51 × ₹699 = ₹356.49



OUTREACH

0.31 × ₹699 = ₹216.69

```



The final economic model may include additional factors such as intervention cost, expected delay, or customer friction.



\---



\# 12. Step 7 — Make a Recommendation



APRO selects the candidate action with the highest expected value among eligible actions.



However, the optimization layer does not have authority to bypass safety or policy constraints.



The output of the decision engine must include:



```text

recommended\_action

expected\_value

confidence

reason

candidate\_actions

```



Example:



```text

Recommended Action:

RETRY



Expected Recovery Value:

₹503



Confidence:

0.87



Reason:

Retry has the highest expected recovery value among

currently eligible actions and the payment remains below

the retry limit.

```



\---



\# 13. Step 8 — Policy Gate



Every non-trivial action must pass through the policy gate.



The policy gate can:



```text

ALLOW

BLOCK

REQUIRE\_HUMAN\_APPROVAL

```



Example policies:



```text

IF payment already captured

→ BLOCK



IF retry\_count >= maximum

→ BLOCK RETRY



IF diagnosis confidence < minimum threshold

→ REQUIRE\_HUMAN\_APPROVAL



IF payment amount > high\_value\_threshold

→ REQUIRE\_HUMAN\_APPROVAL



IF action is unavailable in current environment

→ BLOCK



IF expected recovery value < minimum threshold

→ STOP

```



Policy decisions must be recorded.



\---



\# 14. Step 9 — Execute



If the action is approved, APRO sends it to the appropriate executor.



The executor is responsible only for performing the approved action.



It must not independently make financial decisions.



Conceptually:



```text

Decision Engine

&#x20;     ↓

Policy Gate

&#x20;     ↓

Executor

&#x20;     ↓

Razorpay Test Mode / Simulation

```



\---



\# 15. Payment Link Recovery



Payment Link recovery is one of the initial real Razorpay-integrated recovery paths.



Conceptual flow:



```text

Failed Payment

&#x20;     ↓

APRO recommends Payment Link

&#x20;     ↓

Policy approves

&#x20;     ↓

Payment Link Executor

&#x20;     ↓

Create Razorpay Payment Link

&#x20;     ↓

Customer/Test User completes payment

&#x20;     ↓

Payment Link / Payment event

&#x20;     ↓

APRO observes outcome

&#x20;     ↓

RECOVERED

```



Payment Link execution must remain within the limits and capabilities of Razorpay Test Mode.



\---



\# 16. Retry



Retry is a conceptual recovery action, not an assumed unrestricted Razorpay API.



APRO may recommend a retry when appropriate.



The actual execution mechanism must be validated against the current Razorpay Test Mode/API capabilities before implementation.



APRO must never assume the existence of a generic `retry\_payment()` API.



\---



\# 17. Outreach



Outreach represents a customer-facing recovery intervention.



The initial implementation may simulate message delivery and outcome.



A future implementation may connect it to a supported messaging channel.



An outreach action must contain:



```text

message

reason

channel

case\_id

```



The message should be contextual rather than generic whenever sufficient information is available.



\---



\# 18. Escalation



APRO escalates a Recovery Case when automation is not sufficiently reliable or permitted.



Examples:



\* low confidence,

\* high-value transaction,

\* conflicting signals,

\* policy exception,

\* repeated failed recovery,

\* unknown failure category.



An escalation record should contain:



```text

case\_id

reason

recommended\_action

evidence

confidence

previous\_actions

```



\---



\# 19. Stop



APRO may deliberately stop a recovery case.



Examples:



```text

payment already captured

retry limit reached

expected recovery value too low

no permissible recovery action

repeated unsuccessful interventions

customer should not receive additional intervention

```



A stopped case is not considered a system failure.



It is a valid decision.



\---



\# 20. Observe



After an action executes, APRO must wait for evidence of the outcome.



Possible outcomes include:



```text

RECOVERED

FAILED

PENDING

EXPIRED

ESCALATED

STOPPED

```



APRO must not assume that execution equals recovery.



Recovery must be confirmed through an appropriate payment state or test outcome.



\---



\# 21. Adaptation After Failure



If an approved recovery action fails, APRO must not automatically repeat the same action indefinitely.



The system must update the Recovery Case and re-evaluate the available actions.



Example:



```text

Attempt 1

RETRY

↓

FAILED

↓

Update evidence

↓

Recalculate action values

↓

PAYMENT\_LINK

↓

Policy check

↓

Execute

```



If no sufficiently valuable or permitted action remains:



\*\*STOP or ESCALATE\*\*



\---



\# 22. Race Condition Protection



APRO must handle cases where payment state changes while a recovery decision is being made.



Example:



```text

10:00:00

payment.failed



10:00:01

APRO evaluates recovery



10:00:02

payment.captured



10:00:03

APRO attempts execution

```



Before execution, APRO must re-check whether the action is still valid.



If the payment is already captured:



\*\*ACTION MUST NOT EXECUTE\*\*



The case becomes:



\*\*STOPPED — PAYMENT ALREADY RECOVERED\*\*



\---



\# 23. Duplicate Event Protection



The same webhook/event may arrive more than once.



APRO must ensure that duplicate events do not create:



\* duplicate recovery cases,

\* duplicate decisions,

\* duplicate Payment Links,

\* duplicate outreach,

\* or duplicate recovery execution.



Event processing must therefore be idempotent.



\---



\# 24. Audit Trail



Every major decision must create an immutable-style audit record.



At minimum:



```text

event\_id

case\_id

timestamp

payment\_state

diagnosis

diagnosis\_confidence

candidate\_actions

expected\_values

recommended\_action

policy\_result

execution\_result

outcome

```



Example:



```text

CASE: rc\_00182



Payment:

pay\_test\_123



Amount:

₹699



Diagnosis:

TRANSIENT



Confidence:

0.87



Candidates:

RETRY       ₹503

OUTREACH    ₹217

STOP          ₹0



Recommendation:

RETRY



Policy:

ALLOWED



Execution:

COMPLETED



Outcome:

RECOVERED



Revenue Recovered:

₹699

```



\---



\# 25. Recovery Case Outcome



Every case must eventually reach a meaningful terminal or waiting state.



Terminal outcomes:



```text

RECOVERED

STOPPED

ESCALATED

```



Temporary states:



```text

PENDING

EXECUTING

OBSERVING

```



A case must never disappear without an explainable state.



\---



\# 26. Batch Evaluation



APRO must support evaluation across a large batch of synthetic cases.



The evaluation engine must run:



```text

Baseline A

No Intervention



Baseline B

Always Retry



Baseline C

Static Rules



APRO

Adaptive Decisioning

```



The same underlying cases must be used for each strategy.



\---



\# 27. Primary Economic Metrics



The evaluation system must calculate:



\### Revenue at Risk



Total recoverable value initially exposed to the system.



\### Revenue Recovered



Total value successfully recovered.



\### Recovery Rate



```text

Recovered Revenue / Revenue at Risk

```



\### Incremental Recovery



```text

APRO Recovered Revenue

−

Baseline Recovered Revenue

```



\### Intervention Efficiency



```text

Recovered Revenue / Number of Interventions

```



\### Unnecessary Intervention Rate



Percentage of interventions that did not create meaningful recovery value.



\### Escalation Rate



Percentage of cases sent to human review.



\### Stop Rate



Percentage of cases deliberately terminated without further intervention.



\---



\# 28. Real Integration vs Simulation



APRO will explicitly separate:



\## Razorpay Test Mode



Used for:



\* webhook integration,

\* payment-state events,

\* Payment Link recovery,

\* integration validation,

\* live demonstration.



\## Simulation



Used for:



\* large-scale datasets,

\* thousands of cases,

\* controlled failure scenarios,

\* baseline comparison,

\* model evaluation.



Both environments must feed the same APRO decision engine.



\---



\# 29. Product Boundaries



APRO v1 will NOT attempt to solve:



\* fraud,

\* chargebacks,

\* B2B receivables,

\* checkout abandonment,

\* trial conversion,

\* merchant growth,

\* unrestricted financial automation.



The product remains focused on:



> \*\*Adaptive recovery of failed payment revenue.\*\*



\---



\# 30. Golden Path



The primary successful APRO flow is:



```text

Razorpay payment.failed

&#x20;       ↓

Create Recovery Case

&#x20;       ↓

Verify Current State

&#x20;       ↓

Diagnose Failure

&#x20;       ↓

Generate Candidate Actions

&#x20;       ↓

Estimate Recovery Probability

&#x20;       ↓

Estimate Expected Recovery Value

&#x20;       ↓

Select Best Permissible Action

&#x20;       ↓

Policy Gate

&#x20;       ↓

Execute

&#x20;       ↓

Observe Payment Outcome

&#x20;       ↓

RECOVERED

&#x20;       ↓

Record Revenue Recovered

```



\---



\# 31. Golden Failure Path



The primary failure demonstration is:



```text

payment.failed

&#x20;       ↓

APRO recommends recovery

&#x20;       ↓

recovery attempt fails

&#x20;       ↓

APRO updates evidence

&#x20;       ↓

re-evaluates actions

&#x20;       ↓

no safe/high-value action remains

&#x20;       ↓

STOP or ESCALATE

```



\---



\# 32. Golden Race-Condition Path



The primary state-consistency demonstration is:



```text

payment.failed

&#x20;       ↓

APRO begins recovery decision

&#x20;       ↓

payment.captured

&#x20;       ↓

APRO re-checks state

&#x20;       ↓

pending action cancelled

&#x20;       ↓

STOPPED

Reason:

Payment already recovered

```



\---



\# 33. Product Success



APRO's product behavior is considered successful when it can demonstrate:



1\. Correct diagnosis of payment failure scenarios.

2\. Meaningful action selection.

3\. Economic reasoning behind decisions.

4\. Policy-constrained execution.

5\. Safe handling of changing payment states.

6\. Measurable recovery.

7\. Better performance than simpler baselines.

8\. Complete auditability.

9\. Correct stopping and escalation behavior.



\---



\# 34. Product North Star



The product should always optimize for:



> \*\*The right recovery action, for the right payment, at the right time, for the right economic reason — or no action when recovery is not justified.\*\*



\---



\# 35. Relationship to Other Project Documents



`PROJECT\_CONSTITUTION.md`



Defines the principles APRO must follow.



`PROBLEM\_DEFINITION.md`



Defines the problem APRO solves.



`COMPETITIVE\_ANALYSIS.md`



Defines the competitive landscape and intended differentiation.



`RAZORPAY\_CAPABILITY\_MAP.md`



Defines the external capabilities and constraints available to APRO.



`PRODUCT\_SPECIFICATION.md`



Defines the exact intended behavior of APRO.



The Product Specification must remain consistent with the Constitution and Problem Definition.



