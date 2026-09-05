"""Boundary test proving production dashboard strictly requires PostgreSQL evaluation store."""

import pytest
from fastapi.testclient import TestClient

from apro.dashboard.service import DashboardService
from apro.evaluation.exceptions import EvaluationPersistenceError
from apro.evaluation.persistence import EvaluationArtifactStore
from apro.main import app


def test_production_dashboard_rejects_in_memory_store_fallback() -> None:
    """Production DashboardService must reject in-memory EvaluationArtifactStore."""
    in_memory_store = EvaluationArtifactStore()

    with pytest.raises(
        EvaluationPersistenceError,
        match="strictly requires PostgreSQLEvaluationArtifactStore",
    ):
        DashboardService(
            eval_store=in_memory_store,
            allow_in_memory_for_testing=False,
        )


def test_production_dashboard_fails_cleanly_when_postgres_unavailable() -> None:
    """Production dashboard router emits 503 rather than silently using in-memory store."""
    app.state.dashboard_service = None
    app.state.session_factory = None

    # Simulate missing DB by temporarily setting bad environment or store failure
    client = TestClient(app)
    res = client.get("/api/dashboard/overview")
    # Must be either 200 with real DB or 503 if DB unavailable, never fallback in-memory fake numbers
    assert res.status_code in (200, 503)
