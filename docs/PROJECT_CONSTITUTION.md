\# APRO — Project Constitution



\*\*Project:\*\* Adaptive Revenue Recovery Agent

\*\*Track:\*\* Razorpay AI Buildathon — Track 03: AI Revenue Recovery

\*\*Owner:\*\* Vidisha

\*\*Status:\*\* Foundational / Locked



\---



\## 1. Mission



APRO exists to recover legitimate revenue that is at risk by intelligently determining:



1\. why revenue is at risk,

2\. which recovery actions are available,

3\. which action has the highest expected value under the circumstances,

4\. whether that action is safe and permitted,

5\. whether the action succeeded,

6\. and when the system should stop or escalate.



The objective is not to maximize the number of interventions.



The objective is to maximize \*\*legitimate revenue recovered per safe intervention\*\*.



\---



\## 2. Core Principle



APRO follows this loop:



\*\*DETECT → DIAGNOSE → EVALUATE → DECIDE → GATE → ACT → OBSERVE → RECOVER / STOP / ESCALATE\*\*



Every major component must support at least one part of this loop.



Features that do not materially contribute to this loop should not be added to the core product.



\---



\## 3. AI Must Make a Meaningful Decision



AI must contribute materially to the recovery decision.



The system must not be an ordinary rule-based retry engine with an LLM placed on top.



AI may be used for:



\* failure diagnosis,

\* probability estimation,

\* recovery-action ranking,

\* expected-recovery estimation,

\* contextual reasoning,

\* human-readable explanations.



The exact AI technique will be selected based on measured performance rather than novelty.



\---



\## 4. AI Does Not Have Unrestricted Financial Authority



The AI layer must never directly control unrestricted financial actions.



The mandatory control flow is:



\*\*AI recommendation → Policy Gate → Execution\*\*



The AI recommends.



The policy layer decides whether the recommendation is permitted.



The executor performs only an approved action.



\---



\## 5. Every Action Must Be Explainable



For every recovery decision, the system must be able to record:



\* the revenue-loss event,

\* relevant evidence,

\* diagnosis,

\* model confidence,

\* candidate actions,

\* estimated recovery value,

\* selected action,

\* policy decision,

\* execution result,

\* final outcome.



A reviewer should be able to answer:



> \*\*Why did APRO do this?\*\*



without inspecting hidden model internals.



\---



\## 6. STOP Is a First-Class Decision



APRO must be capable of deciding:



\*\*STOP\*\*



when further intervention is not justified.



Examples include:



\* payment already succeeded,

\* retry limit reached,

\* expected recovery value is too low,

\* confidence is insufficient,

\* no compliant action is available,

\* continued intervention would create unnecessary customer friction.



A system that always tries to recover money is not considered intelligent.



\---



\## 7. ESCALATE Is a First-Class Decision



APRO must be capable of deciding:



\*\*ESCALATE\*\*



when human judgment is safer or more appropriate.



Examples include:



\* high-value ambiguous cases,

\* low model confidence,

\* conflicting signals,

\* policy exceptions,

\* repeated unsuccessful recovery attempts.



The system must prefer safe escalation over unsafe automation.



\---



\## 8. Safety and Policy Override Optimization



Economic optimization must never override safety or policy constraints.



The decision hierarchy is:



\*\*Safety / Policy → Eligibility → Expected Recovery Value → Action\*\*



A higher expected monetary value does not justify an action that violates policy.



\---



\## 9. No Duplicate or Stale Recovery Actions



APRO must protect against state and event inconsistencies.



The system must account for:



\* duplicate events,

\* repeated webhooks,

\* stale decisions,

\* concurrent recovery attempts,

\* payment success during decision-making,

\* already-resolved cases.



Before executing an action, APRO must verify that the payment is still eligible for recovery.



If the payment has already succeeded:



\*\*STOP.\*\*



\---



\## 10. Measure Money, Not Vanity Metrics



The primary evaluation must focus on measurable economic outcomes.



Important metrics include:



\* revenue at risk,

\* revenue recovered,

\* recovery rate,

\* incremental revenue recovered versus baseline,

\* intervention count,

