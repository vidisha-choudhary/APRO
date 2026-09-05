"""Mandatory backend restart persistence and durability test."""

import httpx
import pytest

from apro.dashboard.service import DashboardService
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from apro.main import app
from apro.persistence.database import get_async_engine, get_session_factory
from tests.dashboard.conftest import generate_test_benchmark_report


@pytest.mark.asyncio
async def test_backend_restart_durability_and_hash_stability() -> None:
    """Test that benchmark reports survive process/engine disposal and maintain identical values & report_hash."""
    import os

    from apro.config import settings

    db_url = os.environ.get("POSTGRES_TEST_URL") or settings.DATABASE_URL

    # 1. Initialize engine 1 and save report
    engine1 = get_async_engine(db_url)
    factory1 = get_session_factory(engine1)
    store1 = PostgreSQLEvaluationArtifactStore(session_factory=factory1)

    report1 = generate_test_benchmark_report(
        run_id="run_restart_01",
        dataset_id="snap_restart_01",
        count=25,
        recovery_modulo=2,
        amount=75000,
        seed=123,
    )
    await store1.save_report(report1)

    app.state.dashboard_service = DashboardService(eval_store=store1)
    transport1 = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport1, base_url="http://test"
    ) as client1:
        res1 = await client1.get(
            "/api/dashboard/overview?benchmark_run_id=run_restart_01"
        )
        assert res1.status_code == 200
        body1 = res1.json()
        hash1 = body1["metadata"]["report_hash"]
        kpis1 = body1["data"]

    # 2. Simulate complete backend restart: dispose engine 1 and clear app state
    await engine1.dispose()
    app.state.dashboard_service = None
    app.state.session_factory = None

    # 3. Recreate fresh engine 2, fresh store 2, and fresh client
    engine2 = get_async_engine(db_url)
    factory2 = get_session_factory(engine2)
    store2 = PostgreSQLEvaluationArtifactStore(session_factory=factory2)
    app.state.dashboard_service = DashboardService(eval_store=store2)
    transport2 = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport2, base_url="http://test"
    ) as client2:
        # 4. Read report again after restart
        res2 = await client2.get(
            "/api/dashboard/overview?benchmark_run_id=run_restart_01"
        )
        assert res2.status_code == 200
        body2 = res2.json()
        hash2 = body2["metadata"]["report_hash"]
        kpis2 = body2["data"]

        # 5. Assert durability: identical business values and identical report_hash
        assert hash1 == hash2 == report1.report_hash
        assert (
            kpis1["recovery_rate"]
            == kpis2["recovery_rate"]
            == report1.primary_kpis.recovery_rate
        )
        assert kpis1["gross_recovered_revenue"] == kpis2["gross_recovered_revenue"]
        assert kpis1["net_recovered_revenue"] == kpis2["net_recovered_revenue"]
        assert kpis1["total_intervention_cost"] == kpis2["total_intervention_cost"]

        # 6. Add a second run and verify run 1 is still preserved and retrievable
        report2 = generate_test_benchmark_report(
            run_id="run_restart_02",
            dataset_id="snap_restart_02",
            count=25,
            recovery_modulo=1,
            amount=90000,
            seed=456,
        )
        await store2.save_report(report2)

        res_hist = await client2.get(
            "/api/dashboard/overview?benchmark_run_id=run_restart_01"
        )
        assert res_hist.status_code == 200
        assert res_hist.json()["data"]["recovery_rate"] == kpis1["recovery_rate"]

    await engine2.dispose()


@pytest.mark.asyncio
async def test_database_level_benchmark_immutability_triggers(
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> None:
    """AC-43 / Requirement 11: Assert PostgreSQL triggers reject direct SQL UPDATE and DELETE on evaluation_benchmark_reports."""
    import os

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from apro.config import settings

    report = generate_test_benchmark_report(
        run_id="run_immut_trg_01",
        dataset_id="snap_immut_01",
        count=10,
    )
    await postgres_test_store.save_report(report)

    db_url = os.environ.get("POSTGRES_TEST_URL") or settings.DATABASE_URL
    engine = get_async_engine(db_url)
    factory = get_session_factory(engine)

    # 1. Direct SQL UPDATE MUST FAIL via trigger
    async with factory() as session:
        with pytest.raises(DBAPIError) as exc_info_update:
            await session.execute(
                text(
                    "UPDATE evaluation_benchmark_reports "
                    "SET recovery_rate = 0.999 "
                    "WHERE benchmark_run_id = 'run_immut_trg_01'"
                )
            )
            await session.commit()
        assert "is append-only" in str(exc_info_update.value)

    # 2. Direct SQL DELETE MUST FAIL via trigger
    async with factory() as session:
        with pytest.raises(DBAPIError) as exc_info_delete:
            await session.execute(
                text(
                    "DELETE FROM evaluation_benchmark_reports "
                    "WHERE benchmark_run_id = 'run_immut_trg_01'"
                )
            )
            await session.commit()
        assert "is append-only" in str(exc_info_delete.value)

    await engine.dispose()
