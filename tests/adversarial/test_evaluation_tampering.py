"""Tests for Scenario 8: Evaluation / Benchmark Artifact Tampering and Immutability."""

from typing import Any

import pytest
from sqlalchemy import text

from apro.adversarial.assertions import assert_benchmark_immutability_enforced
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import (
    AdversarialAttackExecutor,
    _build_adversarial_benchmark_report,
)
from apro.adversarial.generators import generate_benchmark_tampering_cases
from apro.evaluation.exceptions import EvaluationPersistenceError
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore


@pytest.mark.asyncio
async def test_scenario_8_benchmark_tampering_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 8: Benchmark tampering cases are blocked."""
    cases = generate_benchmark_tampering_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.BLOCKED


@pytest.mark.asyncio
async def test_scenario_8_benchmark_sql_triggers(
    attack_db_session_factory: Any,
    attack_eval_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Scenario 8: Direct SQL UPDATE and DELETE on evaluation_benchmark_reports are rejected by PostgreSQL triggers."""
    run_id = "run_pg_bench_immutability_001"
    report = _build_adversarial_benchmark_report(
        run_id=run_id, dataset_id="snap_b1", count=5
    )
    await attack_eval_store.save_report(report)
    original_hash = report.report_hash

    # Attempt direct SQL UPDATE
    update_blocked = False
    try:
        async with attack_db_session_factory() as session, session.begin():
            await session.execute(
                text(
                    "UPDATE evaluation_benchmark_reports SET recovery_rate = 1.0, report_hash = 'tampered' WHERE benchmark_run_id = :id;"
                ),
                {"id": run_id},
            )
    except Exception as exc:
        err_msg = str(exc).lower()
        if (
            "evaluation_benchmark_reports is append-only" in err_msg
            or "trg_evaluation_benchmark_reports_immutability" in err_msg
        ):
            update_blocked = True

    assert update_blocked is True

    # Verify report row is unchanged after UPDATE attempt
    loaded_after_update = await attack_eval_store.get_report_by_run_id(run_id)
    assert loaded_after_update is not None
    assert loaded_after_update.report_hash == original_hash

    # Attempt direct SQL DELETE
    delete_blocked = False
    try:
        async with attack_db_session_factory() as session, session.begin():
            await session.execute(
                text(
                    "DELETE FROM evaluation_benchmark_reports WHERE benchmark_run_id = :id;"
                ),
                {"id": run_id},
            )
    except Exception as exc:
        err_msg = str(exc).lower()
        if (
            "evaluation_benchmark_reports is append-only" in err_msg
            or "trg_evaluation_benchmark_reports_immutability" in err_msg
        ):
            delete_blocked = True

    assert delete_blocked is True

    # Verify report row still exists and is unchanged after DELETE attempt
    loaded_after_delete = await attack_eval_store.get_report_by_run_id(run_id)
    assert loaded_after_delete is not None
    assert loaded_after_delete.report_hash == original_hash

    assert_benchmark_immutability_enforced(
        attempted_updates=1,
        attempted_deletes=1,
        blocked_updates=1,
        blocked_deletes=1,
    )


@pytest.mark.asyncio
async def test_scenario_8_conflicting_report_overwrite_rejected(
    attack_eval_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """Scenario 8: Attempting to save a conflicting report with the same run_id raises EvaluationPersistenceError."""
    run_id = "run_conflict_persistence_test"
    report_orig = _build_adversarial_benchmark_report(
        run_id=run_id, dataset_id="snap_orig", count=5, seed=1
    )
    await attack_eval_store.save_report(report_orig)

    # Conflicting report with different content
    report_conflict = _build_adversarial_benchmark_report(
        run_id=run_id, dataset_id="snap_tampered", count=5, seed=2
    )

    with pytest.raises(EvaluationPersistenceError):
        await attack_eval_store.save_report(report_conflict)

    # Verify original report is unchanged
    loaded = await attack_eval_store.get_report_by_run_id(run_id)
    assert loaded is not None
    assert loaded.report_hash == report_orig.report_hash
