# APRO — Phase 5 Simulation Engine Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 5 — Simulation Engine  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0

---

## 1. Purpose

Phase 5 establishes APRO's independent synthetic scenario and outcome engine.

The simulator exists to create a controlled environment in which later APRO diagnosis, recovery prediction, economic decisioning, policy, execution, and evaluation components can be tested without relying on live customer/payment outcomes.

Phase 5 must provide a deterministic, reproducible simulation boundary containing:

- scenario generation;
- hidden ground-truth state;
- observable state available to APRO;
- action-conditioned outcome generation;
- deterministic randomness through seeds;
- scenario/configuration versioning;
- scenario families;
- recoverability classes;
- customer behavior classes;
- enough contextual variation to support later model development without embedding later-phase ML/evaluation logic.

The simulator must be useful as a trustworthy source of synthetic truth while preventing information leakage into APRO.

This phase is an independent simulation capability. It is not the dataset/evaluation framework, ML layer, decision engine, policy engine, execution framework, or final benchmark system.

---

## 2. Authoritative Source Hierarchy

Phase 5 implementation must follow the repository's existing architectural hierarchy.

Authoritative references include:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/IMPLEMENTATION_MASTER_PLAN.md`
6. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
7. `docs/PHASE_01_...` through the currently completed phase specifications/evidence as applicable
8. This document: `docs/PHASE_05_SIMULATION_ENGINE_SPECIFICATION.md`

The master plan explicitly defines Phase 5 as the **Simulation Engine**, with scope covering scenario generation, hidden state, observable state, action outcome generation, seeds, scenario versions, scenario families, recoverability classes, and customer behavior classes.

The broader simulation/evaluation specification defines the required scenario structure, hidden/observable split, outcome independence, initial scenario families and behavior classes, deterministic seeds, versioning, and the no-leakage boundary. It also makes clear that later benchmarking, dataset splitting, baseline comparison, and model evaluation belong to later phases.

Where this phase-specific document is more detailed than the broader simulation/evaluation document, it is intended to define the implementation contract for Phase 5 without changing later-phase ownership.

---

## 3. Phase 5 Objective

Implement an independent simulation system with this conceptual flow:

```text
Scenario Generator
        ↓
Hidden Scenario State
        ↓
Observable Projection
        ↓
APRO / later-phase consumer
        ↓
Chosen Action
        ↓
Independent Outcome Engine
        ↓
