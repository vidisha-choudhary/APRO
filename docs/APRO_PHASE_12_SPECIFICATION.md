# APRO — PHASE 12 SPECIFICATION
## Razorpay TEST-Mode Provider Integration & External Adapter Boundary

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 12  
**Architecture Leads:** Vidisha + GPT  
**Implementation Lead:** Antigravity  
**Status:** Proposed / Architecture Specification  
**Baseline:** Phase 11 Execution Framework  
**Phase 11 Baseline Commit:** `862b463`  
**Repository:** `C:\APRO`  
**Branch:** `main`

---

## 1. Purpose

Phase 12 introduces the first concrete Razorpay provider adapter downstream of the provider-neutral Execution Framework established in Phase 11.

The architectural chain is:

`Economic Decision → Policy Permission → Execution Authorization → Provider TEST-Mode Transport`

The provider adapter is transport only. It MUST NOT become a policy engine, decision engine, recovery planner, or adaptive controller.

Phase 12 is TEST-MODE only. Production money movement, production credentials, production customer messaging, autonomous recovery loops, and multi-step adaptive re-planning remain outside this phase.

---

## 2. Core Invariant

> **Policy authorizes. Execution orchestrates. Provider adapters transport.**

The only supported provider flow is:

```text
Phase 9 RecoveryDecision
        ↓
Phase 10 PolicyDecision
        ↓
Phase 11 ApprovedExecutionRequest
        ↓
Phase 12 Razorpay TEST-Mode Adapter
        ↓
Razorpay TEST environment
        ↓
Normalized ExecutionResult
```

There MUST be no provider path that bypasses Phase 10 or Phase 11.

---

## 3. Scope

### In Scope

- Concrete Razorpay TEST-MODE adapter implementing the existing Phase 11 provider-neutral execution abstraction.
- Explicit `ExecutionMode.RAZORPAY_TEST_MODE` support.
- Provider-specific request and response models isolated inside the provider layer.
- Request validation before network dispatch.
- Deterministic mapping from APRO execution requests to provider requests.
- Normalization of provider responses into `ExecutionResult`.
- Provider error taxonomy and deterministic error mapping.
- Timeout and ambiguous-result handling.
- Provider idempotency integration where genuinely supported by the operation.
- Credential isolation and secret redaction.
- Test-mode configuration validation.
- Network-boundary tests.
- Provider-stub tests for deterministic CI behavior.
- Controlled Razorpay TEST-MODE integration tests when valid test credentials/environment are available.
- Regression protection for Phase 11 `SIMULATION` and `INTERNAL` modes.
- Phase 12 acceptance runner and documentation.

### Explicitly Out of Scope

- Production/live Razorpay execution.
- Production credentials.
- Production money movement.
- Production customer outreach.
- Autonomous adaptive recovery loops.
- Automatic recovery re-planning.
- Multi-provider routing.
- ML retraining or online learning.
- Dynamic policy changes.
- Background scheduling/workers.
- Phase 13+ recovery control loops.

---

## 4. Architecture Boundary

The adapter MUST be downstream of Phase 11.

```text
+------------------------------------------------+
| Phase 10 — Policy & Safety                     |
| ALLOW / BLOCK / REQUIRE_HUMAN_APPROVAL         |
+------------------------------------------------+
                     ↓
+------------------------------------------------+
| Phase 11 — Execution Framework                 |
| authorization / state guard / idempotency      |
| lifecycle / registry / normalized results      |
+------------------------------------------------+
                     ↓
+------------------------------------------------+
| Phase 12 — Razorpay TEST Adapter               |
| provider-specific transport only               |
+------------------------------------------------+
                     ↓
| Razorpay TEST Environment                      |
+------------------------------------------------+
```

The following packages MUST remain provider-neutral:

- `apro.domain`
- `apro.decision`
- `apro.diagnosis`
- `apro.recovery_prediction`
- `apro.policy`

Razorpay-specific types MUST NOT leak into those layers.

---

## 5. Architectural Principles

### 5.1 Authorization before transport

Only an already-authorized Phase 11 execution request may reach the adapter.

