"""Mandatory live dynamic value propagation test through the real PostgreSQL storage path."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_live_value_propagation_through_postgresql_persistence(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-42, AC-43: Test that persisting a new benchmark run dynamically updates latest dashboard values without mutating V1."""
    # 1. Create and persist benchmark run V1
    report_v1 = generate_test_benchmark_report(
        run_id="run_live_v1",
        dataset_id="snap_live_v1",
        count=30,
        recovery_modulo=2,  # 50% recovery
        amount=50000,
        seed=42,
    )
    await postgres_test_store.save_report(report_v1)

    # 2. Query dashboard overview
    res_v1 = await async_client.get("/api/dashboard/overview")
    assert res_v1.status_code == 200
    data_v1 = res_v1.json()["data"]
    v1_rec_rate = data_v1["recovery_rate"]
    v1_net_rev = data_v1["net_recovered_revenue"]
    assert v1_rec_rate == report_v1.primary_kpis.recovery_rate

    # 3. Create and persist NEW legitimate benchmark run V2 (higher recovery, different amounts)
    report_v2 = generate_test_benchmark_report(
        run_id="run_live_v2",
        dataset_id="snap_live_v2",
        count=30,
        recovery_modulo=1,  # 100% recovery
        amount=150000,
        seed=99,
    )
    await postgres_test_store.save_report(report_v2)

    # 4. Query dashboard overview again (latest run selection)
    res_v2 = await async_client.get("/api/dashboard/overview")
    assert res_v2.status_code == 200
    data_v2 = res_v2.json()["data"]
    v2_rec_rate = data_v2["recovery_rate"]
    v2_net_rev = data_v2["net_recovered_revenue"]

    # 5. Assert V2 reflects the changed persisted truth and V1 != V2
    assert v2_rec_rate == report_v2.primary_kpis.recovery_rate
    assert v1_rec_rate != v2_rec_rate
    assert v1_net_rev != v2_net_rev

    # 6. Verify historical run V1 is preserved immutably and retrievable
    res_hist_v1 = await async_client.get(
        "/api/dashboard/overview?benchmark_run_id=run_live_v1"
    )
    assert res_hist_v1.status_code == 200
    data_hist_v1 = res_hist_v1.json()["data"]
    assert data_hist_v1["recovery_rate"] == v1_rec_rate
    assert data_hist_v1["net_recovered_revenue"] == v1_net_rev