Observed Outcome
```

The core rule is:

> Given the underlying scenario and the chosen action, determine what happens without inspecting APRO's predictions, scores, recommendations, or internal decision state.

This independence is mandatory.

---

## 4. Scope

### 4.1 In Scope

Phase 5 implements:

- scenario generation;
- scenario identity;
- generation seed handling;
- scenario version handling;
- simulator configuration version handling;
- scenario families;
- payment context generation;
- failure context generation;
- customer behavior classes;
- customer historical context generation;
- payment amount distribution;
- payment method distribution;
- temporal/contextual variation;
- recoverability classes;
- hidden state construction;
- observable-state projection;
- candidate action representation;
- action outcome generation;
- hidden potential outcomes / ground truth for simulator use;
- deterministic random-number handling;
- reproducibility tests;
- no-leakage tests;
- scenario configuration validation;
- small smoke/demo generation capability for later phases.

### 4.2 Explicitly Out of Scope

Phase 5 must not implement:

- Model A diagnosis intelligence;
- Model B recovery prediction intelligence;
- ML training pipelines;
- feature-learning pipelines for production models;
- model calibration/evaluation tooling;
- train/validation/test dataset splitting;
- benchmark orchestration;
- baseline strategy runners;
- economic decisioning;
- expected recovery value calculation as a decision engine;
- policy enforcement;
- action execution;
- Razorpay outbound recovery operations;
- live-money activity;
- dashboard/UI;
- final audit/decision trace systems owned by later phases;
- final benchmark reporting;
- production customer intervention.

The simulator may expose clean interfaces for later phases, but it must not implement later-phase business logic.

---

## 5. Core Simulation Object

The primary Phase 5 object is a generated **SimulationScenario**.

Each generated scenario must have stable metadata and two deliberately separated views:

```text
SimulationScenario
├── metadata
├── observable_state
└── hidden_state
```

The implementation may use domain objects/dataclasses or an equivalent typed structure, but the separation must be explicit in the API.

Minimum scenario metadata:

```text
scenario_id
generation_seed
scenario_version
configuration_version
scenario_family
```

Minimum contextual content:

```text
customer_context
payment_context
failure_context
candidate_actions
```

The broader simulation/evaluation architecture also defines `hidden_state`, `observable_state`, and `action_outcomes` as first-class scenario content.

---

## 6. Scenario Identity and Versioning

### 6.1 Scenario ID

Every generated scenario must have a unique scenario identifier.

The identifier must not depend on APRO's predictions, action choice, or decision score.

### 6.2 Generation Seed

Every generated scenario must record the generation seed that produced it.

The same:

```text
configuration + scenario_version + seed
```

must reproduce the same scenario content.

### 6.3 Scenario Version

A scenario-version identifier must be part of every generated scenario.

Example:

```text
scenario-v1
```

A change to the scenario-generation contract or semantics that materially changes generated scenarios must use a new scenario version.

### 6.4 Configuration Version

Simulator assumptions must be versioned independently from scenario identity where practical.

At minimum, configuration-versioned assumptions include changes to:

- outcome probabilities;
- scenario-family distributions;
- hidden-state generation;
- action effectiveness;
- cost assumptions when those assumptions are represented by the simulator.

The broader simulation/evaluation contract requires material simulator changes to increment simulator configuration/version.

Example:

```text
config-v1
```

---

## 7. Scenario Families

The initial Phase 5 scenario-family vocabulary is:

```text
TRANSIENT_FAILURE
BANK_SIDE_FAILURE
CUSTOMER_SIDE_FAILURE
AUTHENTICATION_FAILURE
PAYMENT_METHOD_FAILURE
GATEWAY_FAILURE
TIMEOUT
UNKNOWN_FAILURE
```

These families are part of the hidden/ground-truth scenario design and may have observable proxies exposed through `failure_context`.

The family generator must:

- support deterministic generation;
- produce valid scenarios for every supported family;
- permit distribution configuration by versioned simulator configuration;
- avoid making family identity trivially synonymous with any single observable feature.

The final distribution must remain configurable rather than hard-coded into test-only logic.

---

## 8. Recoverability Classes

The simulator must support the following hidden recoverability classes:

```text
HIGHLY_RECOVERABLE
MODERATELY_RECOVERABLE
LOW_RECOVERABILITY
NON_RECOVERABLE
```

Recoverability is hidden state.

APRO must not receive a direct `recoverability` field as part of its observable input.

Recoverability may influence simulated action outcomes because it represents underlying ground truth.

The generator must allow multiple scenario families to occur across multiple recoverability classes where logically valid, preventing a trivial one-to-one mapping such as:

```text
family → recoverability
```

unless explicitly documented by simulator configuration.

---

## 9. Customer Behavior Classes

The simulator must support:

```text
HIGHLY_RESPONSIVE
NORMAL
LOW_RESPONSIVENESS
UNPREDICTABLE
```

Customer behavior class is hidden state.

APRO must receive only observable proxies available at decision time.

Observable historical context may include, for example:

```text
previous_payment_count
previous_success_count
previous_failure_count
previous_recovery_count
previous_retry_success
previous_payment_link_success
```

Only history that existed before the current decision may be exposed.

No future outcome, hidden behavior class, or post-action information may enter the observable projection.

---

## 10. Payment Context Generation

Payment scenarios must vary meaningfully rather than using one fixed synthetic payment shape.

### 10.1 Amounts

The generator must support at least:

```text
LOW_VALUE
MEDIUM_VALUE
HIGH_VALUE
```

The actual numeric distribution must be configuration-driven and versioned.

The distribution should be plausible rather than uniformly arbitrary.

### 10.2 Payment Methods

The initial supported simulation set is:

```text
CARD
UPI
NETBANKING
WALLET
OTHER_SUPPORTED_METHOD
```

Only payment methods represented by the implemented simulator/APRO contract should be generated.

### 10.3 Failure Context

Failure context must carry observable failure information available at decision time, such as:

```text
failure_reason
failure_code
```

It must not directly expose hidden mechanism variables that are intentionally reserved for the outcome engine.

---

## 11. Temporal and Historical Context

Scenario generation should vary observable context across:

```text
hour
calendar day
weekday/weekend
Time since previous attempt
time since previous successful payment
```

Historical customer context must be causally ordered before the current decision.

The generator must not create impossible histories such as a future recovery success appearing in a pre-decision feature.

---

## 12. Scenario Difficulty

Phase 5 should support scenario variation across difficulty classes:

```text
EASY
AMBIGUOUS
HARD
ADVERSARIAL
```

These are generation attributes, not model labels.

Examples of intended properties:

- **Easy:** strong observable signals.
- **Ambiguous:** conflicting observable signals.
- **Hard:** limited evidence and multiple plausible actions.
- **Adversarial:** unusual combinations designed to stress safety/robustness.

The simulator must not contain only easy scenarios.

A difficulty class may be recorded as metadata or configuration-derived hidden context, but it must not become an unearned leakage feature for APRO.

---

## 13. Candidate Action Set

The initial candidate action vocabulary is:

```text
RETRY
PAYMENT_LINK
OUTREACH
STOP
ESCALATE
```

Actual later execution availability is a later-phase concern.

Phase 5 uses these actions only to generate independent simulated outcomes.

The simulation API must allow a later consumer to ask for the outcome of a supported chosen action without granting that consumer access to hidden state.

---

## 14. Hidden State Boundary

Hidden state is information available only to the simulator and later evaluation/ground-truth components.

Examples:

```text
true_failure_mechanism
latent_customer_intent
latent_bank_condition
latent_recoverability
true_action_effectiveness
customer_behavior_class
```

The hidden state must be represented so that it is structurally difficult to accidentally pass into APRO.

### Mandatory design rule

Do not implement a single undifferentiated dictionary and rely only on naming conventions to protect hidden values.

Use a distinct hidden-state object/view from the observable-state object/view.

The public observable projection must contain only information legitimately available at decision time.

---

## 15. Observable State Projection

Observable state is the only scenario representation that APRO is allowed to consume.

It may include:

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

The projection function must be deterministic for a fixed scenario.

It must not copy hidden fields accidentally.

The implementation must provide a testable boundary such as:

```text
hidden_scenario → observable_projection()
```

and tests must verify that forbidden hidden attributes are absent.

---

## 16. Independent Outcome Engine

The Outcome Engine determines the result of a chosen action from the underlying scenario and controlled randomness.

Conceptual interface:

```text
(hidden scenario state)
        +
