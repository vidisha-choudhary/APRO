"""Tests for GET /api/dashboard/safety endpoint."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_safety_metrics_endpoint(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-24: Test safety metrics reflect Phase 15 values and invariant statuses."""
    report = generate_test_benchmark_report(
        run_id="run_safety_01",
        dataset_id="snap_safety_01",
        count=20,
    )
    await postgres_test_store.save_report(report)

    response = await async_client.get("/api/dashboard/safety")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["overall_safety_status"] == "PASS"
    assert body["unsafe_dispatch_count"] == 0
    assert body["policy_bypass_count"] == 0
    assert body["stale_policy_reuse_count"] == 0
    assert len(body["invariants"]) >= 6
    assert all(inv["status"] == "PASS" for inv in body["invariants"])


@pytest.mark.asyncio
async def test_safety_empty_state() -> None:
    """Test safety endpoint returns NO_DATA status when no reports exist."""
    from apro.dashboard.service import DashboardService
    from apro.evaluation.persistence import EvaluationArtifactStore
    from apro.main import app

    empty_store = EvaluationArtifactStore()
    app.state.dashboard_service = DashboardService(
        eval_store=empty_store, allow_in_memory_for_testing=True
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/dashboard/safety")
        assert res.status_code == 200
        assert res.json()["overall_safety_status"] == "NO_DATA"
