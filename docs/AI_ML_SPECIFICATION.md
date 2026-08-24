\# APRO — AI/ML Specification



\*\*Project:\*\* Adaptive Payment Recovery Orchestrator

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Owner:\*\* Vidisha

\*\*Architecture Leads:\*\* Vidisha + GPT

\*\*Implementation Lead:\*\* Antigravity

\*\*Status:\*\* AI/ML Specification

\*\*Version:\*\* 1.0



\---



\# 1. Purpose



This document defines exactly where and how artificial intelligence and machine learning are used inside APRO.



The objective is not to maximize the amount of AI in the system.



The objective is to use AI where prediction provides measurable value in deciding how to recover revenue.



APRO must remain:



\* measurable,

\* explainable,

\* reproducible,

\* policy-constrained,

\* auditable,

\* and resistant to data leakage.



\---



\# 2. AI/ML Philosophy



APRO follows the principle:



> \*\*Use machine learning for uncertainty. Use deterministic software for authority.\*\*



Machine learning may answer:



> "What is likely to happen?"



It must not independently answer:



> "What am I legally/operationally allowed to do?"



The system therefore separates:



```text

Observed Facts

&#x20;     ↓

AI / ML Prediction

&#x20;     ↓

Economic Evaluation

&#x20;     ↓

Deterministic Policy

&#x20;     ↓

Execution

```



\---



\# 3. AI/ML Components



APRO v1 contains two primary predictive intelligence components:



\## Model A — Failure Diagnosis



Answers:



> \*\*Why did the payment fail?\*\*



\## Model B — Recovery Outcome Prediction



Answers:



> \*\*If we perform action X now, how likely is the payment to recover?\*\*



These predictions are then used by deterministic economic decisioning.



\---



\# 4. Model A — Failure Diagnosis



\## Objective



Classify a failed payment into a useful failure category.



Initial taxonomy:



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



The taxonomy may be adjusted if dataset analysis demonstrates that categories are:



\* indistinguishable,

\* too sparse,

\* operationally redundant,

\* or not useful for recovery decisions.



The final taxonomy must be justified using evidence.



\---



\# 5. Diagnosis Model Output



Every diagnosis prediction must produce:



```text

category

confidence

class\_probabilities

evidence\_features

model\_name

model\_version

prediction\_timestamp

```



Example:



```text

category:

TRANSIENT



confidence:

0.87



class\_probabilities:

TRANSIENT: 0.87

BANK\_SIDE: 0.05

GATEWAY: 0.04

TIMEOUT: 0.02

UNKNOWN: 0.02

```



\---



\# 6. Diagnosis Features



Only information available at decision time may be used.



Potential features include:



\### Payment features



```text

amount

currency

payment\_method

attempt\_number

time\_of\_day

day\_of\_week

```



\### Failure features



```text

failure\_code

failure\_source

failure\_step

failure\_reason

failure\_description

```



\### Historical features



```text

customer\_previous\_payment\_count

customer\_success\_rate

customer\_failure\_rate

previous\_recovery\_rate

previous\_attempt\_count

```



\### Temporal features



```text

time\_since\_previous\_attempt

time\_since\_last\_success

recent\_failure\_frequency

```



\---



\# 7. Diagnosis Feature Rule



Every feature must satisfy:



> \*\*Could this information have been known at the exact moment APRO made the decision?\*\*



If the answer is no, the feature is prohibited.



This rule exists to prevent future-information leakage.



\---



\# 8. Diagnosis Training Target



The training label represents the underlying failure category.



For synthetic data, the scenario generator will define the hidden ground-truth failure class.



For any real/test-mode data where a trustworthy failure category can be derived from provider evidence, that evidence may be used.



Ground truth must not be generated from the model's own prediction.



\---



\# 9. Diagnosis Candidate Models



The initial model search should prioritize simple, interpretable models.



Candidate models:



```text

Logistic Regression

Decision Tree

Random Forest

Gradient Boosted Trees

XGBoost / LightGBM

```



The final model is selected through validation performance and operational usefulness.



