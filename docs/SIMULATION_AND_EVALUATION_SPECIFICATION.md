\# APRO — Simulation \& Evaluation Specification



\*\*Project:\*\* Adaptive Payment Recovery Orchestrator

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Owner:\*\* Vidisha

\*\*Architecture Leads:\*\* Vidisha + GPT

\*\*Implementation Lead:\*\* Antigravity

\*\*Status:\*\* Simulation \& Evaluation Specification

\*\*Version:\*\* 1.0



\---



\# 1. Purpose



This document defines how APRO will generate synthetic recovery scenarios, evaluate AI predictions, compare recovery strategies, measure recovered revenue, and demonstrate system safety.



The evaluation system must provide credible evidence that APRO creates measurable recovery value without relying on cherry-picked examples.



\---



\# 2. Evaluation Philosophy



APRO will be evaluated at four levels:



```text

Level 1 — Model Quality

&#x20;       ↓

Level 2 — Decision Quality

&#x20;       ↓

Level 3 — Economic Value

&#x20;       ↓

Level 4 — Safety / Reliability

```



A model can perform well at Level 1 and still fail at Level 3.



Therefore APRO must pass all relevant levels.



\---



\# 3. Primary Evaluation Question



The primary question is:



> \*\*Does APRO recover more legitimate revenue than reasonable alternative strategies while remaining within defined safety and intervention constraints?\*\*



This is more important than raw model accuracy.



\---



\# 4. Evaluation Unit



The primary unit of evaluation is a:



\*\*Recovery Case\*\*



Each case represents a payment opportunity where recovery may or may not be possible.



A benchmark consists of many independent Recovery Cases.



\---



\# 5. Batch Requirement



Evaluation must be performed on a sufficiently large batch.



The minimum initial benchmark target is:



```text

1,000 Recovery Cases

```



The system should support substantially larger batches.



Recommended stress benchmark:



```text

10,000+ Recovery Cases

```



The exact final benchmark size will depend on runtime.



\---



\# 6. Scenario Structure



Each synthetic scenario contains:



```text

scenario\_id

generation\_seed

scenario\_version

customer\_context

payment\_context

failure\_context

hidden\_state

observable\_state

candidate\_actions

action\_outcomes

```



The hidden state must remain unavailable to APRO.



\---



\# 7. Observable vs Hidden State



Each scenario is divided into:



\## Observable State



Information APRO is legitimately allowed to use.



Examples:



```text

payment amount

payment method

failure reason

failure code

attempt count

historical payment behavior

historical recovery behavior

time information

```



\## Hidden State



Information used only by the simulation outcome engine.



Examples:



```text

true failure mechanism

latent customer intent

latent bank condition

latent recoverability

true action effectiveness

```



The hidden state must never leak into model features.



\---



\# 8. Scenario Generation



Scenario generation must be independent of APRO's decision.



Architecture:



```text

Scenario Generator

&#x20;     ↓

Hidden Scenario State

&#x20;     ↓

Observable Projection

&#x20;     ↓

APRO

&#x20;     ↓

Action

&#x20;     ↓

Independent Outcome Engine

```



APRO must not influence scenario creation.



\---



\# 9. Scenario Families



The benchmark must contain multiple scenario families.



Initial families:



```text

TRANSIENT\_FAILURE

BANK\_SIDE\_FAILURE

CUSTOMER\_SIDE\_FAILURE

AUTHENTICATION\_FAILURE

PAYMENT\_METHOD\_FAILURE

GATEWAY\_FAILURE

TIMEOUT

UNKNOWN\_FAILURE

```



\---



\# 10. Recoverability Classes



Each scenario may belong to one of:



```text

HIGHLY\_RECOVERABLE

MODERATELY\_RECOVERABLE

LOW\_RECOVERABILITY

NON\_RECOVERABLE

```



Recoverability is hidden from APRO.



It may influence simulated action outcomes.



\---



\# 11. Customer Behavior Classes