\* unnecessary intervention rate,

\* escalation rate,

\* stop rate,

\* recovery cost,

\* decision latency.



Model accuracy may be reported where useful, but accuracy alone is not considered evidence of revenue impact.



\---



\## 11. Every Claim Must Be Reproducible



No performance number may be presented without a reproducible experiment.



Claims such as:



> “₹X recovered”



must be generated from a documented dataset, simulation or Razorpay Test Mode experiment.



The benchmark must be repeatable from the repository.



No fabricated business results will be presented as real-world results.



\---



\## 12. Baselines Are Mandatory



APRO must be evaluated against simpler strategies.



At minimum, we should compare against:



1\. No intervention.

2\. Always retry / static recovery strategy.

3\. A deterministic rule-based strategy.

4\. APRO.



The purpose is to demonstrate that intelligent decision-making creates measurable value beyond naive intervention.



\---



\## 13. AI Where Useful, Deterministic Code Where Better



Not every component needs AI.



Deterministic engineering should be preferred for:



\* authentication,

\* webhook verification,

\* idempotency,

\* state transitions,

\* policy enforcement,

\* retry limits,

\* audit logging,

\* execution constraints.



AI should be used where uncertainty, prediction, ranking or contextual reasoning provides meaningful value.



\---



\## 14. Failure Is Part of the Product



APRO must be deliberately tested against failure scenarios.



Examples include:



\* duplicate events,

\* API failure,

\* recovery failure,

\* payment captured during recovery,

\* repeated payment failure,

\* unknown failure reason,

\* low-confidence prediction,

\* conflicting payment states.



For significant failures, documentation must record:



\*\*What broke → Why it broke → How it was fixed → How the fix was tested\*\*



\---



\## 15. Test Mode Before Real Money



All development and demonstrations must use safe test/synthetic environments.



No real customer money will be used.



Real-world payment behavior may be simulated using controlled synthetic data and Razorpay Test Mode.



\---



\## 16. Minimal Scope, Maximum Depth



APRO will prioritize:



1\. Correctness

2\. Reliability

3\. Measurable recovery intelligence

4\. Safety

5\. Explainability

6\. Evaluation

7\. User experience

8\. Additional features



A small number of deeply implemented capabilities is preferable to a large number of shallow features.



\---



\## 17. No Feature Without Evidence



A feature should be added only if at least one of the following is true:



\* it improves recovery,

\* it improves decision quality,

\* it improves safety,

\* it improves reliability,

\* it improves explainability,

\* it improves measurable evaluation.



Features added solely because they look impressive will be rejected.



\---



\## 18. Human Oversight Is a Feature



APRO is designed as a bounded AI system, not an unrestricted autonomous financial agent.



The system must clearly communicate:



\* what it knows,

\* what it predicts,

\* what it recommends,

\* what it is allowed to do,

\* what it actually did,

\* when it needs a human.



\---



\## 19. The Demo Must Prove the System



The final demonstration must show more than a dashboard.



It should demonstrate:



\*\*A real revenue-loss event → diagnosis → candidate actions → AI decision → policy gate → execution → outcome\*\*



and at least one failure case where the system:



\*\*stops, adapts, or escalates correctly.\*\*



\---



\## 20. The Hiring Test



The project is successful only if it demonstrates that its builder can:



\* identify a meaningful payment/revenue problem,

\* reason about AI appropriately,

\* build reliable software,

\* handle failure,

\* measure outcomes honestly,

\* design safe agentic workflows,

\* and communicate engineering decisions clearly.



The goal is not merely to win a competition.



The goal is to demonstrate the ability to build systems that a payment company could trust.



\---



\# Decision Rule



When making any significant project decision, ask:



\### 1. Does it solve the defined revenue-recovery problem?



\### 2. Does it obey this constitution?



\### 3. Can we measure whether it works?



\### 4. Can we explain why it works?



\### 5. Can we safely handle when it does not work?



If the answer to these questions is not satisfactory, the decision must be reconsidered.



\---



\*\*Constitution status: LOCKED\*\*



Any change to these principles must be explicitly discussed and documented rather than silently changed during implementation.