(chosen action)
        +
(controlled randomness)
        ↓
Independent Outcome Engine
        ↓
SUCCESS / FAILURE / PENDING
```

The broader simulation/evaluation contract explicitly requires this independence.

### 16.1 Mandatory Inputs

The outcome engine may use:

- hidden scenario state;
- chosen action;
- simulator configuration;
- controlled RNG state derived from the scenario seed / outcome seed strategy.

### 16.2 Forbidden Inputs

The outcome engine must never inspect:

```text
APRO predicted probability
APRO expected recovery value
APRO decision score
APRO selected rationale
APRO internal model state
APRO confidence
```

### 16.3 Outcome Vocabulary

The initial outcome vocabulary is:

```text
SUCCESS
FAILURE
PENDING
```

The outcome object should also carry enough metadata for later phases to understand what happened without exposing hidden truth to APRO prematurely.

---

## 17. Outcome Independence and Anti-Circularity

The simulator must answer:

> Given the underlying scenario and the chosen action, what happens?

It must never answer:

> APRO chose this action, therefore make it succeed.

This is a hard architectural constraint.

An implementation that accepts APRO's predicted probability as an input to the outcome engine fails this specification.

An implementation that changes outcome probability based on APRO's selected score fails this specification.

Outcome generation must remain reproducible and independent of downstream consumers.

---

## 18. Ground Truth and Potential Outcomes

For each scenario, the simulator may maintain hidden potential outcomes for multiple candidate actions.

Conceptually:

```text
Scenario 001

RETRY
→ SUCCESS

PAYMENT_LINK
→ SUCCESS