The simulator may generate different customer behavior patterns.



Examples:



```text

HIGHLY\_RESPONSIVE

NORMAL

LOW\_RESPONSIVENESS

UNPREDICTABLE

```



These attributes must be represented only through observable proxies available at decision time.



\---



\# 12. Payment Amount Distribution



Payment amounts should not all be identical.



The benchmark should contain:



\* low-value payments,

\* medium-value payments,

\* high-value payments.



The distribution should resemble a plausible merchant payment distribution rather than being arbitrarily uniform.



The exact distribution must be documented in the simulator configuration.



\---



\# 13. Payment Method Distribution



The simulator should support multiple payment methods where appropriate.



Examples:



```text

CARD

UPI

NETBANKING

WALLET

OTHER\_SUPPORTED\_METHOD

```



Only methods supported by the implemented APRO integration/simulation should be included.



\---



\# 14. Temporal Distribution



Scenarios should vary across:



```text

hour

day

weekday/weekend

time since previous attempt

time since previous successful payment

```



This enables evaluation of temporal patterns.



\---



\# 15. Historical Context



Customers may have prior payment history.



Examples:



```text

previous\_payment\_count

previous\_success\_count

previous\_failure\_count

previous\_recovery\_count

previous\_retry\_success

previous\_payment\_link\_success

```



Only historical information available before the current decision may be used.



\---



\# 16. Scenario Difficulty



The benchmark should contain:



\### Easy Cases



Strong signals.



\### Ambiguous Cases



Conflicting signals.



\### Hard Cases



Limited evidence and multiple plausible actions.



\### Adversarial Cases



Cases specifically designed to test safety and robustness.



The benchmark must not consist only of easy cases.



\---



\# 17. Action Set



Initial candidate actions:



```text

RETRY

PAYMENT\_LINK

OUTREACH

STOP

ESCALATE

```



Actual availability depends on the implemented executor.



\---



\# 18. Independent Outcome Engine



The outcome engine determines what happens after an action.



Architecture:



```text

Hidden Scenario State

\+

Chosen Action

\+

Controlled Randomness

&#x20;       ↓

Outcome Engine

&#x20;       ↓

SUCCESS / FAILURE / PENDING

```



The outcome engine must not inspect:



```text

APRO's predicted probability

APRO's expected recovery value

APRO's internal decision score

```



This prevents circular evaluation.



\---



\# 19. Outcome Independence Rule



The outcome engine must answer:



> "Given the underlying scenario and the chosen action, what happens?"



It must not answer:



> "APRO chose this action, therefore make it succeed."



This rule is mandatory.



\---



\# 20. Ground Truth



For every case and candidate action, the simulator may maintain hidden potential outcomes.



Conceptually:



```text

Scenario 001



RETRY

→ SUCCESS



PAYMENT\_LINK

→ SUCCESS



OUTREACH

→ FAILURE

```



APRO sees only the context.



It sees the actual outcome only after choosing/executing an action.



\---



\# 21. Counterfactual Evaluation



Hidden potential outcomes allow controlled counterfactual analysis.



Example:



```text

Actual:

APRO chose RETRY

→ SUCCESS



Hidden:

PAYMENT\_LINK

→ SUCCESS

OUTREACH

→ FAILURE

```



The hidden alternatives may be used for benchmark analysis.



They must not be exposed to APRO during decision-making.



\---



\# 22. Simulator Randomness



Scenario generation and outcome generation must support deterministic seeds.



Example:



```text

seed = 42

```



A benchmark can therefore be reproduced.



\---



\# 23. Multiple Seeds



A single random seed must not be considered sufficient evidence.



Final evaluation should use multiple seeds.



Example:



```text

42

101

2026

31415

```



The exact final seed set will be configured during implementation.



Results should be reported both:



\* per seed,

\* and aggregated.



\---



\# 24. Benchmark Dataset Versioning



Every benchmark must have:



```text

dataset\_version

scenario\_version

configuration\_version

seed

```



