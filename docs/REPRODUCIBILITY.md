# APRO — Reproducibility Specification & Provenance Guide

This document defines the cryptographic provenance, dataset hashing, random seed management, and audit trail reconstruction mechanisms implemented across APRO to guarantee complete scientific and operational reproducibility.

---

## 1. Principles of Reproducibility in APRO

APRO treats reproducibility as an engineering invariant across four layers:

```text
┌─────────────────────────────────┐
│ 1. Code Provenance              │ ──> Git commit hash / code revision snapshot
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Data Provenance              │ ──> Cryptographic SHA-256 dataset digests
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. Execution Determinism        │ ──> Fixed random seeds and pseudorandom stream isolation
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Output Hash Manifest         │ ──> SHA-256 content digest of evaluation reports & audit logs
└─────────────────────────────────┘
```

Repeating any evaluation or security attack with the same code revision, dataset digest, and random seed is guaranteed to produce identical statistical outcomes and an identical canonical hash.

---

## 2. Benchmark Run Provenance Structure

Every benchmark run produces a `ReproducibilityManifest` stored alongside the evaluation report in PostgreSQL.

### Manifest Schema

```json
{
  "benchmark_run_id": "eval_run_20260908_170100",
  "report_hash": "a1b2c3d4e5f6... (64-char SHA-256)",
  "dataset_name": "canonical_payment_failures_v1",
  "dataset_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "code_revision": "3a10eea2caf0d2ef8d5de65aa9cdeb7b34f8f556",
  "created_at": "2026-09-08T12:00:00Z",
  "metric_schema_version": "1.0.0",
  "config_snapshot": {
    "random_seed": 1701,
    "bootstrap_samples": 1000,
    "confidence_level": 0.95,
    "cost_model": {
      "retry_cost": 0.05,
      "payment_link_cost": 0.15,
      "customer_fatigue_penalty": 1.00
    }
  },
  "environment": {
    "python_version": "3.11.9",
    "platform": "Windows-10",
    "database_engine": "PostgreSQL 16.4"
  }
}
```

### Computing the Canonical Report Hash

The report hash is calculated over a deterministic JSON serialization of the primary metrics and baseline comparisons:

```python
canonical_bytes = json.dumps(
    report_dict,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode("utf-8")

report_hash = hashlib.sha256(canonical_bytes).hexdigest()
```

Any modification to numbers, baseline point estimates, or configuration parameters invalidates the hash.

---

## 3. Case Audit Reconstruction (The Seven Questions)

Phase 14 ([`src/apro/audit/`](../src/apro/audit)) implements `CaseReconstructionService`, which reconstructs the complete lifecycle history of any case from the immutable `audit_events` table.

A reconstructed case deterministically answers the Seven Authoritative Reviewer Questions:

1. **Q1 — Why did this payment fail?** Reconstructed from initial failure diagnosis event (`FAILURE_DIAGNOSED`), providing the raw gateway error code and mapped `FailureArchetype`.
2. **Q2 — What recovery action was chosen and why?** Reconstructed from `ACTION_RECOMMENDED`, showing candidate ranking and Expected Net Recovery Value (ENRV).
3. **Q3 — What was the predicted success probability?** Reconstructed from `PREDICTION_GENERATED`, showing model calibrated probability $\hat{p}$.
4. **Q4 — What was the expected net economic value?** Reconstructed from `DECISION_EVALUATED`, documenting expected recovery value minus intervention costs.
5. **Q5 — Did policy and safety authorize the action?** Reconstructed from `POLICY_EVALUATED`, documenting the policy decision (`ALLOW`, `DENY`, `ESCALATE`) and policy rule checks.
6. **Q6 — What was the outcome of the intervention?** Reconstructed from `EXECUTION_COMPLETED` and `OUTCOME_CLASSIFIED`, detailing provider response and case status.
7. **Q7 — What was the subsequent adaptive response?** Reconstructed from `ADAPTIVE_LOOP_PROGRESSION`, showing whether a next recovery cycle was scheduled or if a terminal stopping condition was triggered.

---

## 4. Reproducibility in the Reviewer Dashboard

The Live Dashboard includes a dedicated Provenance view:
- **Route:** `/dashboard/reproducibility` (or `/dashboard/reproducibility/:runId`)
- **API Endpoint:** `GET /api/dashboard/reproducibility/{benchmark_run_id}`
- **Features:**
  - Displays the active benchmark run ID and associated SHA-256 report hash.
  - Displays the dataset name and SHA-256 digest.
  - Displays the Git commit hash and execution seed.
  - Provides a one-click **"Copy Manifest"** button to export the complete cryptographic JSON record to clipboard.

---

## 5. Verifying Reproducibility Locally

To verify reproducibility of an evaluation or adversarial run:

```powershell
# 1. Run evaluation with fixed seed
python scripts/run_phase_15_acceptance.py

# 2. Run adversarial security verification with seed 1701
python scripts/run_phase_17_acceptance.py --seed 1701

# 3. Verify in pytest
pytest tests/evaluation/test_reproducibility.py -v
pytest tests/adversarial/test_replay_reproducibility.py -v
```