OUTREACH
→ FAILURE
```

APRO must see only the observable context during decision-making.

Hidden potential outcomes are available to the simulator/evaluation side only.

This structure enables later counterfactual analysis without leaking counterfactual truth into the decision path.

Phase 5 must establish the data structure and generation behavior needed for this later use, but it must not implement the later evaluation/benchmark framework.

---

## 19. Randomness and Reproducibility

The simulator must use explicit, controlled randomness.

### 19.1 Seed Requirements

Given the same:

```text
scenario_version
configuration_version
generation_seed
```

the generated scenario must be reproducible.

### 19.2 Independent Outcome Randomness

Outcome generation must use a deterministic RNG strategy that is reproducible for a chosen scenario/action while remaining independent of APRO predictions.

The implementation must document whether outcome randomness derives from:

- a deterministic child seed;
- a stable hash of scenario/action/seed;
- or an equivalent deterministic strategy.

The exact mechanism is an implementation detail, but the reproducibility contract is mandatory.

### 19.3 Multiple Seeds

The engine must support multiple independent seeds.

Example seeds may include:

```text
42
101
2026
31415
```

A single seed is useful for debugging but is not sufficient for later evidence.

---

## 20. Scenario Distribution Configuration

The simulator must separate generation logic from configuration assumptions.

Configuration should be able to control, where applicable:

- scenario-family probabilities;
- recoverability distribution;
- customer-behavior distribution;
- payment-amount distribution;
- payment-method distribution;
- temporal distributions;
- action effectiveness/outcome probabilities;
- scenario difficulty mix;
- version identifiers.

Configuration must be explicit and inspectable.

Avoid scattering probability constants across multiple generator functions.

The configuration used for generation must be identifiable through `configuration_version`.

---

## 21. No Leakage Contract

This phase requires an explicit anti-leakage contract.

### APRO may receive

Only observable information available before action selection.

### APRO may not receive

```text
true recoverability
true action effectiveness
latent customer intent
latent bank condition
hidden failure mechanism
future outcome
counterfactual outcomes
post-action information
```

unless a later phase explicitly makes a specific piece observable at a valid time.

### Testing requirement

Tests must directly assert that the observable projection excludes known hidden attributes.

A passing test suite that only checks value equality is insufficient if the hidden/observable boundary is not tested.

---

## 22. No Decision Feedback Into Generation

Scenario generation must be independent of APRO.

The generator must not accept:

- APRO predictions;
- decisions;
- recommendation scores;
- model confidence;
- expected recovery value;
- policy output.

Scenario creation happens before APRO acts.

The only later interaction is the chosen action being supplied to the independent Outcome Engine.

---

## 23. API / Module Boundary

The implementation should provide clean internal interfaces along these conceptual boundaries:

```text
ScenarioGenerator
ScenarioConfig
SimulationScenario
HiddenScenarioState
ObservableScenarioState
ObservableProjector
OutcomeEngine
ActionOutcome
```

Exact class/function names may differ if the repository's architecture dictates otherwise, but the responsibilities must remain separable.

Recommended dependency direction:

```text
ScenarioConfig
     ↓
ScenarioGenerator
     ↓
SimulationScenario
   ↙       ↘
Hidden      Observable Projection
State           ↓
             APRO consumer

Hidden State + Chosen Action + RNG
                ↓
          Outcome Engine
                ↓
          Action Outcome