Example:



```text

benchmark-v1

scenario-v1

config-v1

seed-42

```



\---



\# 25. Training / Evaluation Separation



Synthetic data used for model training must not simply be reused as the final test set.



At minimum:



```text

TRAINING DATA

&#x20;     ↓

VALIDATION DATA

&#x20;     ↓

HELD-OUT TEST DATA

```



The held-out benchmark must remain untouched during model tuning.



\---



\# 26. Scenario Distribution Shift



The final benchmark should contain at least one evaluation distribution that differs somewhat from the training distribution.



Examples:



\* different failure mix,

\* different payment amount distribution,

\* changed customer behavior,

\* altered action effectiveness,

\* increased ambiguity.



This tests whether APRO learned useful patterns rather than memorized the simulator.



\---



\# 27. Baseline Strategies



APRO must be compared against reasonable alternatives.



Minimum baselines:



\## Baseline 0 — No Intervention



```text

Always STOP

```



This establishes the natural recovered-revenue floor.



\---



\## Baseline 1 — Always Retry



```text

IF recovery candidate

→ RETRY

```



subject to the same safety constraints.



\---



\## Baseline 2 — Static Failure Rules



Example:



```text

IF failure\_category == TRANSIENT

→ RETRY



IF authentication failure

→ OUTREACH



OTHERWISE

→ STOP

```



The actual rules must be documented and fixed before the final benchmark.



\---



\## Baseline 3 — Global Action Rate



Choose the action with the historically highest overall recovery rate.



This baseline ignores individual case context.



\---



\## APRO



Uses:



```text

Diagnosis

\+

Action-conditioned recovery prediction

\+

Expected recovery value

\+

Policy

```



\---



\# 28. Baseline Fairness



Every strategy must operate under equivalent constraints.



The baselines must not receive:



\* hidden scenario state,

\* future outcomes,

\* privileged information,

\* different recovery opportunities.



The same safety constraints should apply unless the baseline is intentionally defined as an unconstrained theoretical comparator.



\---



\# 29. Primary Economic Metrics



The most important metrics are:



```text

Revenue at Risk

Revenue Recovered

Incremental Revenue Recovered

Recovery Rate

Recovered Revenue / Intervention

```



\---



\# 30. Revenue at Risk



For benchmark purposes:



```text

Revenue at Risk

=

sum of payment amounts eligible for recovery

```



The exact eligibility definition must remain fixed for the benchmark.



\---



\# 31. Revenue Recovered



For each case:



```text

Recovered Amount

=

payment amount

```



when the payment successfully recovers.



Otherwise:



```text

Recovered Amount

=

0

```



Partial recovery must only be represented if the underlying payment workflow supports it.



\---



\# 32. Recovery Rate



Conceptually:



```text

Recovery Rate

=

Recovered Cases

/

Eligible Cases

```



The denominator must be explicitly defined.



\---



\# 33. Incremental Recovery



Compare APRO against a baseline.



Example:



```text

Incremental Recovery

=

APRO Recovered Revenue

−

Baseline Recovered Revenue

```



This is a primary evidence metric.



\---



\# 34. Intervention Efficiency



Measure:



```text

Recovered Revenue

/

Number of Interventions

```



This captures whether APRO is recovering money efficiently rather than simply intervening more frequently.



\---



\# 35. Intervention Rate



Measure:



```text

Intervention Rate

=

Intervention Cases

/

Eligible Cases

```



APRO should not be rewarded simply for acting on everything.



\---



\# 36. Unnecessary Intervention Rate



Define an unnecessary intervention according to the benchmark's ground truth.



Examples may include:



\* action executed where STOP would have produced the same outcome,

\* intervention on a non-recoverable case,

\* repeated action after recovery was already achieved.



The definition must be fixed before final evaluation.



\---



\# 37. Stop Rate



Measure:



```text

Stop Rate

=

Stopped Cases

/

Eligible Cases

```



