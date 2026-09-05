"""Tests for GET /api/dashboard/overview endpoint."""

import httpx
import pytest

from apro.dashboard.service import DashboardService
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_overview_with_persisted_benchmark(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-01, AC-02, AC-13, AC-14, AC-15, AC-16, AC-17: Test overview reflects real persisted Phase 15 KPIs."""
    report = generate_test_benchmark_report(
        run_id="run_overview_01",
        dataset_id="snap_overview_01",
        count=20,
        recovery_modulo=2,
        amount=60000,
    )
    await postgres_test_store.save_report(report)

    response = await async_client.get("/api/dashboard/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["metadata"]["benchmark_run_id"] == "run_overview_01"
    assert body["metadata"]["report_hash"] == report.report_hash

    data = body["data"]
    assert data is not None
    assert data["eligible_cases"] == report.primary_kpis.eligible_cases
    assert data["recovered_cases"] == report.primary_kpis.recovered_cases
    assert data["recovery_rate"] == report.primary_kpis.recovery_rate
    assert data["gross_recovered_revenue"] == report.primary_kpis.gross_recovered_amount
    assert data["net_recovered_revenue"] == report.primary_kpis.net_recovered_revenue
    assert (
        data["total_intervention_cost"] == report.primary_kpis.total_intervention_cost
    )
    assert data["safety_status"] == "PASS"


@pytest.mark.asyncio
async def test_overview_empty_state() -> None:
    """AC-04: Test overview returns explicit empty state when no benchmark runs exist."""
    from apro.evaluation.persistence import EvaluationArtifactStore
    from apro.main import app

    empty_store = EvaluationArtifactStore()
    app.state.dashboard_service = DashboardService(
        eval_store=empty_store, allow_in_memory_for_testing=True
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/dashboard/overview")
        assert response.status_code == 200
        body = response.json()

        assert body["status"] == "empty"
        assert body["data"] is None
        assert "No benchmark run available" in body["message"]


@pytest.mark.asyncio
async def test_overview_query_by_run_id(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Test overview resolves specific benchmark run ID when requested."""
    report1 = generate_test_benchmark_report(
        run_id="run_spec_01",
        dataset_id="snap_spec_01",
        count=10,
        recovery_modulo=2,
    )
    report2 = generate_test_benchmark_report(
        run_id="run_spec_02",
        dataset_id="snap_spec_02",
        count=10,
        recovery_modulo=5,
    )
    await postgres_test_store.save_report(report1)
    await postgres_test_store.save_report(report2)

    res1 = await async_client.get(
        "/api/dashboard/overview?benchmark_run_id=run_spec_01"
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["latest_benchmark_run_id"] == "run_spec_01"
    assert res1.json()["data"]["recovery_rate"] == report1.primary_kpis.recovery_rate

    res2 = await async_client.get(
        "/api/dashboard/overview?benchmark_run_id=run_spec_02"
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["latest_benchmark_run_id"] == "run_spec_02"
    assert res2.json()["data"]["recovery_rate"] == report2.primary_kpis.recovery_rate