```

The generator must not depend on APRO's implementation.

The outcome engine must not depend on APRO's implementation.

---

## 24. Persistence Boundary

Phase 5 does not require persistence to PostgreSQL.

The simulator should be usable as a deterministic in-process library first.

Writing simulator scenarios directly into the APRO production PostgreSQL schema is out of scope unless a later phase explicitly requires such integration.

This keeps the simulator independent from the event/case persistence system and prevents the simulation environment from becoming coupled to production workflow state.

---

## 25. Error Handling and Validation

The simulation engine must fail explicitly on invalid configuration or invalid requests.

Examples:

- unsupported scenario family;
- unsupported payment method;
- unsupported action;
- missing required context;
- malformed probability configuration;
- invalid seed value;
- invalid version identifier.

Do not silently replace invalid configuration with arbitrary defaults that change benchmark meaning.

Deterministic generation and outcome calculation must not silently swallow configuration errors.

---

## 26. Determinism Requirements

For a fixed version/configuration/seed:

1. scenario metadata must be identical;
2. hidden-state generation must be identical;
3. observable projection must be identical;
4. candidate-action availability must be identical;
5. outcome generation for the same chosen action must be identical.

Two independent simulator instances given identical deterministic inputs must produce equivalent results.

---

## 27. Test Requirements

Phase 5 tests must cover the simulation engine directly.

### 27.1 Scenario Generation

Verify:

- scenarios can be generated;
- scenario IDs are present;
- seeds are recorded;
- versions are recorded;
- all initial scenario families are supported;
- all recoverability classes are supported;
- all customer behavior classes are supported;
- payment amount categories vary;
- supported payment methods vary;
- temporal context can vary.

### 27.2 Reproducibility

For identical version/configuration/seed:

```text
scenario A == scenario B
```

for all deterministic scenario content.

### 27.3 Multiple Seeds

Generate scenarios under several seeds and verify that:

- generation succeeds;
- seed metadata is correct;
- the engine remains deterministic for each individual seed;
- different seeds are not incorrectly forced to identical scenarios.

### 27.4 Hidden/Observable Separation

Verify that hidden attributes are not present in observable state.

Test known hidden examples explicitly.

### 27.5 Outcome Engine

For every supported action:

- a valid action outcome can be generated;
- outcome vocabulary is valid;
- identical deterministic inputs reproduce the outcome;
- outcome generation does not require APRO predictions or decision scores.

### 27.6 Outcome Independence

Use a test that supplies different mock/stand-in APRO scores or prediction values externally and demonstrates that outcome generation remains unchanged.

Preferably, the production outcome-engine interface should not accept those values at all.

### 27.7 No Leakage

Test that:

```text
hidden state ≠ observable projection
```

and that adding/changing hidden-only values does not silently add hidden fields to the APRO-facing representation.

### 27.8 Configuration Versioning

Verify that changing a material simulator configuration produces a distinct configuration version and that the version is recorded in generated scenarios.

### 27.9 Invalid Configuration

Verify explicit failures for malformed probabilities, unsupported categories, and other invalid configuration.

---

## 28. Phase 5 Acceptance Criteria

Phase 5 is accepted only when all of the following are true.

### AC-01 — Scenario Generation

The engine can generate valid synthetic payment-recovery scenarios.

### AC-02 — Scenario Identity

Every generated scenario records `scenario_id` and `generation_seed`.

### AC-03 — Scenario Versioning

Every scenario records `scenario_version`.

### AC-04 — Configuration Versioning

Every scenario records `configuration_version`.

### AC-05 — Scenario Families

All initial scenario families are supported:

```text
TRANSIENT_FAILURE
BANK_SIDE_FAILURE
CUSTOMER_SIDE_FAILURE
AUTHENTICATION_FAILURE
PAYMENT_METHOD_FAILURE
GATEWAY_FAILURE
TIMEOUT
UNKNOWN_FAILURE
```

### AC-06 — Recoverability

All four recoverability classes are supported and kept hidden from observable state.

### AC-07 — Customer Behavior

All four initial behavior classes are supported and represented in APRO only through valid observable proxies.

### AC-08 — Observable State

A deterministic observable projection can be generated without hidden-state leakage.

### AC-09 — Hidden State

The simulator retains ground-truth hidden state that is inaccessible through the APRO-facing observable representation.

### AC-10 — Candidate Actions

The initial action set is supported:

```text
RETRY
PAYMENT_LINK
OUTREACH
STOP
ESCALATE
```

### AC-11 — Independent Outcomes

The outcome engine generates:

```text
SUCCESS
FAILURE
PENDING
```

without consuming APRO predictions, scores, or decisions.

### AC-12 — Reproducibility

Identical deterministic inputs reproduce identical scenarios and action outcomes.

### AC-13 — Multiple Seeds

Multiple seeds can be used successfully.

### AC-14 — Distribution Variation

Scenario generation produces meaningful variation in amount, method, temporal, historical, family, recoverability, and behavior dimensions within configured distributions.

### AC-15 — Configuration Governance

Material simulator configuration changes are versioned and observable through scenario metadata.

### AC-16 — Explicit Validation

Invalid configurations and unsupported requests fail explicitly rather than silently mutating benchmark semantics.

### AC-17 — Phase Boundary

No AI inference, ML model, economic decision engine, policy engine, execution framework, benchmark runner, or live Razorpay money operation is implemented as part of Phase 5.

### AC-18 — Test Coverage

All Phase 5 critical behavior has automated tests, including reproducibility, hidden/observable isolation, multiple seeds, and outcome independence.

---

## 29. Manual Verification Requirements

Phase 5 should include a small manual smoke verification after automated tests pass.

The manual demonstration should show:

```text
choose configuration + seed
        ↓
