"""Evaluation persistence and benchmark artifact repository."""

from typing import Any

from apro.evaluation.exceptions import EvaluationPersistenceError
from apro.evaluation.models import BenchmarkReport


class EvaluationArtifactStore:
    """In-memory persistence store for evaluation artifacts."""

    def __init__(self) -> None:
        self._reports: dict[str, BenchmarkReport] = {}
        self._runs: dict[str, dict[str, Any]] = {}

    def save_report(self, report: BenchmarkReport) -> str:
        """Persist a benchmark report strictly in the evaluation plane."""
        try:
            self._reports[report.report_id] = report
            self._runs[report.benchmark_run_id] = {
                "report_id": report.report_id,
                "benchmark_run_id": report.benchmark_run_id,
                "dataset_id": report.dataset_id,
                "created_at": report.created_at,
                "recovery_rate": report.primary_kpis.recovery_rate,
                "net_recovered_revenue": report.primary_kpis.net_recovered_revenue,
            }
            return report.report_id
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

    def list_reports(self) -> list[dict[str, Any]]:
        """List summary metadata for all persisted evaluation reports."""
        return list(self._runs.values())