The most complex model does not automatically win.



\---



\# 10. Diagnosis Baseline



At minimum, APRO must establish a baseline.



Candidate baseline:



> Predict the majority failure class.



A stronger deterministic baseline may also be implemented:



> Map known failure codes/reasons directly to predefined categories.



The ML model must demonstrate improvement over a meaningful baseline.



\---



\# 11. Diagnosis Evaluation Metrics



The diagnosis model will be evaluated using:



```text

Accuracy

Precision

Recall

F1

Macro-F1

Confusion Matrix

Calibration

```



Macro-F1 is important because some failure classes may be less frequent than others.



The final evaluation must report class-level performance rather than only overall accuracy.



\---



\# 12. Model B — Recovery Outcome Prediction



This is the more important APRO intelligence component.



For every candidate action `a`, APRO estimates:



```text

P(success | context, action)

```



Examples:



```text

P(success | context, RETRY)

P(success | context, PAYMENT\_LINK)

P(success | context, OUTREACH)

```



The prediction represents the probability that the action will result in successful recovery under the defined observation window.



\---



\# 13. Recovery Prediction Architecture



The conceptual flow is:



```text

Payment Context

&#x20;     +

Diagnosis

&#x20;     +

Historical Context

&#x20;     +

Candidate Action

&#x20;     ↓

Feature Builder

&#x20;     ↓

Recovery Model

&#x20;     ↓

P(success | context, action)

```



The model must explicitly receive the proposed action as a feature.



This allows one model to estimate multiple action outcomes.



\---



\# 14. Why Action-Conditioned Prediction



APRO is not trying to answer:



> "Will this payment recover?"



It is trying to answer:



> "How likely is recovery if we choose this specific action?"



Therefore the prediction target is action-conditioned.



Conceptually:



```text

same payment

&#x20;     │

&#x20;     ├── RETRY → 0.72

&#x20;     ├── PAYMENT\_LINK → 0.51

&#x20;     └── OUTREACH → 0.31

```



This is essential to APRO's identity as a decision orchestrator rather than a simple failure classifier.



\---



\# 15. Recovery Training Dataset



Each training example represents an action opportunity.



Conceptually:



```text

case\_context

\+

action

\+

historical information available at decision time

\+

observed outcome

```



Example:



```text

amount = ₹699

failure\_category = TRANSIENT

attempt\_count = 1

customer\_success\_rate = 0.81

action = RETRY



outcome = SUCCESS

```



Another example:



```text

amount = ₹699

failure\_category = AUTHENTICATION

attempt\_count = 2

customer\_success\_rate = 0.81

action = RETRY



outcome = FAILURE

```



\---



\# 16. Ground Truth



The recovery model's target is:



```text

1 = successful recovery

0 = unsuccessful recovery

```



The observation window must be defined consistently for each action.



For example:



```text

action executed

&#x20;       ↓

observation window

&#x20;       ↓

payment captured?

```



The exact windows will be finalized during implementation based on the action type and available Test Mode behavior.



\---



\# 17. Critical Anti-Leakage Rule



The recovery model must never receive information that occurred after the action decision.



Invalid:



```text

Decision at 10:00



Feature:

payment captured at 10:05

```



Valid:



```text

Decision at 10:00



Feature:

customer had previously recovered

after a retry three days earlier

```



The feature-generation system must use a strict decision timestamp.



\---



\# 18. Counterfactual Limitation



A real historical payment normally provides an outcome for only the action that was actually taken.



Example:



```text

Customer received RETRY

→ recovered

```



We do not automatically know:



```text

What would have happened with PAYMENT\_LINK?

```



Therefore APRO must not pretend that historical observational data gives perfect counterfactual information.



This limitation must be explicitly acknowledged.



\---



\# 19. Synthetic Counterfactual Data



The simulator may provide controlled counterfactual outcomes.



For a scenario, it may evaluate:



```text

RETRY

PAYMENT\_LINK

OUTREACH

STOP

```



under controlled conditions.