generate scenario
        ↓
show scenario metadata
        ↓
show observable state
        ↓
show hidden state only in simulator/debug output
        ↓
choose an action
        ↓
generate action outcome
```

The manual demonstration must make clear that:

1. APRO-facing observable state does not contain hidden truth;
2. the same deterministic seed reproduces the same scenario;
3. the outcome is derived from scenario/action state rather than an APRO prediction.

Hidden-state display is for simulator verification only and must never be part of the production APRO-facing interface.

No real payment or Razorpay API call is required for Phase 5 manual verification.

---

## 30. Implementation Constraints

- Use standard deterministic randomness facilities appropriate for the project runtime.
- Do not use wall-clock time as an uncontrolled source of randomness.
- Do not use global mutable RNG state that makes results depend on prior test execution order.
- Keep simulator configuration explicit and versioned.
- Keep hidden and observable objects structurally separate.
- Keep outcome generation independent from APRO implementation details.
- Prefer pure functions or side-effect-light components where practical.
- Avoid database dependency unless later architecture explicitly requires it.
- Do not introduce network calls.
- Do not introduce secrets.
- Do not call external AI services.

---

## 31. Phase 5 Deliverables

The implementation should result in:

1. a reusable simulation package/module;
2. scenario configuration definitions;
3. deterministic scenario generator;
4. hidden-state model;
5. observable-state projection;
6. independent outcome engine;
7. action outcome representation;
8. version/seed metadata handling;
9. comprehensive Phase 5 automated tests;
10. minimal local smoke/demo mechanism where useful for verification.

Exact repository paths are intentionally left to implementation after inspection of the existing project structure.

---

## 32. Relationship to Later Phases

Phase 5 must make later phases possible without prematurely implementing them.

```text
Phase 5 — Simulation Engine
        ↓
Phase 6 — Dataset & Evaluation Foundation
        ↓
Phase 7 — Diagnosis Intelligence
        ↓
Phase 8 — Recovery Prediction Intelligence
        ↓
Phase 9 — Economic Decision Engine
        ↓
Phase 10 — Policy & Safety Engine
        ↓
Phase 11 — Execution Framework
        ↓
Phase 12 — Razorpay Test Mode Integration
        ↓
Phase 13 — Outcome & Adaptive Recovery Loop
```

In particular:

- Phase 5 supplies synthetic truth.
- Phase 6 will turn that capability into benchmark/data infrastructure.
- Phase 7+ will consume observable information and learn/predict.
- Later evaluation may use hidden outcomes and counterfactual information, but those must remain outside APRO's decision-time view.

---

## 33. Phase Closure Evidence

Before Phase 5 can be considered complete, the implementation lead must provide:

- automated test results;
- reproducibility evidence across multiple seeds;
- hidden/observable leakage test evidence;
- independent outcome-engine evidence;
- scenario/version/configuration evidence;
- quality-gate results appropriate to the repository;
- manual smoke-test evidence;
- final Git state;
- explicit confirmation that later-phase functionality did not leak into Phase 5.

Phase 5 must not be declared closed solely because the simulator can generate examples. The acceptance criteria above and the manual evidence requirement must both be satisfied.

---

## 34. Final Design Principle

The simulator is not the model.

It is not the decision-maker.

It is not the benchmark.

It is the controlled world in which APRO can later be tested honestly.

Its most important property is not visual realism. It is **causal independence, reproducibility, and strict separation between hidden truth and decision-time observable information.**

---

## 35. Status

**Version:** 1.0  
**Status:** Ready for Implementation  
**Next Step:** Implementation of Phase 5 against this locked specification.

Any material change to scenario-generation methodology, hidden-state semantics, outcome-generation logic, scenario distributions, or versioning rules must be documented before Phase 5 acceptance.
