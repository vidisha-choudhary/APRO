"""Tests for secret leakage prevention and security sentinels in Dashboard API."""

import httpx
import pytest

from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_sentinel_secrets_not_leaked(
    async_client: httpx.AsyncClient,
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-54 through AC-60 / Requirement 8: Injected sentinels persisted to PostgreSQL never appear in dashboard responses."""
    sentinels = [
        "sentinel_dashboard_secret_87654321",
        "sentinel_card_number_4111222233334444",
        "sentinel_auth_header_bearer_xyz999",
        "sentinel_db_password_topsecret_2026",
        "sentinel_raw_provider_payload",
    ]

    report = generate_test_benchmark_report(
        run_id="run_sec_sentinel_01",
        dataset_id="snap_sec_sentinel_01",
        count=10,
    )

    # Injected sentinels persisted to PostgreSQL
    report.reproducibility_metadata["internal_secret_api_key"] = sentinels[0]
    report.reproducibility_metadata["pan_card_holder"] = sentinels[1]
    report.reproducibility_metadata["auth_bearer_token"] = sentinels[2]
    report.reproducibility_metadata["db_password_hash"] = sentinels[3]
    report.reproducibility_metadata["provider_raw_response"] = sentinels[4]

    # Persist genuine report with injected sentinels to isolated PostgreSQL storage
    await postgres_test_store.save_report(report)

    endpoints = [
        "/api/dashboard/overview?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/funnel?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/benchmarks?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/prediction-quality?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/adaptive?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/safety?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/cohorts?benchmark_run_id=run_sec_sentinel_01",
        "/api/dashboard/cases",
        "/api/dashboard/reproducibility/run_sec_sentinel_01",
    ]

    for ep in endpoints:
        res = await async_client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} failed: {res.text}"
        text = res.text
        for s in sentinels:
            assert s not in text, (
                f"Security sentinel '{s}' found in response from {ep}!"
            )
        assert "postgres_local_dev" not in text
        assert "postgresql://" not in text