However, synthetic counterfactuals must not be presented as real merchant outcomes.



\---



\# 20. Avoiding Simulator-Induced Bias



The simulator must not be designed solely to reward APRO.



The system must not use:



```text

APRO decision

```



as an input to determine:



```text

ground\_truth outcome

```



before the action has been evaluated.



Instead:



```text

Hidden Scenario State

&#x20;       ↓

Outcome Function

&#x20;       ↓

Action Outcome

```



and separately:



```text

Observed Context

&#x20;       ↓

APRO Decision

```



The two paths must remain independent.



\---



\# 21. Hidden Scenario State



Synthetic scenarios may contain hidden variables such as:



```text

failure\_mechanism

customer\_intent

bank\_condition

authentication\_requirement

payment\_method\_condition

recovery\_propensity

```



These variables may influence the simulated outcome.



APRO should only receive observable information that would realistically be available at decision time.



This creates a meaningful prediction problem.



\---



\# 22. Recovery Model Candidates



Candidate models:



```text

Logistic Regression

Random Forest

Gradient Boosted Trees

XGBoost / LightGBM

```



The first implementation should establish a simple baseline before testing more sophisticated models.



\---



\# 23. Recovery Model Baseline



At minimum:



\## Baseline A — Global Recovery Rate



Estimate:



```text

P(success | action)

```



using the overall historical/synthetic recovery rate for each action.



This ignores contextual features.



Example:



```text

RETRY = 0.61

PAYMENT\_LINK = 0.44

OUTREACH = 0.29

```



APRO's contextual model must demonstrate whether using additional information improves predictions.



\---



\# 24. Recovery Model Evaluation



Metrics:



```text

ROC-AUC

PR-AUC

Log Loss

Brier Score

Calibration

Precision

Recall

```



Because the probabilities are used to calculate expected monetary value, \*\*calibration is especially important\*\*.



A model with slightly lower classification accuracy but substantially better probability calibration may be preferable.



\---



\# 25. Probability Calibration



Predicted probabilities should be evaluated for calibration.



Potential techniques:



```text

Platt Scaling

Isotonic Regression

```



The calibration method must be selected using validation data only.



The final test set must remain untouched until final evaluation.



\---



\# 26. Expected Recovery Value



For action `a`:



```text

ERV(a)

=

P(success | context, a)

×

recoverable\_amount

−

action\_cost

```



All monetary values must use integer minor units internally.



\---



\# 27. Action Cost



Action cost represents the economic or operational penalty associated with an intervention.



Initial v1 costs may include:



```text

direct monetary cost

estimated operational cost

estimated customer-friction cost

```



If a cost cannot be measured credibly, it must not be given a fake precision.



The system may initially use a configurable cost model.



All assumptions must be documented.



\---



\# 28. Decision Selection



For eligible actions:



```text

ERV(RETRY)

ERV(PAYMENT\_LINK)

ERV(OUTREACH)

ERV(STOP)

```



The decision engine selects the highest-value permissible option.



Conceptually:



```text

best\_action

=

argmax(ERV(action))

```



subject to policy constraints.



\---



\# 29. STOP as an Economic Option



STOP must be treated as a legitimate decision.



Conceptually:



```text

ERV(STOP) = 0

```



An intervention should only be preferred when its expected value exceeds the relevant stopping threshold.



This prevents APRO from intervening simply because an action exists.



\---



\# 30. ESCALATE as a Decision Option



ESCALATE may be selected when:



\* model confidence is low,

\* policy requires human review,

\* transaction value is high,

\* signals conflict,

\* action availability is uncertain,

\* or the case falls outside the model's reliable operating region.



Escalation is not treated as model failure.



It is a controlled outcome.



\---



\# 31. Uncertainty Handling



APRO must not treat every probability as equally trustworthy.



The system should identify:



```text

low confidence

out-of-distribution context

insufficient history

rare failure type

conflicting signals

```



Potential responses:



```text

STOP

ESCALATE

use conservative baseline

```



The final behavior is governed by the Policy Engine.



\---



