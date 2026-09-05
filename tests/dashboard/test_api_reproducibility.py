"""Tests for GET /api/dashboard/reproducibility/{benchmark_run_id} endpoint."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_reproducibility_manifest(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-39, AC-40, AC-44: Test reproducibility metadata returns identical hashes and provenance."""
    report = generate_test_benchmark_report(
        run_id="run_repro_01",
        dataset_id="snap_repro_01",
        count=20,
    )
    await postgres_test_store.save_report(report)

    res1 = await async_client.get("/api/dashboard/reproducibility/run_repro_01")
    assert res1.status_code == 200
    body1 = res1.json()

    res2 = await async_client.get("/api/dashboard/reproducibility/run_repro_01")
    assert res2.status_code == 200
    body2 = res2.json()

    assert body1["report_hash"] == report.report_hash
    assert body1["snapshot_hash"] == report.snapshot_hash
    assert body1["benchmark_run_id"] == "run_repro_01"
    # Idempotent reproducibility
    assert body1["report_hash"] == body2["report_hash"]
    assert body1["snapshot_hash"] == body2["snapshot_hash"]


@pytest.mark.asyncio
async def test_reproducibility_unknown_run_yields_404(
    async_client: httpx.AsyncClient,
) -> None:
    """Test unknown benchmark_run_id returns 404."""
    res = await async_client.get("/api/dashboard/reproducibility/run_nonexistent_999")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_reproducibility_cost_model_matches_persisted_config(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-40 / Requirement 4: Test cost model values match persisted run configuration exactly."""
    from apro.evaluation.config import CostModelConfig, EvaluationConfig

    custom_cost = CostModelConfig(
        retry_cost=150,
        payment_link_cost=275,
        outreach_cost=600,
        escalation_cost=1250,
        stop_cost=25,
    )
    custom_cfg = EvaluationConfig(cost_model=custom_cost)

    report = generate_test_benchmark_report(
        run_id="run_custom_cost_01",
        dataset_id="snap_custom_cost_01",
        count=15,
        config=custom_cfg,
    )
    await postgres_test_store.save_report(report)

    res = await async_client.get("/api/dashboard/reproducibility/run_custom_cost_01")
    assert res.status_code == 200
    body = res.json()

    cost_model = body["cost_model"]
    assert cost_model["retry_cost"] == 150
    assert cost_model["payment_link_cost"] == 275
    assert cost_model["outreach_cost"] == 600
    assert cost_model["escalation_cost"] == 1250
    assert cost_model["stop_cost"] == 25