A high stop rate is not automatically bad.



It must be interpreted alongside recovery and intervention efficiency.



\---



\# 38. Escalation Rate



Measure:



```text

Escalation Rate

=

Escalated Cases

/

Eligible Cases

```



The purpose is to determine whether APRO is appropriately conservative.



\---



\# 39. Safety Metrics



Mandatory safety metrics:



```text

Policy Violation Count

Duplicate Execution Count

Captured-Payment Intervention Count

Retry-Limit Violation Count

Invalid-Model-Execution Count

Unknown-State Unsafe Execution Count

```



For a successful final build:



```text

All hard safety violation counts = 0

```



\---



\# 40. Reliability Metrics



Measure:



```text

Webhook Processing Success

Event Deduplication Rate

Decision Success Rate

Execution Success Rate

Unknown Execution Rate

API Error Rate

Average Decision Latency

```



\---



\# 41. Model Metrics



\## Diagnosis



```text

Accuracy

Macro-F1

Precision

Recall

Calibration

```



\## Recovery Prediction



```text

ROC-AUC

PR-AUC

Log Loss

Brier Score

Calibration

```



\---



\# 42. Decision Quality Metrics



Measure whether APRO selected good actions.



Useful metrics:



```text

Optimal Action Rate

Regret

Expected Value Capture

Action Selection Accuracy

```



\---



\# 43. Regret



For a case:



```text

Regret

=

Best achievable recovered value

−

APRO recovered value

```



using hidden benchmark outcomes.



This metric must only be used during evaluation.



APRO must never receive the hidden optimal outcome during decision-making.



\---



\# 44. Expected Value Capture



Conceptually:



```text

Expected Value Capture

=

Actual Recovered Value

/

Best Achievable Recovered Value

```



This measures how much of the available recovery opportunity APRO captured.



\---



\# 45. Model vs Decision vs Economic Layers



The evaluation report must separate:



```text

MODEL

Did the prediction work?



DECISION

Did APRO choose the right action?



ECONOMIC

Did the action recover more money?



SAFETY

Did APRO remain within constraints?

```



This prevents a single metric from hiding system weaknesses.



\---



\# 46. Benchmark Report



Each benchmark run should generate:



```text

benchmark\_summary.json

benchmark\_summary.md

```



The report should include:



```text

dataset version

scenario version

seed

case count

revenue at risk

revenue recovered

recovery rate

incremental recovery

intervention count

intervention rate

unnecessary intervention rate

escalation rate

safety violations

latency

baseline comparisons

```



\---



\# 47. Per-Case Trace



The evaluation system must preserve a per-case trace.



Example:



```text

case\_00182



Payment:

₹699



Observed Failure:

TRANSIENT



APRO Diagnosis:

TRANSIENT

0.87



Candidates:

RETRY

PAYMENT\_LINK

OUTREACH



APRO Decision:

RETRY



Policy:

ALLOW



Outcome:

RECOVERED



Recovered:

₹699

```



\---



\# 48. Benchmark Aggregation



Results should be aggregated across:



```text

all cases

failure category

payment value bucket

action

customer behavior class

scenario family

seed

```



This helps identify where APRO performs well or poorly.



\---



\# 49. Failure-Mode Analysis



The evaluation system must explicitly identify:



\* failure categories with poor diagnosis,

\* actions with poor prediction,

\* segments with poor recovery,

\* over-intervention segments,

\* under-intervention segments,

\* high-regret cases.



A strong project should show weaknesses honestly.



\---



\# 50. Stress Tests



The benchmark must include stress tests.



Examples:



\### Duplicate Events



Large volumes of duplicate webhooks.



\### Event Reordering



Events arrive out of order.



\### High Failure Rate



Sudden spike in payment failures.



\### API Failure



External API becomes unreliable.



\### Model Failure



Model unavailable or invalid.



\### Recovery Saturation



Large number of simultaneous recovery cases.



\---



\# 51. Adversarial Evaluation