\# 32. Out-of-Distribution Detection



The system should attempt to identify cases materially outside the training distribution.



Possible approaches:



```text

feature-range checks

rare-category detection

distance-based methods

model confidence thresholds

```



A sophisticated OOD model is not required for v1.



The system must at minimum have a conservative mechanism for obviously unsupported cases.



\---



\# 33. AI Does Not Control State



The AI model does not determine:



```text

payment.status

case.status

execution.status

```



Those are controlled by deterministic domain logic.



AI only produces predictions/recommendations.



\---



\# 34. AI Does Not Control Policy



The AI cannot override:



```text

retry limits

high-value approval requirements

captured-payment protection

unsupported-action restrictions

minimum-value thresholds

```



Policy is deterministic.



\---



\# 35. AI Does Not Execute Payments



The AI cannot directly call:



```text

Razorpay APIs

Payment Link creation

payment capture

```



Instead:



```text

AI

&#x20;↓

Recommendation

&#x20;↓

Policy

&#x20;↓

Executor

&#x20;↓

Razorpay

```



\---



\# 36. Optional LLM Layer



An LLM is optional and not part of the critical decision path.



Potential uses:



```text

case summarization

operator explanation

customer message generation

natural-language audit explanation

```



The LLM must output structured data where necessary.



\---



\# 37. LLM Safety Boundary



The LLM must not be allowed to:



\* change payment state,

\* bypass policy,

\* directly execute payment actions,

\* alter monetary values,

\* modify model predictions,

\* alter historical audit records.



Any LLM-generated content that becomes actionable must pass deterministic validation.



\---



\# 38. Explainability



Every AI decision should be explainable through structured evidence.



Example:



```text

Recommended Action:

RETRY



Why:

\- transient failure classification

\- first failure attempt

\- customer historically succeeds after retry

\- retry has highest predicted recovery value



Expected Recovery Value:

₹503



Confidence:

0.87

```



The explanation should be generated from recorded structured evidence rather than inventing a rationale after the fact.



\---



\# 39. Model Registry



Each trained model must have:



```text

model\_name

model\_version

training\_dataset\_version

feature\_schema\_version

training\_timestamp

evaluation\_metrics

calibration\_metrics

```



Example:



```text

diagnosis-v1

recovery-v1

```



\---



\# 40. Model Promotion



A model may only be promoted when it passes predefined evaluation gates.



Example:



```text

candidate model

&#x20;     ↓

validation

&#x20;     ↓

calibration

&#x20;     ↓

held-out test

&#x20;     ↓

economic benchmark

&#x20;     ↓

promotion

```



A model must not be promoted merely because it has a higher training score.



\---



\# 41. Dataset Versioning



Training datasets must have explicit versions.



Example:



```text

dataset-v1

dataset-v2

```



A model must record which dataset version was used.



\---



\# 42. Train / Validation / Test Split



Data must be divided before model tuning.



Preferred split strategy:



```text

Training

Validation

Held-out Test

```



Where temporal information is available, a temporal split is preferred.



Example:



```text

older cases → training

later cases → validation

latest cases → held-out test

```



This better represents future deployment.



\---



\# 43. Test Set Rule



The held-out test set must not be used for:



\* feature selection,

\* hyperparameter tuning,

\* threshold tuning,

\* calibration tuning,

\* repeated model selection.



It is reserved for final evaluation.



\---



\# 44. Cross-Validation



Cross-validation may be used on the training set for model selection.



For time-dependent data, temporal cross-validation should be preferred over random shuffling.



\---



\# 45. Imbalanced Data



Some failure categories and recovery outcomes may be rare.



Potential techniques:



```text

class weighting

stratified sampling

careful resampling

threshold tuning

```



Synthetic oversampling should only be used when justified and must not contaminate the held-out test set.



\---



\# 46. Feature Store



A dedicated production-grade feature store is not required for v1.



Instead, APRO will use a versioned feature-building layer.



Conceptually:



```text

Raw Events

&#x20;  ↓

Feature Builder

&#x20;  ↓

Feature Vector

&#x20;  ↓

Model

```



