import json

import httpx
import pytest

from apro.adversarial.assertions import assert_zero_secret_leakage
from apro.adversarial.enums import CANONICAL_SENTINELS, AttackDisposition
from apro.adversarial.executor import (
    AdversarialAttackExecutor,
    _build_adversarial_benchmark_report,
)
from apro.adversarial.generators import generate_secret_exfiltration_cases
from apro.audit.sanitization import TelemetrySanitizer
from apro.dashboard.service import DashboardService
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from apro.main import app


@pytest.mark.asyncio
async def test_scenario_10_secret_exfiltration_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 10: Secret exfiltration cases are safely contained and redacted."""
    cases = generate_secret_exfiltration_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.CONTAINED


@pytest.mark.asyncio
async def test_scenario_10_five_canonical_sentinels_redacted(
    attack_eval_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Scenario 10: All 5 canonical sentinels persisted in DB are never leaked in API outputs or exports."""
    app.state.dashboard_service = DashboardService(
        eval_store=attack_eval_store, allow_in_memory_for_testing=False
    )
    transport = httpx.ASGITransport(app=app)

    persisted_count = 0
    eval_safe_count = 0
    dashboard_safe_count = 0
    leak_count = 0

    endpoints_template = [
        "/api/dashboard/overview?benchmark_run_id={run_id}",
        "/api/dashboard/reproducibility/{run_id}",
        "/api/dashboard/funnel?benchmark_run_id={run_id}",
        "/api/dashboard/benchmarks?benchmark_run_id={run_id}",
        "/api/dashboard/prediction-quality?benchmark_run_id={run_id}",
        "/api/dashboard/adaptive?benchmark_run_id={run_id}",
        "/api/dashboard/safety?benchmark_run_id={run_id}",
        "/api/dashboard/cohorts?benchmark_run_id={run_id}",
        "/api/dashboard/runs",
    ]

    for idx, sentinel in enumerate(CANONICAL_SENTINELS):
        run_id = f"run_sentinel_canonical_{idx}"
        rep = _build_adversarial_benchmark_report(
            run_id=run_id,
            dataset_id=f"snap_sentinel_{idx}",
            count=3,
        )
        rep.reproducibility_metadata["secret_key"] = sentinel
        rep.reproducibility_metadata["auth_token"] = f"Bearer {sentinel}"
        rep.reproducibility_metadata["db_pass"] = sentinel
        await attack_eval_store.save_report(rep)
        persisted_count += 1

        # 1. Verify evaluation artifact representation
        persisted_rep = await attack_eval_store.get_report_by_run_id(run_id)
        assert persisted_rep is not None
        eval_export = json.dumps(
            TelemetrySanitizer.sanitize(persisted_rep.reproducibility_metadata)
        )
        if sentinel not in eval_export:
            eval_safe_count += 1
        else:
            leak_count += 1

        # 2. Verify all 9 dashboard endpoints with expected status 200 OK
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            responses = []
            for ep in endpoints_template:
                res = await client.get(ep.format(run_id=run_id))
                assert res.status_code == 200, (
                    f"Expected 200 OK for {ep}, got {res.status_code}"
                )
                responses.append(res.text)

            all_dashboard_text = "".join(responses)
            if sentinel not in all_dashboard_text:
                dashboard_safe_count += 1
            else:
                leak_count += 1

    assert persisted_count == 5
    assert eval_safe_count == 5
    assert dashboard_safe_count == 5
    assert_zero_secret_leakage(leaked_count=leak_count)
