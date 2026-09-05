"""Tests for GET /api/dashboard/prediction-quality endpoint."""

import httpx
import pytest

from apro.evaluation.models import DecisionQualitySummary
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_prediction_quality_endpoint(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-22: Test prediction quality returns authoritative Brier score, calibration bins, and classification stats."""
    report = generate_test_benchmark_report(
        run_id="run_pred_01",
        dataset_id="snap_pred_01",
        count=30,
    )
    # Set explicit authoritative decision quality values
    report = report.model_copy(
        update={
            "decision_quality": DecisionQualitySummary(
                oracle_gap_avg=0.25,
                best_action_selection_rate=0.80,
                action_regret_avg=0.05,
            )
        }
    )
    await postgres_test_store.save_report(report)

    response = await async_client.get(
        "/api/dashboard/prediction-quality?benchmark_run_id=run_pred_01"
    )
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["brier_score"] is not None
    assert len(body["calibration_bins"]) >= 1
    assert body["classification_metrics"] is not None
    assert body["classification_metrics"]["accuracy"] is None
    assert body["classification_metrics"]["roc_auc"] is not None
    assert body["decision_quality"] is not None
    # Authoritative Phase 15 decision fields without recomputation or fake monetary derivations
    assert body["decision_quality"]["oracle_gap_avg"] == 0.25
    assert body["decision_quality"]["best_action_selection_rate"] == 0.80
    assert body["decision_quality"]["action_regret_avg"] == 0.05
    assert "net_benefit_vs_oracle" not in body["decision_quality"]
    assert "suboptimal_decision_count" not in body["decision_quality"]
    assert "suboptimal_decision_rate" not in body["decision_quality"]


@pytest.mark.asyncio
async def test_prediction_quality_missing_decision_metrics(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Requirement 4: When decision quality fields are None, the API returns None rather than fabricated values."""
    report = generate_test_benchmark_report(
        run_id="run_pred_missing_dec",
        dataset_id="snap_pred_missing_dec",
        count=20,
    )
    report = report.model_copy(
        update={
            "decision_quality": DecisionQualitySummary(
                oracle_gap_avg=None,
                best_action_selection_rate=None,
                action_regret_avg=None,
            )
        }
    )
    await postgres_test_store.save_report(report)

    response = await async_client.get(
        "/api/dashboard/prediction-quality?benchmark_run_id=run_pred_missing_dec"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["decision_quality"] is not None
    assert body["decision_quality"]["oracle_gap_avg"] is None
    assert body["decision_quality"]["best_action_selection_rate"] is None
    assert body["decision_quality"]["action_regret_avg"] is None