### 5.2 Fail closed

Missing configuration, unsupported operation, malformed response, authentication failure, provider rejection, or ambiguous transport state MUST fail safely.

### 5.3 Explicit execution mode

Razorpay execution MUST require:

```text
ExecutionMode.RAZORPAY_TEST_MODE
```

There MUST be no implicit promotion from `SIMULATION` to provider execution.

### 5.4 No production path

Production/live mode MUST NOT be registered by default.

Any production/live mode MUST fail closed.

### 5.5 Provider neutrality

No Razorpay request/response structure may become a domain entity.

### 5.6 Secret isolation

Secrets MUST NOT appear in:

- `ExecutionResult`
- policy traces
- logs
- exceptions
- persisted execution records
- reports
- test output

### 5.7 Normalized results

Downstream APRO code consumes normalized `ExecutionResult`, not raw provider responses.

---

## 6. Proposed Source Layout

Exact filenames may be refined to fit existing repository conventions, but the logical boundary should be:

```text
src/apro/providers/
    __init__.py
    base.py
    exceptions.py
    razorpay/
        __init__.py
        config.py
        client.py
        models.py
        mapper.py
        adapter.py
        errors.py
        security.py
```

The existing Phase 11 execution registry/interface should be extended or integrated rather than replaced.

No Phase 0–11 contract should be rewritten unnecessarily.

---

## 7. Provider Adapter Contract

The Razorpay adapter MUST implement the Phase 11 abstraction.

Conceptually:

```python
class RazorpayTestModeExecutor(BaseExecutor):
    async def validate(
        self,
        request: ApprovedExecutionRequest,
    ) -> None: ...

    async def execute(
        self,
        request: ApprovedExecutionRequest,
    ) -> ExecutionResult: ...
```

The exact method signatures MUST follow the actual Phase 11 repository interface.

The adapter receives an immutable approved request and returns an immutable normalized result.

---

## 8. Supported Operation Matrix

Phase 12 MUST explicitly document which `RecoveryAction` values are:

- supported in `RAZORPAY_TEST_MODE`,
- simulation-only,
- internal-only,
- unsupported.

A provider-specific action mapping MUST NOT be inferred implicitly.

Unsupported combinations MUST fail closed.

The implementation MUST NOT create a generic provider endpoint abstraction without evidence that the selected Razorpay operation supports it.

---

## 9. Configuration

Configuration MUST be explicit, validated, and isolated.

Minimum categories:

```text
provider
execution mode
test credential references
request timeout
environment identifier
```

Where an operation has provider-specific options, those options must be strongly validated.

Secrets MUST come from environment/configuration mechanisms, never hard-coded source.

For Phase 12:

```text
PRODUCTION_CREDENTIALS = FORBIDDEN
```

Configuration objects should be immutable after validation.

A missing TEST-mode configuration MUST fail clearly and safely.

---

## 10. Credential Security

The implementation MUST:

1. Never hard-code credentials.
2. Never persist raw credentials.
3. Never include secrets in exceptions.
4. Never include authorization headers in logs or traces.
5. Never serialize credential values into execution records.
6. Redact provider-sensitive fields.
7. Keep credential access localized to the provider boundary.
8. Reject invalid/malformed credential configuration.

Tests MUST prove secrets are absent from:

```text
ExecutionResult
exceptions
traces
logs
serialized provider artifacts
acceptance output
```

---

## 11. Request Mapping

The adapter must translate:

```text
ApprovedExecutionRequest
```

into an explicit provider request.

The mapping MUST:

- validate required fields before network access,
- preserve the APRO action identity,
- preserve execution/idempotency identity,
- reject unsupported parameters,
- reject secret-bearing arbitrary parameters,
- avoid sending irrelevant internal fields,
- avoid serializing raw domain objects,
- be deterministic for equivalent frozen inputs.

Provider-specific request objects MUST be separate from domain objects.

---

## 12. Response Mapping

Provider responses MUST map to:

```text
SUCCEEDED
FAILED
UNKNOWN
CANCELLED
```

