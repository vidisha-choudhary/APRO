"""Integration test for consistent benchmark_run_id propagation across all benchmark-derived views."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_benchmark_run_id_consistency_propagation(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Test that selecting Run A or Run B consistently propagates across all benchmark views."""
    report_a = generate_test_benchmark_report(
        run_id="run_consistency_A",
        dataset_id="snap_consistency_A",
        count=20,
        recovery_modulo=2,
        amount=50000,
        seed=101,
    )
    report_b = generate_test_benchmark_report(
        run_id="run_consistency_B",
        dataset_id="snap_consistency_B",
        count=20,
        recovery_modulo=4,
        amount=80000,
        seed=202,
    )

    await postgres_test_store.save_report(report_a)
    await postgres_test_store.save_report(report_b)

    # 1. Query Run A across all views
    endpoints = [
        "/api/dashboard/overview",
        "/api/dashboard/benchmarks",
        "/api/dashboard/prediction-quality",
        "/api/dashboard/adaptive",
        "/api/dashboard/safety",
        "/api/dashboard/cohorts",
    ]

    for ep in endpoints:
        res_a = await async_client.get(f"{ep}?benchmark_run_id=run_consistency_A")
        assert res_a.status_code == 200
        body_a = res_a.json()
        assert body_a["metadata"]["benchmark_run_id"] == "run_consistency_A"
        assert body_a["metadata"]["report_hash"] == report_a.report_hash

    # 2. Query Run B across all views
    for ep in endpoints:
        res_b = await async_client.get(f"{ep}?benchmark_run_id=run_consistency_B")
        assert res_b.status_code == 200
        body_b = res_b.json()
        assert body_b["metadata"]["benchmark_run_id"] == "run_consistency_B"
        assert body_b["metadata"]["report_hash"] == report_b.report_hash

    # 3. Query unknown run ID across all views: must return 404, never fallback to latest
    for ep in endpoints:
        res_unk = await async_client.get(f"{ep}?benchmark_run_id=run_unknown_9999")
        assert res_unk.status_code == 404, (
            f"Endpoint {ep} did not return 404 for unknown run ID"
        )
