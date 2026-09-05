import {
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
} from "../types/dashboard";

export class DashboardApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = "/api/dashboard") {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, queryParams?: Record<string, string | number | undefined | null>): Promise<T> {
    const fullPath = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const targetUrl = new URL(fullPath, window.location.origin.startsWith("http") ? window.location.origin : "http://localhost:5173");

    if (queryParams) {
      Object.entries(queryParams).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          targetUrl.searchParams.set(key, String(value));
        }
      });
    }

    const response = await fetch(targetUrl.toString(), {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({ detail: response.statusText }));
      const error = new Error(errBody.detail || `Request failed with status ${response.status}`);
      (error as any).status = response.status;
      throw error;
    }

    return response.json();
  }

  async getOverview(benchmarkRunId?: string | null): Promise<OverviewResponse> {
    return this.request<OverviewResponse>("/overview", { benchmark_run_id: benchmarkRunId });
  }

  async getFunnel(benchmarkRunId?: string | null): Promise<FunnelResponse> {
    return this.request<FunnelResponse>("/funnel", { benchmark_run_id: benchmarkRunId });
  }

  async getBenchmarks(benchmarkRunId?: string | null): Promise<BenchmarksResponse> {
    return this.request<BenchmarksResponse>("/benchmarks", { benchmark_run_id: benchmarkRunId });
  }

  async getPredictionQuality(benchmarkRunId?: string | null): Promise<PredictionQualityResponse> {
    return this.request<PredictionQualityResponse>("/prediction-quality", { benchmark_run_id: benchmarkRunId });
  }

  async getAdaptive(benchmarkRunId?: string | null): Promise<AdaptiveRecoveryResponse> {
    return this.request<AdaptiveRecoveryResponse>("/adaptive", { benchmark_run_id: benchmarkRunId });
  }

  async getSafety(benchmarkRunId?: string | null): Promise<SafetyResponse> {
    return this.request<SafetyResponse>("/safety", { benchmark_run_id: benchmarkRunId });
  }

  async getCohorts(benchmarkRunId?: string | null): Promise<CohortsResponse> {
    return this.request<CohortsResponse>("/cohorts", { benchmark_run_id: benchmarkRunId });
  }

  async listCases(page: number = 1, pageSize: number = 20, status?: string, search?: string): Promise<CaseListResponse> {
    return this.request<CaseListResponse>("/cases", {
      page,
      page_size: pageSize,
      status,
      search,
    });
  }

  async getCaseDetail(caseId: string): Promise<CaseDetailResponse> {
    return this.request<CaseDetailResponse>(`/cases/${encodeURIComponent(caseId)}`);
  }

  async getCaseTimeline(caseId: string): Promise<CaseTimelineResponse> {
    return this.request<CaseTimelineResponse>(`/cases/${encodeURIComponent(caseId)}/timeline`);
  }

  async getReviewerQuestions(caseId: string): Promise<ReviewerQuestionsResponse> {
    return this.request<ReviewerQuestionsResponse>(`/cases/${encodeURIComponent(caseId)}/reviewer-questions`);
  }

  async getReproducibility(benchmarkRunId: string): Promise<ReproducibilityResponse> {
    return this.request<ReproducibilityResponse>(`/reproducibility/${encodeURIComponent(benchmarkRunId)}`);
  }

  async listBenchmarkRuns(): Promise<BenchmarkRunListResponse> {
    return this.request<BenchmarkRunListResponse>("/runs");
  }
}

export const apiClient = new DashboardApiClient();
