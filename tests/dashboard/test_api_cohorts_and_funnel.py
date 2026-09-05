"""Tests for GET /api/dashboard/cohorts and GET /api/dashboard/funnel endpoints."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_funnel_and_cohorts_endpoints(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-46, AC-48, AC-53: Test funnel stages and cohort breakdowns."""
    report = generate_test_benchmark_report(
        run_id="run_cohorts_01",
        dataset_id="snap_cohorts_01",
        count=30,
    )
    await postgres_test_store.save_report(report)

    # Test Funnel
    res_funnel = await async_client.get("/api/dashboard/funnel")
    assert res_funnel.status_code == 200
    body_funnel = res_funnel.json()
    assert body_funnel["status"] == "ok"
    assert len(body_funnel["data"]) == 6
    stages = [s["stage_name"] for s in body_funnel["data"]]
    assert stages == [
        "Eligible",
        "Attempted",
        "Pending",
        "Recovered",
        "Stopped",
        "Escalated",
    ]

    # Test Cohorts
    res_cohorts = await async_client.get("/api/dashboard/cohorts")
    assert res_cohorts.status_code == 200
    body_cohorts = res_cohorts.json()
    assert body_cohorts["status"] == "ok"
    assert len(body_cohorts["cohorts"]) >= 1
    dims = {c["dimension"] for c in body_cohorts["cohorts"]}
    assert (
        "failure_category" in dims
        or "amount_bucket" in dims
        or "payment_method" in dims
    )


@pytest.mark.asyncio
async def test_funnel_missing_values_returns_none_instead_of_fallback(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Requirement 4: When attempted/stopped are not reported, count/percentage are None, not inferred."""
    report = generate_test_benchmark_report(
        run_id="run_funnel_missing",
        dataset_id="snap_funnel_missing",
        count=50,
    )
    # Ensure no case_counts and empty terminal_disposition_mix
    primary_kpis = report.primary_kpis.model_copy(
        update={"terminal_disposition_mix": {}}
    )
    report = report.model_copy(
        update={
            "case_counts": {},
            "primary_kpis": primary_kpis,
        }
    )
    await postgres_test_store.save_report(report)

    res = await async_client.get(
        "/api/dashboard/funnel?benchmark_run_id=run_funnel_missing"
    )
    assert res.status_code == 200
    data = res.json()["data"]

    stage_map = {s["stage_name"]: s for s in data}
    assert stage_map["Eligible"]["count"] == 50
    assert stage_map["Eligible"]["percentage"] == 100.0

    # Non-authoritative stages MUST NOT fall back to eligible or eligible - recovered
    assert stage_map["Attempted"]["count"] is None
    assert stage_map["Attempted"]["percentage"] is None
    assert stage_map["Pending"]["count"] is None
    assert stage_map["Stopped"]["count"] is None
    assert stage_map["Escalated"]["count"] is None