The same feature logic must be reproducible during evaluation.



\---



\# 47. Feature Schema Versioning



Each model prediction must identify the feature schema version.



Example:



```text

feature\_schema\_v1

```



If feature definitions change materially, a new version must be created.



\---



\# 48. Training Pipeline



Initial training pipeline:



```text

Raw Dataset

&#x20;    ↓

Validation

&#x20;    ↓

Feature Generation

&#x20;    ↓

Train / Validation / Test Split

&#x20;    ↓

Baseline

&#x20;    ↓

Candidate Models

&#x20;    ↓

Validation

&#x20;    ↓

Calibration

&#x20;    ↓

Held-Out Test

&#x20;    ↓

Economic Benchmark

&#x20;    ↓

Model Artifact

```



\---



\# 49. Recovery Model Training Objective



The primary predictive objective is:



> Estimate the probability of successful recovery for each eligible action as accurately and reliably as possible.



The business objective is:



> Maximize legitimate recovered revenue subject to policy and intervention constraints.



These are related but not identical objectives.



\---



\# 50. Decision Evaluation



A model should not be judged only by prediction metrics.



APRO must evaluate:



```text

Prediction Quality

&#x20;       +

Decision Quality

&#x20;       +

Economic Outcome

&#x20;       +

Safety

```



A highly accurate model that causes unnecessary interventions is not automatically a successful APRO model.



\---



\# 51. Policy-Aware Evaluation



Evaluation must measure whether the system correctly respects:



```text

maximum retries

high-value escalation

captured-payment stop

low-confidence handling

unsupported actions

```



Policy violations count as failures even if the predicted recovery would have been successful.



\---



\# 52. Economic Evaluation



The final benchmark must compare:



```text

No Intervention

Always Retry

Static Rules

APRO

```



Metrics:



```text

Revenue at Risk

Revenue Recovered

Recovery Rate

Incremental Revenue Recovered

Interventions

Recovered Revenue / Intervention

Unnecessary Intervention Rate

Escalation Rate

Stop Rate

```



\---



\# 53. AI Value Test



The project must answer:



> \*\*Does AI make APRO better than a reasonable deterministic strategy?\*\*



This must be demonstrated experimentally.



Possible comparison:



```text

Static Rule:

IF TRANSIENT → RETRY



APRO:

Predict outcome of each action

→ calculate ERV

→ choose best permissible action

```



If APRO does not outperform the baseline, the system must not hide that result.



The model or decision strategy must be improved or the limitation documented.



\---



\# 54. Synthetic Data Governance



Synthetic data must contain:



```text

scenario\_id

generation\_seed

scenario\_version

hidden\_ground\_truth

observable\_features

action\_outcomes

```



The hidden ground truth must remain separate from the model's observable input.



\---



\# 55. Scenario Diversity



The simulator must generate a mixture of:



\* easy cases,

\* ambiguous cases,

\* low-value cases,

\* high-value cases,

\* transient failures,

\* persistent failures,

\* repeated failures,

\* successful recoveries,

\* unrecoverable cases,

\* race conditions,

\* duplicate events,

\* API failures.



The benchmark must not consist primarily of cases that favor one strategy.



\---



\# 56. Hard Evaluation Cases



A dedicated hard-case set should include:



```text

payment captured immediately after failure

duplicate webhook

unknown failure

conflicting failure signals

high-value payment

maximum retry reached

previous recovery failure

low-confidence diagnosis

unsupported action

external API timeout

```



APRO should be evaluated for both recovery and restraint.



\---



\# 57. Recovery vs Restraint



The system has two goals:



\### Recover money when justified.



\### Avoid unnecessary intervention when not justified.



Therefore evaluation must include both:



```text

Recovery Performance

```



and:



```text

Intervention Restraint

```



\---



\# 58. AI Failure Handling



If a model fails to load, times out, produces invalid output, or returns unusable probabilities:



```text

AI failure

&#x20;  ↓

Do not execute directly

&#x20;  ↓

Fallback strategy

&#x20;  ↓

Policy

```