Rules:

```text
Definitive success       → SUCCEEDED
Definitive provider fail → FAILED
Ambiguous outcome        → UNKNOWN
Local explicit cancel    → CANCELLED
```

The adapter MUST NOT interpret an ambiguous response as success.

Raw provider response bodies must not become the default public result surface.

---

## 13. Timeout and Ambiguity

A network timeout does not prove that a provider operation did not execute.

Therefore:

```text
provider timeout
      ↓
UNKNOWN
```

unless a definitive provider response establishes non-execution.

The adapter MUST NOT blindly retry an ambiguous request.

Any later reconciliation mechanism must be separately scoped and approved.

---

## 14. Idempotency

Phase 11 APRO idempotency remains authoritative.

Provider-side idempotency, where available, is a second layer.

Requirements:

- duplicate APRO execution requests remain protected by Phase 11;
- provider idempotency identifiers are deterministic where supported;
- provider IDs do not depend on hidden randomness or current wall-clock time;
- provider idempotency MUST NOT replace APRO idempotency;
- duplicate execution claims must not result in duplicate provider dispatch.

---

## 15. Retry Boundary

Distinguish:

```text
transport retry
```

from:

```text
recovery retry
```

A transport retry is permitted only where provider semantics make it safe.

Phase 12 MUST NOT implement adaptive recovery loops such as:

```text
provider failure
   ↓
choose new action
   ↓
execute
   ↓
re-evaluate
   ↓
repeat
```

---

## 16. Error Taxonomy

The provider layer should distinguish at least:

```text
ProviderConfigurationError
ProviderCredentialError
ProviderRequestValidationError
UnsupportedProviderOperationError
ProviderAuthenticationError
ProviderAuthorizationError
ProviderRateLimitError
ProviderRejectedError
ProviderUnavailableError
ProviderTimeoutError
ProviderMalformedResponseError
ProviderAmbiguousResultError
```

Provider-specific exceptions MUST be normalized at the Phase 11 result boundary without exposing credentials.

---

## 17. Network Boundary

All external network access in Phase 12 MUST live inside the provider adapter/client boundary.

No network calls are permitted from:

```text
domain
policy
decision
diagnosis
recovery_prediction
```

The provider client MUST be replaceable by a deterministic test stub.

CI tests MUST NOT depend on external network access unless explicitly invoked as an integration suite.

---

## 18. Testing Strategy

### 18.1 Pure unit tests

Cover:

- configuration validation,
- supported operation matrix,
- request mapping,
- response mapping,
- error mapping,
- redaction,
- idempotency mapping,
- unsupported modes,
- malformed provider responses.

No network.

### 18.2 Provider integration tests

When TEST credentials/environment are supplied:

- authentication/configuration,
- supported TEST operation,
- provider rejection,
- malformed response handling,
- timeout handling,
- idempotency behavior where applicable.

When external TEST environment is unavailable:

- use deterministic provider stubs,
- mark live-provider integration as unavailable rather than pretending it passed.

### 18.3 Execution integration tests

Prove:

```text
Phase 10 ALLOW
  ↓
Phase 11 execution authorization
  ↓
Phase 12 adapter
  ↓
normalized ExecutionResult
```

Also prove:

- BLOCK never reaches provider,
- missing human approval never reaches provider,
- action mismatch never reaches provider,
- captured-payment StateGuard blocks dispatch,
- duplicate APRO execution does not duplicate provider dispatch.

### 18.4 Security and boundary tests

Prove:

- production mode unavailable,
- production credentials rejected/unavailable,
- secrets never leak,
- adapter is the only network boundary,
- upstream layers remain provider-neutral,
- no adaptive loop exists.

---

## 19. Required Test Modules

Recommended structure:

```text
tests/providers/
    test_config.py
    test_models.py
    test_request_mapping.py
    test_response_mapping.py
    test_errors.py
    test_security.py
    test_idempotency.py
    test_razorpay_adapter.py
    test_razorpay_timeout.py
    test_razorpay_malformed_response.py
    test_execution_integration.py
    test_network_boundary.py
    test_no_production_access.py
    test_phase_boundary.py
```

