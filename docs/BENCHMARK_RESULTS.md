# APRO — Benchmark Results & Evaluation Methodology

This document outlines the evaluation methodology, metric definitions, baseline models, and persisted storage schema implemented in Phase 15 ([`src/apro/evaluation/`](../src/apro/evaluation)).

---

## 1. Evaluation Methodology

APRO evaluates recovery performance using deterministic, counterfactual evaluation protocols on versioned payment failure datasets. The benchmarking engine evaluates whether APRO's adaptive decision loop outperforms industry-standard heuristics while strictly respecting policy and cost constraints.

### Core Evaluation Invariants

1. **Persisted Truth as Single Source:** Evaluation metrics are computed and persisted in the PostgreSQL `evaluation_reports` table. This markdown document summarizes the methodology and metrics schema, but does **not** hardcode static benchmark runs.
2. **Deterministic Datasets:** Evaluations execute on versioned datasets identified by cryptographic SHA-256 digests.
3. **Statistical Rigor:** Comparisons against baselines report point estimates alongside 95% bootstrap confidence intervals and hypothesis test p-values.
4. **No Oracle Leakage:** Benchmarking strictly separates evaluation ground truth (e.g. latent customer payment propensity) from runtime decision inputs.

---

## 2. Baseline Comparison Models

APRO is evaluated against four reference baseline strategies:

| Baseline Model | Description | Behavioral Rules |
|---|---|---|
| **Zero-Action Baseline** | Measures organic customer recovery without merchant intervention. | Dispatches 0 recovery actions. Measures organic customer retry or payment link self-service. |
| **Blind Retry Baseline** | Represents naive automatic retry systems. | Retries every technical or funds-related failure immediately or on fixed schedules, ignoring costs. |
| **Immediate Retry Baseline** | Standard single-retry heuristic. | Triggers an immediate retry once, and terminates if that attempt fails. |
| **Rule-Based Heuristic** | Common industry error-code routing table. | Routes purely based on raw gateway error codes using fixed lookup tables without economic optimization. |

---

## 3. Primary Evaluated Metrics

### Economic & Recovery KPIs

1. **Recovery Rate (%):**
   $$\text{Recovery Rate} = \frac{\text{Successfully Recovered Cases}}{\text{Total Eligible Failed Cases}}$$
2. **Net Revenue Recovered ($/₹):**
   $$\text{Net Revenue} = \sum \text{Recovered Amounts} - \sum \text{Intervention Execution Costs} - \sum \text{Customer Fatigue Costs}$$
3. **Recovery Uplift (Percentage Points):**
   $$\text{Uplift} = \text{Recovery Rate}_{\text{APRO}} - \text{Recovery Rate}_{\text{Baseline}}$$
4. **Cost Efficiency Ratio:**
   $$\text{Cost Efficiency} = \frac{\text{Net Revenue Recovered}}{\text{Total Recovery Operating Cost}}$$

### Probabilistic Prediction Quality

- **Brier Score:** Mean squared difference between predicted recovery probability and actual binary outcome.
- **Expected Calibration Error (ECE):** Weighted absolute difference between predicted confidence and empirical accuracy across 10 calibration bins.
- **ROC-AUC & PR-AUC:** Area under Receiver Operating Characteristic and Precision-Recall curves.

### Safety Invariants

- **Unsafe Dispatch Count:** Must be **0**. (Actions executed on unapproved policies).
- **Policy Bypass Count:** Must be **0**. (Actions that skipped the policy authorization gate).
- **Duplicate Execution Count:** Must be **0**. (Duplicate provider calls for identical semantic events).

---

## 4. Persisted Benchmark Storage Schema

Benchmark results are stored directly in PostgreSQL via `PostgreSQLEvaluationArtifactStore`:

```sql
CREATE TABLE IF NOT EXISTS evaluation_reports (
    benchmark_run_id VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metric_schema_version VARCHAR(16) NOT NULL,
    dataset_name VARCHAR(128) NOT NULL,
    dataset_hash VARCHAR(64) NOT NULL,
    code_revision VARCHAR(64) NOT NULL,
    report_hash VARCHAR(64) NOT NULL,
    primary_kpis JSONB NOT NULL,
    baseline_comparisons JSONB NOT NULL,
    prediction_quality JSONB,
    adaptive_recovery JSONB,
    cohort_breakdown JSONB,
    safety_metrics JSONB NOT NULL,
    config_snapshot JSONB NOT NULL
);
```

### Database Immutability Trigger

To guarantee that evaluation records cannot be modified or forged post-run, PostgreSQL enforces an immutability trigger created in migration `004`:

```sql
CREATE OR REPLACE FUNCTION prevent_benchmark_reports_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'evaluation_reports rows are immutable and cannot be updated or deleted';
END;
$$ LANGUAGE plpgsql;
```

---

## 5. Inspecting Benchmark Results in the Dashboard

The Live Reviewer Dashboard directly queries this table:

- **List Benchmark Runs:** `GET /api/dashboard/runs` provides all persisted run summaries for the top-bar dropdown.
- **Detailed Benchmarks:** `GET /api/dashboard/benchmarks?benchmark_run_id=<run_id>` returns full baseline comparisons and statistical confidence intervals.
- **Prediction Reliability:** `GET /api/dashboard/prediction-quality?benchmark_run_id=<run_id>` provides calibration bin distributions for the calibration chart.
- **Provenance Manifest:** `GET /api/dashboard/reproducibility/<run_id>` returns the full cryptographic audit record.

*Note:* If no benchmark runs exist in your local PostgreSQL database, the dashboard displays clean empty states. Phase acceptance runners (such as `scripts/run_phase_16_acceptance.py`) must **never** be run against `apro_test_db`, as acceptance runners populate ephemeral test fixtures and truncate evaluation tables. `apro_test_db` must contain canonical evaluation records only.