The fallback may be:



\* deterministic baseline,

\* STOP,

\* ESCALATE.



The exact fallback policy will be defined in the Policy/Safety Specification.



\---



\# 59. Invalid Model Output



If the model returns:



```text

NaN

negative probability

probability > 1

missing action

unknown class

```



the output must be rejected.



It must never reach the executor.



\---



\# 60. Reproducibility



Training and evaluation should record:



```text

random\_seed

dataset\_version

feature\_schema\_version

model\_version

configuration\_version

```



This allows results to be reproduced.



\---



\# 61. AI/ML Audit Record



For every production/test decision, record:



```text

model\_name

model\_version

feature\_schema\_version

prediction

probability

candidate\_actions

expected\_values

recommendation

timestamp

```



The raw feature vector need not always be duplicated in the audit log if it can be deterministically reconstructed from versioned data.



\---



\# 62. Model Monitoring



During evaluation/demo, track:



```text

prediction distribution

confidence distribution

failure-category distribution

action distribution

recovery probability distribution

```



Unexpected shifts should be visible.



\---



\# 63. Model Drift



Production-grade automated retraining is outside v1.



However, the architecture must allow future monitoring for:



\* changing failure distributions,

\* changing recovery rates,

\* probability calibration drift,

\* action-performance changes.



\---



\# 64. AI/ML Decision Boundary



The final AI/ML architecture is:



```text

&#x20;                   OBSERVED PAYMENT DATA

&#x20;                            │

&#x20;                            ▼

&#x20;                    FEATURE BUILDER

&#x20;                            │

&#x20;                ┌───────────┴───────────┐

&#x20;                ▼                       ▼

&#x20;         DIAGNOSIS MODEL        RECOVERY MODEL

&#x20;                │                       │

&#x20;                ▼                       ▼

&#x20;         Failure Category       P(success | action)

&#x20;                │                       │

&#x20;                └───────────┬───────────┘

&#x20;                            ▼

&#x20;                    ECONOMIC ENGINE

&#x20;                            │

&#x20;                            ▼

&#x20;                   ACTION RECOMMENDATION

&#x20;                            │

&#x20;                            ▼

&#x20;                      POLICY GATE

&#x20;                            │

&#x20;                   ┌────────┴────────┐

&#x20;                   ▼                 ▼

&#x20;                EXECUTE           ESCALATE

```



\---



\# 65. What AI Is Responsible For



AI/ML is responsible for:



\* interpreting uncertain failure patterns,

\* estimating recovery probabilities,

\* supporting expected-value calculations,

\* identifying useful contextual patterns.



\---



\# 66. What AI Is NOT Responsible For



AI/ML is not responsible for:



\* payment state transitions,

\* policy enforcement,

\* authorization,

\* financial execution,

\* duplicate prevention,

\* audit integrity,

\* final outcome determination.



\---



\# 67. AI/ML Success Criteria



The AI layer is considered successful only if it demonstrates:



1\. meaningful diagnosis performance,

2\. calibrated recovery probabilities,

3\. improvement over simple baselines where expected,

4\. measurable improvement in recovery decision quality,

5\. no future-information leakage,

6\. reproducible evaluation,

7\. safe behavior under uncertainty,

8\. complete model versioning,

9\. explainable structured decisions,

10\. no direct uncontrolled financial execution.



\---



\# 68. Final AI Principle



APRO does not use AI because AI is fashionable.



APRO uses AI because payment recovery contains uncertainty:



> \*\*Which failure happened?\*\*



> \*\*Which action is most likely to work?\*\*



> \*\*How valuable is that action?\*\*



AI estimates those uncertainties.



Deterministic software decides what the system is allowed to do.



That separation is fundamental to APRO.



\---



\# 69. Status



\*\*Version:\*\* 1.0



\*\*Status:\*\* Ready for Policy/Safety Design.



Any material change to the AI decision boundary, model target, feature policy, training methodology or evaluation methodology must be documented before implementation.