Use existing repository naming conventions when a better equivalent exists.

---

## 20. Acceptance Criteria

### Authorization

**AC-01** — Only Phase 11-approved requests reach the adapter.

**AC-02** — `BLOCK` cannot invoke provider execution.

**AC-03** — `REQUIRE_HUMAN_APPROVAL` without valid approval cannot invoke provider execution.

**AC-04** — Action/case/payment binding remains enforced before dispatch.

### Provider Integration

**AC-05** — Razorpay TEST MODE is explicitly selectable.

**AC-06** — Unsupported modes fail closed.

**AC-07** — Supported action-to-provider mappings are explicit.

**AC-08** — Unsupported action/provider combinations fail closed.

**AC-09** — Provider results normalize deterministically into `ExecutionResult`.

### Safety

**AC-10** — Captured payment is rejected before provider dispatch.

**AC-11** — Phase 11 final StateGuard remains authoritative.

**AC-12** — Ambiguous provider results map to `UNKNOWN`.

**AC-13** — Ambiguous results do not trigger blind recovery retry.

### Idempotency

**AC-14** — Phase 11 APRO idempotency remains authoritative.

**AC-15** — Provider idempotency identifiers are deterministic where supported.

**AC-16** — Duplicate APRO execution requests cannot cause duplicate provider dispatch.

### Security

**AC-17** — No credentials are hard-coded.

**AC-18** — Secrets are absent from results, traces, logs, and errors.

**AC-19** — Invalid credential/configuration state fails closed.

**AC-20** — Production/live credentials and production execution are unavailable.

### Network Boundary

**AC-21** — External network access exists only in the provider adapter/client.

**AC-22** — Upstream layers contain no provider network calls.

**AC-23** — Provider transport can be deterministically stubbed.

### Determinism

**AC-24** — Equivalent frozen inputs generate equivalent provider request structures.

**AC-25** — Error classification is deterministic.

**AC-26** — Provider integration does not alter APRO execution identity semantics.

### Compatibility

**AC-27** — `SIMULATION` remains unchanged.

**AC-28** — `INTERNAL` remains unchanged.

**AC-29** — Full Phase 0–11 regression remains green.

**AC-30** — Existing Phase 11 concurrency/idempotency guarantees remain green.

### Phase Boundary

**AC-31** — No production money movement is possible.

**AC-32** — No production customer communication is possible.

**AC-33** — No autonomous adaptive recovery loop is introduced.

**AC-34** — No provider-specific logic leaks into upstream modules.

### Documentation / Provenance

**AC-35** — TEST-mode configuration is documented.

**AC-36** — Supported operation matrix is documented.

**AC-37** — TEST-mode integration/stub evidence is documented with credential-safe outputs.

**AC-38** — A genuine Phase 12 acceptance runner verifies all mandatory criteria.

---

## 21. Manual Acceptance Scenarios

A compact human-validation suite should cover:

1. **Authorized TEST-Mode Operation**  
   A valid Phase 10 ALLOW / Phase 11 execution request reaches the Razorpay TEST adapter and returns a normalized result.

2. **Production Mode Fail-Closed**  
   Attempting production/live mode fails before production transport.

3. **Captured Payment Recheck**  
   Payment becomes CAPTURED before dispatch; Phase 11 StateGuard blocks provider access.

4. **Provider Rejection**  
   Controlled provider rejection maps to `FAILED`.

5. **Provider Timeout / Ambiguous Result**  
   Controlled timeout maps to `UNKNOWN` without blind recovery retry.

6. **Duplicate Execution**  
   Repeating the same APRO execution identity cannot cause duplicate dispatch.

7. **Secret Isolation**  
   Credentials are absent from result, trace, log, and error surfaces.

8. **Simulation Regression**  
   Simulation remains provider-free and unchanged.

---

## 22. Acceptance Runner

Create:

```text
scripts/run_phase_12_acceptance.py
```

It MUST:

