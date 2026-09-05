"""Tests for Scenario 9: Reviewer Dashboard Read-Only and Abuse Resistance."""

import httpx
import pytest

from apro.adversarial.assertions import assert_dashboard_read_only_enforced
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_dashboard_abuse_cases
from apro.dashboard.service import DashboardService
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from apro.main import app
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_scenario_9_dashboard_abuse_cases(
    adversarial_executor: AdversarialAttackExecutor,
    attack_eval_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Scenario 9: Dashboard abuse cases (POST/PUT/DELETE/SQLi) are blocked."""
    # Seed a baseline benchmark report
    rep = generate_test_benchmark_report(
        run_id="run_dash_test_001", dataset_id="snap_dash_001", count=5
    )
    await attack_eval_store.save_report(rep)

    cases = generate_dashboard_abuse_cases(seed=1701, count=10)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.BLOCKED


@pytest.mark.asyncio
async def test_scenario_9_mutating_http_methods_rejected(
    attack_eval_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Scenario 9: All mutating HTTP methods (POST, PUT, DELETE, PATCH) return 405 Method Not Allowed."""
    app.state.dashboard_service = DashboardService(
        eval_store=attack_eval_store, allow_in_memory_for_testing=False
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        endpoints = [
            "/api/dashboard/overview",
            "/api/dashboard/funnel",
            "/api/dashboard/benchmarks",
            "/api/dashboard/prediction-quality",
            "/api/dashboard/adaptive",
            "/api/dashboard/safety",
            "/api/dashboard/cohorts",
            "/api/dashboard/cases",
            "/api/dashboard/runs",
            "/api/dashboard/reproducibility/run_dash_test_001",
        ]

        attempted_mutations = 0
        blocked_mutations = 0

        for ep in endpoints:
            for method in ["POST", "PUT", "DELETE", "PATCH"]:
                attempted_mutations += 1
                res = await client.request(
                    method, ep, json={"tamper": True} if method != "DELETE" else None
                )
                if res.status_code == 405:
                    blocked_mutations += 1

        assert_dashboard_read_only_enforced(
            attempted_mutations=attempted_mutations,
            blocked_mutations=blocked_mutations,
        )
