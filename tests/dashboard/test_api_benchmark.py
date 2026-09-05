"""Tests for GET /api/dashboard/benchmarks endpoint."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_benchmarks_baseline_comparisons(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-11, AC-18, AC-19, AC-20, AC-21: Test benchmark comparisons match Phase 15 output."""
    report = generate_test_benchmark_report(
        run_id="run_bench_01",
        dataset_id="snap_bench_01",
        count=30,
        recovery_modulo=2,
        amount=100000,
    )
    await postgres_test_store.save_report(report)

    response = await async_client.get("/api/dashboard/benchmarks")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert len(body["data"]) >= 4

    names = [b["baseline_name"] for b in body["data"]]
    assert "No Intervention" in names
    assert "Fixed Retry" in names
    assert "Payment Link" in names
    assert "Fixed Escalation" in names

    for item in body["data"]:
        assert item["comparison_label"] in [
            "BENCHMARK_ASSOCIATION",
            "BENCHMARK ASSOCIATION",
        ]
        assert item["delta_recovery_ci_95"] is not None
        assert len(item["delta_recovery_ci_95"]) == 2
        assert item["p_value"] is not None
        assert 0.0 <= item["p_value"] <= 1.0


@pytest.mark.asyncio
async def test_benchmarks_empty_state() -> None:
    """Test benchmarks returns empty list when no reports exist."""
    from apro.dashboard.service import DashboardService
    from apro.evaluation.persistence import EvaluationArtifactStore
    from apro.main import app

    empty_store = EvaluationArtifactStore()
    app.state.dashboard_service = DashboardService(
        eval_store=empty_store, allow_in_memory_for_testing=True
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/dashboard/benchmarks")
        assert res.status_code == 200
        assert res.json()["status"] == "empty"
        assert res.json()["data"] == []
