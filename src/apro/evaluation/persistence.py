"""Evaluation persistence and benchmark artifact repository."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from apro.evaluation.exceptions import EvaluationPersistenceError
from apro.evaluation.models import BenchmarkReport
from apro.persistence.models import EvaluationBenchmarkReportModel


class EvaluationArtifactStore:
    """In-memory persistence store for isolated offline evaluation tests."""

    def __init__(self) -> None:
        self._reports: dict[str, BenchmarkReport] = {}
        self._runs: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []

    def save_report(self, report: BenchmarkReport) -> str:
        """Persist a benchmark report append-only strictly in the evaluation plane."""
        try:
            if report.benchmark_run_id in self._runs:
                existing_report_id = self._runs[report.benchmark_run_id]["report_id"]
                existing = self._reports.get(existing_report_id)
                if existing and existing.report_hash == report.report_hash:
                    return str(existing_report_id)
                raise EvaluationPersistenceError(
                    f"Conflicting benchmark report for run_id "
                    f"{report.benchmark_run_id}: cannot mutate immutable benchmark run."
                )

            self._reports[report.report_id] = report
            self._runs[report.benchmark_run_id] = {
                "report_id": report.report_id,
                "benchmark_run_id": report.benchmark_run_id,
                "dataset_id": report.dataset_id,
                "dataset_version": report.dataset_version,
                "report_hash": report.report_hash,
                "created_at": report.created_at,
                "recovery_rate": report.primary_kpis.recovery_rate,
                "gross_recovered_amount": report.primary_kpis.gross_recovered_amount,
                "net_recovered_revenue": report.primary_kpis.net_recovered_revenue,
                "total_intervention_cost": report.primary_kpis.total_intervention_cost,
                "is_synthetic_demo": "demo" in report.dataset_id.lower(),
            }
            self._order.append(report.benchmark_run_id)
            return report.report_id
        except EvaluationPersistenceError:
            raise
        except Exception as e:
            raise EvaluationPersistenceError(
                f"Failed to persist benchmark report: {e}"
            ) from e

    def get_report(self, report_id: str) -> BenchmarkReport | None:
        """Retrieve a persisted benchmark report by report_id."""
        return self._reports.get(report_id)

    def get_report_by_run_id(self, benchmark_run_id: str) -> BenchmarkReport | None:
        """Retrieve a persisted benchmark report by benchmark_run_id."""
        run_info = self._runs.get(benchmark_run_id)
        if run_info:
            return self.get_report(run_info["report_id"])
        return None

    def get_latest_report(self) -> BenchmarkReport | None:
        """Retrieve the latest immutable benchmark report."""
        if not self._order:
            return None
        latest_run_id = self._order[-1]
        return self.get_report_by_run_id(latest_run_id)

    def list_reports(self) -> list[dict[str, Any]]:
        """List summary metadata for all persisted evaluation reports."""
        return [self._runs[run_id] for run_id in reversed(self._order)]


class PostgreSQLEvaluationArtifactStore:
    """PostgreSQL evaluation repository for immutable benchmark reports."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        if session_factory is not None:
            self._session_factory = session_factory
        elif engine is not None:
            self._session_factory = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
        else:
            import os

            from apro.config import settings
            from apro.persistence.database import get_async_engine, get_session_factory

            db_url = settings.DATABASE_URL or os.environ.get("POSTGRES_TEST_URL")
            eng = get_async_engine(db_url)
            self._session_factory = get_session_factory(eng)

    async def save_report(self, report: BenchmarkReport) -> str:
        """Persist a benchmark report immutably in PostgreSQL."""
        try:
            payload = json.loads(report.model_dump_json())
            try:
                created_dt = datetime.fromisoformat(
                    report.created_at.replace("Z", "+00:00")
                )
            except Exception:
                created_dt = datetime.now(UTC)

            async with self._session_factory() as session, session.begin():
                stmt = select(EvaluationBenchmarkReportModel).where(
                    EvaluationBenchmarkReportModel.benchmark_run_id
                    == report.benchmark_run_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing is not None:
                    if existing.report_hash == report.report_hash:
                        return existing.report_id
                    raise EvaluationPersistenceError(
                        f"Conflicting benchmark report for run_id "
                        f"'{report.benchmark_run_id}': existing hash "
                        f"'{existing.report_hash}' != new hash '{report.report_hash}'."
                    )

                is_demo = (
                    "demo" in report.dataset_id.lower()
                    or "synthetic" in report.dataset_id.lower()
                )

                seed = int(report.reproducibility_metadata.get("bootstrap_seed", 42))
                iters = int(
                    report.reproducibility_metadata.get("bootstrap_iterations", 1000)
                )

                model = EvaluationBenchmarkReportModel(
                    report_id=report.report_id,
                    benchmark_run_id=report.benchmark_run_id,
                    dataset_id=report.dataset_id,
                    dataset_version=report.dataset_version,
                    snapshot_hash=report.snapshot_hash,
                    evaluation_config_version=report.evaluation_config_version,
                    metric_schema_version=report.metric_schema_version,
                    code_revision=report.code_revision,
                    bootstrap_seed=seed,
                    bootstrap_iterations=iters,
                    report_hash=report.report_hash,
                    recovery_rate=report.primary_kpis.recovery_rate,
                    gross_recovered_amount=report.primary_kpis.gross_recovered_amount,
                    net_recovered_revenue=report.primary_kpis.net_recovered_revenue,
                    total_intervention_cost=report.primary_kpis.total_intervention_cost,
                    is_synthetic_demo=is_demo,
                    report_payload=payload,
                    created_at=created_dt,
                )
                session.add(model)

            return report.report_id
        except EvaluationPersistenceError:
            raise
        except Exception as e:
            raise EvaluationPersistenceError(
                f"Failed to persist benchmark report to PostgreSQL: {e}"
            ) from e

    async def get_report(self, report_id: str) -> BenchmarkReport | None:
        """Retrieve a persisted benchmark report by report_id."""
        try:
            async with self._session_factory() as session:
                stmt = select(EvaluationBenchmarkReportModel).where(
                    EvaluationBenchmarkReportModel.report_id == report_id
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if model is None:
                    return None
                return BenchmarkReport.model_validate(model.report_payload)
        except Exception as e:
            raise EvaluationPersistenceError(
                f"Failed to load benchmark report {report_id} from PostgreSQL: {e}"
            ) from e

    async def get_report_by_run_id(
        self, benchmark_run_id: str
    ) -> BenchmarkReport | None:
        """Retrieve a persisted benchmark report by benchmark_run_id."""
        try:
            async with self._session_factory() as session:
                stmt = select(EvaluationBenchmarkReportModel).where(
                    EvaluationBenchmarkReportModel.benchmark_run_id == benchmark_run_id
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if model is None:
                    return None
                return BenchmarkReport.model_validate(model.report_payload)
        except Exception as e:
            raise EvaluationPersistenceError(
                f"Failed to load benchmark report for run_id {benchmark_run_id}: {e}"
            ) from e

    async def get_latest_report(self) -> BenchmarkReport | None:
        """Retrieve the latest immutable benchmark report ordered by created_at DESC."""
        try:
            async with self._session_factory() as session:
                stmt = (
                    select(EvaluationBenchmarkReportModel)
                    .order_by(EvaluationBenchmarkReportModel.created_at.desc())
                    .limit(1)
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if model is None:
                    return None
                return BenchmarkReport.model_validate(model.report_payload)
        except Exception as e:
            raise EvaluationPersistenceError(
                f"Failed to load latest benchmark report from PostgreSQL: {e}"
            ) from e

    async def list_reports(self, limit: int = 50) -> list[dict[str, Any]]:
        """List summary metadata for all persisted evaluation reports."""
        try:
            async with self._session_factory() as session:
                stmt = (
                    select(EvaluationBenchmarkReportModel)
                    .order_by(EvaluationBenchmarkReportModel.created_at.desc())
                    .limit(limit)
                )
                res = await session.execute(stmt)
                models = res.scalars().all()
                return [
                    {
                        "report_id": m.report_id,
                        "benchmark_run_id": m.benchmark_run_id,
                        "dataset_id": m.dataset_id,
                        "dataset_version": m.dataset_version,
                        "report_hash": m.report_hash,
                        "created_at": m.created_at.isoformat(),
                        "recovery_rate": m.recovery_rate,
                        "gross_recovered_amount": m.gross_recovered_amount,
                        "net_recovered_revenue": m.net_recovered_revenue,
                        "total_intervention_cost": m.total_intervention_cost,
                        "is_synthetic_demo": m.is_synthetic_demo,
                    }
                    for m in models
                ]
        except Exception as e:
            raise EvaluationPersistenceError(
                f"Failed to list benchmark reports from PostgreSQL: {e}"
            ) from e