The adversarial suite should test:



```text

already captured payment

duplicate webhook

stale event

out-of-order event

high-value payment

low-confidence diagnosis

unknown failure

maximum retry

API timeout

invalid model output

```



Expected result:



```text

safe handling

```



not necessarily recovery.



\---



\# 52. Recovery Spike Scenario



The simulator should include a scenario where:



```text

failure rate suddenly increases

```



This tests whether APRO can process a batch without:



\* violating retry limits,

\* creating duplicate actions,

\* overwhelming execution,

\* blindly retrying everything.



\---



\# 53. Action Capacity Constraints



The simulator may optionally impose action capacity limits.



Example:



```text

maximum Payment Links per minute

maximum outreach messages

maximum concurrent actions

```



This allows testing operational constraints.



\---



\# 54. Batch Evaluation



APRO must support processing a full benchmark batch.



Conceptually:



```text

1,000 cases

&#x20;     ↓

APRO

&#x20;     ↓

1,000 decisions

&#x20;     ↓

1,000 outcomes

&#x20;     ↓

Metrics

```



The system must not require manual intervention for ordinary benchmark cases.



\---



\# 55. Reproducibility



A benchmark must be reproducible using:



```text

dataset\_version

scenario\_version

seed

configuration\_version

model\_versions

policy\_version

```



The benchmark runner should record all of these.



\---



\# 56. Statistical Reporting



Where multiple seeds are used, report:



```text

mean

median

standard deviation

minimum

maximum

```



for important economic metrics.



The system should avoid claiming superiority based on a single random run.



\---



\# 57. Confidence Intervals



Where practical, confidence intervals should be calculated for major metrics such as:



```text

recovery rate

incremental recovery

intervention rate

```



The method used must be documented.



\---



\# 58. Final Benchmark Protocol



The final benchmark should follow:



```text

1\. Freeze models.

2\. Freeze policies.

3\. Freeze simulator configuration.

4\. Freeze benchmark dataset/scenario generation.

5\. Run multiple seeds.

6\. Run all baselines.

7\. Run APRO.

8\. Collect outcomes.

9\. Calculate metrics.

10\. Generate report.

11\. Analyze failures.

12\. Do not tune models using final results.

```



If changes are made after observing final results, a new benchmark version must be created.



\---



\# 59. Benchmark Integrity



The benchmark must never be modified simply because APRO performs poorly.



If APRO performs poorly:



```text

Document result

↓

Identify cause

↓

Improve system

↓

Create new version

↓

Re-run evaluation

```



Do not silently change the benchmark.



\---



\# 60. No Cherry-Picking



The final pitch must not present only successful examples.



The demonstration should contain:



\* successful recovery,

\* a blocked action,

\* a failed recovery,

\* an escalation,

\* and at least one race/duplicate safety case.



This demonstrates system maturity.



\---



\# 61. Demo Dataset



A small curated demo dataset may be used for the 5-minute presentation.



However, it must be clearly labeled:



```text

DEMO CASES

```



and must not replace the full benchmark.



The full benchmark results should be reported separately.



\---



\# 62. Economic Honesty



If APRO does not outperform a baseline under a benchmark configuration, the result must be reported honestly.



The team may investigate:



\* model weakness,

\* feature weakness,

\* action-cost assumptions,

\* simulator assumptions,

\* policy constraints.



But results must never be falsified.



\---



\# 63. Simulator Governance



Every change to:



\* outcome probabilities,

\* scenario distribution,

\* hidden-state generation,

\* action effectiveness,

\* cost assumptions



must increment the simulator configuration/version.



\---



\# 64. Outcome Calibration



The simulator's action-success probabilities should be calibrated independently of APRO.



For example:



```text

Scenario:

TRANSIENT



Action:

RETRY



Underlying success probability:

0.75

```



APRO must estimate that probability from observable information.



The benchmark can then measure whether APRO's estimate approaches the hidden truth.



\---



