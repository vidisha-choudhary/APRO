"""FastAPI read-only dashboard API router (Phase 16)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apro.dashboard.schemas import (
    AdaptiveRecoveryResponse,
    BenchmarkRunListResponse,
    BenchmarksResponse,
    CaseDetailResponse,
    CaseListResponse,
    CaseTimelineResponse,
    CohortsResponse,
    FunnelResponse,
    OverviewResponse,
    PredictionQualityResponse,
    ReproducibilityResponse,
    ReviewerQuestionsResponse,
    SafetyResponse,
)
from apro.dashboard.service import DashboardService
from apro.evaluation.exceptions import EvaluationPersistenceError

logger = logging.getLogger("apro.dashboard.router")

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_dashboard_service(request: Request) -> DashboardService:
    """Dependency provider for DashboardService."""
    if (
        hasattr(request.app.state, "dashboard_service")
        and request.app.state.dashboard_service
    ):
        return request.app.state.dashboard_service  # type: ignore[no-any-return]

    # Fallback to application session factory if available
    session_factory = getattr(request.app.state, "session_factory", None)
    try:
        from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore

        store = (
            PostgreSQLEvaluationArtifactStore(session_factory=session_factory)
            if session_factory
            else PostgreSQLEvaluationArtifactStore()
        )
        return DashboardService(eval_store=store)
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL evaluation repository: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL evaluation repository unavailable.",
        ) from e


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> OverviewResponse:
    """Get high-level operational recovery KPIs and summary health."""
    try:
        return await service.get_overview(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/funnel", response_model=FunnelResponse)
async def get_funnel(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> FunnelResponse:
    """Get case funnel stages and conversion metrics."""
    try:
        return await service.get_funnel(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/benchmarks", response_model=BenchmarksResponse)
async def get_benchmarks(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> BenchmarksResponse:
    """Get baseline comparison metrics, confidence intervals, and p-values."""
    try:
        return await service.get_benchmarks(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/prediction-quality", response_model=PredictionQualityResponse)
async def get_prediction_quality(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> PredictionQualityResponse:
    """Get recovery prediction calibration curves and classification quality."""
    try:
        return await service.get_prediction_quality(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/adaptive", response_model=AdaptiveRecoveryResponse)
async def get_adaptive(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> AdaptiveRecoveryResponse:
    """Get adaptive recovery cycle distributions and re-evaluation lift."""
    try:
        return await service.get_adaptive(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/safety", response_model=SafetyResponse)
async def get_safety(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> SafetyResponse:
    """Get safety invariant checks, violation counts, and overall safety status."""
    try:
        return await service.get_safety(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/cohorts", response_model=CohortsResponse)
async def get_cohorts(
    benchmark_run_id: Annotated[
        str | None, Query(description="Optional benchmark run ID")
    ] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> CohortsResponse:
    """Get disaggregated segment breakdowns across failure categories."""
    try:
        return await service.get_cohorts(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query()] = None,
    service: DashboardService = Depends(get_dashboard_service),
) -> CaseListResponse:
    """List paginated recovery cases for the Case Explorer."""
    try:
        return await service.list_cases(
            page=page, page_size=page_size, status=status_filter, search=search
        )
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    case_id: str,
    service: DashboardService = Depends(get_dashboard_service),
) -> CaseDetailResponse:
    """Reconstruct full case audit provenance via Phase 14."""
    try:
        return await service.get_case_detail(case_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/cases/{case_id}/timeline", response_model=CaseTimelineResponse)
async def get_case_timeline(
    case_id: str,
    service: DashboardService = Depends(get_dashboard_service),
) -> CaseTimelineResponse:
    """Get causal chronological audit events for a specific case."""
    try:
        return await service.get_case_timeline(case_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get(
    "/cases/{case_id}/reviewer-questions",
    response_model=ReviewerQuestionsResponse,
)
async def get_reviewer_questions(
    case_id: str,
    service: DashboardService = Depends(get_dashboard_service),
) -> ReviewerQuestionsResponse:
    """Get answers to the seven authoritative reviewer questions (Q1–Q7)."""
    try:
        return await service.get_reviewer_questions(case_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get(
    "/reproducibility/{benchmark_run_id}",
    response_model=ReproducibilityResponse,
)
async def get_reproducibility(
    benchmark_run_id: str,
    service: DashboardService = Depends(get_dashboard_service),
) -> ReproducibilityResponse:
    """Get complete provenance metadata, dataset hashes, and configurations."""
    try:
        return await service.get_reproducibility(benchmark_run_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/runs", response_model=BenchmarkRunListResponse)
async def list_benchmark_runs(
    service: DashboardService = Depends(get_dashboard_service),
) -> BenchmarkRunListResponse:
    """List all persisted benchmark runs for the benchmark-run selector."""
    try:
        return await service.list_benchmark_runs()
    except EvaluationPersistenceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
