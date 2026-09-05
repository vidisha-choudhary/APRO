"""Tests for GET /api/dashboard/adaptive endpoint."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_adaptive_recovery_endpoint(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-23: Test adaptive recovery metrics, cycle distributions, and boundedness."""
    report = generate_test_benchmark_report(
        run_id="run_adapt_01",
        dataset_id="snap_adapt_01",
        count=30,
    )
    await postgres_test_store.save_report(report)

    response = await async_client.get("/api/dashboard/adaptive")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["same_action_avoidance_rate"] == 1.0
    assert body["bounded_termination_rate"] == 1.0
    assert body["hard_ceiling_violations"] is None
    assert isinstance(body["cycle_distribution"], list)
    assert body["single_cycle_recovery_count"] >= 0
    assert body["multi_cycle_recovery_count"] >= 0