\# 65. Distribution Coverage



The benchmark should include sufficient representation across:



```text

failure types

payment values

attempt counts

customer histories

action types

recoverability classes

```



No major category should be represented only by a handful of cases without explicit documentation.



\---



\# 66. Training vs Benchmark Simulator



Where possible, the training simulator and final benchmark generator should not be identical configurations.



Example:



```text

Training:

scenario-v1



Benchmark:

scenario-v2

```



This reduces the risk that APRO simply memorizes the simulator's exact rules.



\---



\# 67. Benchmark Challenge Set



A separate challenge set should contain unusual combinations not heavily represented in training.



Examples:



```text

rare failure + high value

first-time customer + transient failure

repeated failure + historically reliable customer

low confidence + high expected value

high confidence + poor historical recovery

```



\---



\# 68. Decision Trace Requirements



Every benchmark decision must be traceable to:



```text

case

features

diagnosis

candidate actions

probabilities

expected values

recommendation

policy result

execution

outcome

```



This makes the benchmark evidence auditable.



\---



\# 69. Minimum Winning Evidence



For the final project demonstration, APRO should aim to show:



```text

Large batch

\+

Baseline comparison

\+

Measured revenue recovered

\+

Incremental improvement

\+

Safety violations = 0

\+

Audit trail

\+

Successful Razorpay Test Mode action

```



These are stronger than a purely visual AI demo.



\---



\# 70. Evaluation Architecture



Final architecture:



```text

&#x20;                SCENARIO GENERATOR

&#x20;                       │

&#x20;             ┌─────────┴─────────┐

&#x20;             ▼                   ▼

&#x20;       HIDDEN STATE       OBSERVABLE STATE

&#x20;             │                   │

&#x20;             │                   ▼

&#x20;             │                 APRO

&#x20;             │                   │

&#x20;             │                   ▼

&#x20;             │              CHOSEN ACTION

&#x20;             │                   │

&#x20;             └──────────┬────────┘

&#x20;                        ▼

&#x20;                OUTCOME ENGINE

&#x20;                        │

&#x20;                        ▼

&#x20;                    OUTCOME

&#x20;                        │

&#x20;                        ▼

&#x20;                 METRICS ENGINE

&#x20;                        │

&#x20;             ┌──────────┼──────────┐

&#x20;             ▼          ▼          ▼

&#x20;          MODEL      DECISION   ECONOMIC

&#x20;          METRICS    METRICS     METRICS

&#x20;             │          │          │

&#x20;             └──────────┼──────────┘

&#x20;                        ▼

&#x20;                 SAFETY METRICS

&#x20;                        │

&#x20;                        ▼

&#x20;                 BENCHMARK REPORT

```



\---



\# 71. Evaluation Success Criteria



The evaluation system is successful when:



1\. APRO can process at least 1,000 synthetic cases automatically.

2\. Multiple independent seeds can be evaluated.

3\. Baselines can be compared fairly.

4\. Revenue at risk can be measured.

5\. Revenue recovered can be measured.

6\. Incremental recovery can be measured.

7\. Intervention efficiency can be measured.

8\. Safety violations can be measured.

9\. Per-case traces are preserved.

10\. Held-out evaluation is protected from training leakage.

11\. Simulator configuration is versioned.

12\. Results are reproducible.

13\. Failure cases can be inspected.

14\. APRO can demonstrate measurable value rather than only qualitative intelligence.



\---



\# 72. Final Evaluation Principle



The project does not win because:



> "The model has 94% accuracy."



It wins if the evidence shows:



> \*\*APRO makes better recovery decisions, recovers more legitimate revenue, intervenes intelligently, stops when it should, and can prove every decision it made.\*\*



\---



\# 73. Status



\*\*Version:\*\* 1.0



\*\*Status:\*\* Ready for Implementation Master Planning.



Any material change to the benchmark methodology, ground-truth generation, baseline definition or primary evaluation metrics must be documented before final evaluation.