1. Verify every mandatory AC individually.
2. Use genuine assertions.
3. Exercise provider stubs deterministically.
4. Support explicit TEST-mode integration checks when configured.
5. Fail the process on any mandatory failure.
6. Verify Phase 0–11 regression compatibility.
7. Verify no production mode is available.
8. Verify secret isolation.
9. Verify network-boundary restrictions.
10. Verify deterministic request/response mapping.
11. Distinguish:
   - stub evidence,
   - real TEST-mode evidence,
   - automated-only evidence.
12. Never print credentials.

Placeholder loops and unconditional PASS statements are prohibited.

---

## 23. Quality Gates

Before Phase 12 closure:

```text
pytest tests/providers/
pytest tests/
ruff check .
ruff format --check .
mypy src
python scripts/run_phase_12_acceptance.py
```

All mandatory commands must pass.

Any external TEST-mode suite must report whether it ran against a real configured TEST environment or a deterministic stub.

---

## 24. Regression Requirements

Phase 12 must preserve:

```text
Prediction != Permission
Permission != Execution
Execution != Provider Transport
```

It must not weaken:

- policy precedence,
- approval integrity,
- captured-payment safety,
- StateGuard,
- domain state machines,
- idempotency,
- concurrency safety,
- anti-leakage,
- simulation determinism,
- provider-neutral upstream architecture.

---

## 25. Explicit Non-Goals

The following must remain absent:

```text
production Razorpay endpoint
production Razorpay credentials
production money movement
production customer messaging
automatic recovery re-planning
adaptive recovery loop
autonomous recurring execution
cross-provider routing
self-modifying policy
ML retraining
```

If implementation requires any of these, stop and request architecture review.

---

## 26. Completion Definition

Phase 12 is complete only when:

```text
1. Razorpay TEST adapter exists.
2. Phase 11 adapter boundary is reused.
3. Provider logic is isolated.
4. Authorization cannot be bypassed.
5. StateGuard remains authoritative.
6. APRO idempotency remains authoritative.
7. Ambiguous provider results fail safely.
8. Secrets are isolated.
9. Production mode is unavailable.
10. Simulation/Internal behavior remains unchanged.
11. Phase 12 automated tests pass.
12. Full Phase 0–12 regression passes.
13. Phase 12 acceptance runner passes genuinely.
14. Manual acceptance scenarios pass.
15. Phase-boundary checks pass.
16. Git provenance is recorded.
17. Working tree is clean.
```

Only after all conditions are satisfied may Phase 13 be planned.

---

## 27. Architecture Sign-Off Checklist

```text
[ ] Phase 10 cannot be bypassed.
[ ] Phase 11 cannot be bypassed.
[ ] Razorpay TEST MODE is explicit.
[ ] Production/live execution is unavailable.
[ ] Provider credentials are isolated.
[ ] Ambiguous results map to UNKNOWN.
[ ] Provider errors are normalized.
[ ] APRO idempotency remains authoritative.
[ ] Provider idempotency is additive only.
[ ] No upstream Razorpay coupling exists.
[ ] Simulation remains unchanged.
[ ] No adaptive loop exists.
[ ] Full regression is green.
[ ] Acceptance runner is genuine.
[ ] Manual validation is complete.
[ ] Git working tree is clean.
[ ] Phase 12 provenance is recorded.
```

---

## 28. Phase Boundary Summary

**Phase 10**  
May determine whether recovery is permitted.

**Phase 11**  
May execute an already-authorized action through a provider-neutral execution framework.

**Phase 12**  
May connect that execution framework to Razorpay TEST MODE through a concrete provider adapter.

**Future phase**  
Production/live provider execution requires a separate architecture-approved scope.

---

## 29. Final Architectural Statement

The APRO safety chain remains:

```text
Prediction
    ↓
Economic Decision
    ↓
Policy Permission
    ↓
Execution Authorization
    ↓
Razorpay TEST-Mode Transport
```

> **The Razorpay adapter is never the authority. It can only transport an execution that APRO policy has already permitted and the execution framework has already authorized.**

# PHASE 12 SPECIFICATION — READY FOR IMPLEMENTATION PLANNING
