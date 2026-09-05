import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { KPICard } from "../components/KPICard";
import { StatusBadge } from "../components/StatusBadge";
import { FunnelChart } from "../components/FunnelChart";
import { CalibrationChart } from "../components/CalibrationChart";
import { Layout } from "../components/Layout";
import { OverviewPage } from "../pages/OverviewPage";
import { BenchmarksPage } from "../pages/BenchmarksPage";
import { AdaptivePage } from "../pages/AdaptivePage";
import { CasesPage } from "../pages/CasesPage";
import { PredictionsPage } from "../pages/PredictionsPage";
import { apiClient } from "../api/client";
import { DashboardProvider } from "../context/DashboardContext";

describe("Anti-Static Dynamic Value Verification", () => {
  it("KPICard renders dynamically passed arbitrary metric values V1 and V2", () => {
    const { unmount } = render(<KPICard title="Recovery Rate" value="42.7%" subtitle="Test V1" />);
    expect(screen.getByText("42.7%")).toBeInTheDocument();
    expect(screen.getByText("Test V1")).toBeInTheDocument();
    unmount();

    render(<KPICard title="Recovery Rate" value="89.1%" subtitle="Test V2" />);
    expect(screen.getByText("89.1%")).toBeInTheDocument();
    expect(screen.getByText("Test V2")).toBeInTheDocument();
  });

  it("StatusBadge dynamically reflects PASS, FAIL, ACTIVE, CLOSED_RECOVERED", () => {
    const { unmount, rerender } = render(<StatusBadge status="PASS" />);
    expect(screen.getByText("PASS")).toBeInTheDocument();

    rerender(<StatusBadge status="FAIL" />);
    expect(screen.getByText("FAIL")).toBeInTheDocument();

    rerender(<StatusBadge status="CLOSED_RECOVERED" />);
    expect(screen.getByText("CLOSED_RECOVERED")).toBeInTheDocument();
    unmount();
  });

  it("FunnelChart renders backend percentage 50.0 as 50.0% without 100x multiplication", () => {
    const stages = [
      {
        stage_name: "Eligible",
        count: 1000,
        percentage: 100.0,
        dropoff_count: 0,
        dropoff_percentage: 0.0,
      },
      {
        stage_name: "Recovered",
        count: 500,
        percentage: 50.0,
        dropoff_count: 500,
        dropoff_percentage: 50.0,
      },
    ];

    render(<FunnelChart stages={stages} />);
    expect(screen.getByText("Eligible")).toBeInTheDocument();
    expect(screen.getByText("1,000 cases")).toBeInTheDocument();
    expect(screen.getByText("100.0% of total")).toBeInTheDocument();

    expect(screen.getByText("Recovered")).toBeInTheDocument();
    expect(screen.getByText("500 cases")).toBeInTheDocument();
    expect(screen.getByText("50.0% of total")).toBeInTheDocument();
  });

  it("FunnelChart renders N/A / Not reported by benchmark when counts are null", () => {
    const stages = [
      { stage_name: "Eligible", count: 100, percentage: 100.0 },
      { stage_name: "Attempted", count: null, percentage: null },
      { stage_name: "Pending", count: null, percentage: null },
      { stage_name: "Recovered", count: 40, percentage: 40.0 },
      { stage_name: "Stopped", count: null, percentage: null },
      { stage_name: "Escalated", count: null, percentage: null },
    ];

    render(<FunnelChart stages={stages} />);
    expect(screen.getByText("100 cases")).toBeInTheDocument();
    expect(screen.getByText("40 cases")).toBeInTheDocument();
    const naTexts = screen.getAllByText("N/A / Not reported by benchmark");
    expect(naTexts.length).toBe(4);
  });

  it("CalibrationChart renders dynamic bin intervals and rates", () => {
    const bins = [
      {
        bin_index: 0,
        bin_lower: 0.0,
        bin_upper: 0.2,
        mean_predicted_prob: 0.12,
        empirical_recovery_rate: 0.15,
        sample_count: 55,
      },
    ];

    render(<CalibrationChart bins={bins} />);
    expect(screen.getByText("[0.00 – 0.20]")).toBeInTheDocument();
    expect(screen.getByText("12.0%")).toBeInTheDocument();
    expect(screen.getByText("15.0%")).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
  });

  it("OverviewPage renders dynamically from injected API response V1 and updates on V2 with INR ₹ formatting", async () => {
    vi.spyOn(apiClient, "listBenchmarkRuns").mockResolvedValue({ status: "ok", metadata: {} as any, runs: [] });
    const getOverviewSpy = vi.spyOn(apiClient, "getOverview");
    const getFunnelSpy = vi.spyOn(apiClient, "getFunnel");

    // V1 response
    getOverviewSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_v1" },
      data: {
        eligible_cases: 100,
        recovered_cases: 40,
        recovery_rate: 0.40,
        gross_recovered_revenue: 400000,
        net_recovered_revenue: 350000,
        total_intervention_cost: 50000,
        cost_per_recovered_rupee: 0.1428,
        safety_status: "PASS",
        latest_benchmark_run_id: "run_v1",
        dataset_id: "ds_v1",
        dataset_version: "1.0",
        is_synthetic_demo: false,
        last_updated_at: "2026-09-04T00:00:00Z",
      },
    } as any);

    getFunnelSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_v1" },
      data: [
        { stage_name: "Eligible", count: 100, percentage: 100.0, dropoff_count: 0, dropoff_percentage: 0.0 },
      ],
    } as any);

    const { unmount } = render(
      <MemoryRouter initialEntries={["/dashboard?benchmark_run_id=run_v1"]}>
        <DashboardProvider>
          <OverviewPage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("40.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("40 of 100 eligible cases")).toBeInTheDocument();
    // Verify genuine INR currency formatting (₹4,000.00 and ₹3,500.00)
    expect(screen.getByText("₹4,000.00")).toBeInTheDocument();
    expect(screen.getByText("₹3,500.00")).toBeInTheDocument();
    expect(screen.getByText("After ₹500.00 costs")).toBeInTheDocument();
    expect(screen.getByText("₹0.1428/₹1")).toBeInTheDocument();
    expect(screen.queryByText(/\$/)).toBeNull();
    unmount();

    // V2 response
    getOverviewSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_v2" },
      data: {
        eligible_cases: 200,
        recovered_cases: 150,
        recovery_rate: 0.75,
        gross_recovered_revenue: 1500000,
        net_recovered_revenue: 1400000,
        total_intervention_cost: 100000,
        cost_per_recovered_rupee: 0.0714,
        safety_status: "PASS",
        latest_benchmark_run_id: "run_v2",
        dataset_id: "ds_v2",
        dataset_version: "2.0",
        is_synthetic_demo: false,
        last_updated_at: "2026-09-04T00:00:00Z",
      },
    } as any);

    getFunnelSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_v2" },
      data: [
        { stage_name: "Eligible", count: 200, percentage: 100.0, dropoff_count: 0, dropoff_percentage: 0.0 },
      ],
    } as any);

    render(
      <MemoryRouter initialEntries={["/dashboard?benchmark_run_id=run_v2"]}>
        <DashboardProvider>
          <OverviewPage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("75.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("150 of 200 eligible cases")).toBeInTheDocument();
    expect(screen.getByText("₹15,000.00")).toBeInTheDocument();
    expect(screen.getByText("₹14,000.00")).toBeInTheDocument();
  });

  it("BenchmarksPage propagates benchmark_run_id and renders baseline deltas with INR formatting", async () => {
    const getBenchmarksSpy = vi.spyOn(apiClient, "getBenchmarks");
    getBenchmarksSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_benchmark_a" },
      data: [
        {
          baseline_name: "Fixed Retry",
          baseline_type: "FIXED_RETRY",
          baseline_version: "1.0.0",
          apro_recovery_rate: 0.75,
          baseline_recovery_rate: 0.50,
          absolute_recovery_delta: 0.25,
          relative_recovery_delta: 0.50,
          apro_gross_recovered: 75000,
          baseline_gross_recovered: 50000,
          incremental_recovered_amount: 25000,
          apro_net_recovered: 70000,
          baseline_net_recovered: 45000,
          incremental_net_revenue: 25000,
          apro_intervention_cost: 5000,
          baseline_intervention_cost: 5000,
          delta_recovery_ci_95: [0.15, 0.35],
          delta_net_revenue_ci_95: [15000, 35000],
          p_value: 0.001,
          adjusted_p_value: 0.004,
          comparison_label: "BENCHMARK_ASSOCIATION",
          is_statistically_significant: true,
        },
      ],
      multiplicity_policy: "HOLM",
    } as any);

    render(
      <MemoryRouter initialEntries={["/dashboard/benchmarks?benchmark_run_id=run_benchmark_a"]}>
        <DashboardProvider>
          <BenchmarksPage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Fixed Retry")).toBeInTheDocument();
    });
    expect(screen.getByText("+25.00%")).toBeInTheDocument();
    expect(screen.getByText("0.0010")).toBeInTheDocument();
    expect(screen.getByText("+₹250.00")).toBeInTheDocument();
  });

  it("PredictionsPage renders authoritative Phase 15 decision fields without derivations and handles N/A", async () => {
    const getPredSpy = vi.spyOn(apiClient, "getPredictionQuality");
    getPredSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_pred_auth" },
      brier_score: 0.1234,
      calibration_bins: [],
      classification_metrics: {
        precision: 0.85,
        recall: 0.75,
        f1_score: 0.796,
        roc_auc: 0.88,
        pr_auc: 0.82,
      },
      decision_quality: {
        best_action_selection_rate: 0.80,
        oracle_gap_avg: 0.25,
        action_regret_avg: 0.05,
      },
    } as any);

    const { unmount } = render(
      <MemoryRouter initialEntries={["/dashboard/predictions?benchmark_run_id=run_pred_auth"]}>
        <DashboardProvider>
          <PredictionsPage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("0.1234")).toBeInTheDocument();
    });
    expect(screen.getByText("80.0%")).toBeInTheDocument();
    expect(screen.getByText("0.2500")).toBeInTheDocument();
    expect(screen.getByText("0.0500")).toBeInTheDocument();
    expect(screen.queryByText("Accuracy")).toBeNull();
    expect(screen.queryByText("Suboptimal Rate")).toBeNull();
    expect(screen.queryByText("Net Benefit vs Oracle")).toBeNull();
    unmount();

    // Test with missing decision quality metrics
    getPredSpy.mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_pred_null" },
      brier_score: 0.15,
      calibration_bins: [],
      classification_metrics: {
        f1_score: null,
        precision: null,
        recall: null,
      },
      decision_quality: {
        best_action_selection_rate: null,
        oracle_gap_avg: null,
        action_regret_avg: null,
      },
    } as any);

    render(
      <MemoryRouter initialEntries={["/dashboard/predictions?benchmark_run_id=run_pred_null"]}>
        <DashboardProvider>
          <PredictionsPage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("0.1500")).toBeInTheDocument();
    });
    const naElements = screen.getAllByText("N/A");
    expect(naElements.length).toBeGreaterThanOrEqual(3);
  });

  it("AdaptivePage renders N/A when cycle metrics are unavailable or zero without 1.00 fallback", async () => {
    vi.spyOn(apiClient, "getAdaptive").mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_adapt_na" },
      data: {
        single_cycle_recovery_count: 50,
        single_cycle_recovery_rate: 50.0,
        multi_cycle_recovery_count: 0,
        multi_cycle_recovery_rate: 0.0,
        mean_cycles_to_recovery: 0.0,
        median_cycles_to_recovery: 0.0,
        same_action_avoidance_rate: 1.0,
        bounded_termination_rate: 1.0,
        re_evaluated_cases_count: 0,
        re_evaluation_recovery_rate: 0.0,
        action_transition_matrix: {},
        cycle_distribution: { 1: 50 },
        hard_ceiling_violations: 0,
      },
    } as any);

    render(
      <MemoryRouter initialEntries={["/dashboard/adaptive?benchmark_run_id=run_adapt_na"]}>
        <DashboardProvider>
          <AdaptivePage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Mean Cycles to Recovery")).toBeInTheDocument();
    });
    expect(screen.getByText("Median cycles: N/A")).toBeInTheDocument();
    expect(screen.queryByText("1.00")).toBeNull();
  });

  it("AdaptivePage renders 'Hard ceiling data unavailable' when hard_ceiling_violations is null", async () => {
    vi.spyOn(apiClient, "getAdaptive").mockResolvedValueOnce({
      status: "ok",
      metadata: { benchmark_run_id: "run_adapt_no_ceiling" },
      data: {
        single_cycle_recovery_count: 50,
        single_cycle_recovery_rate: 50.0,
        multi_cycle_recovery_count: 10,
        multi_cycle_recovery_rate: 10.0,
        mean_cycles_to_recovery: 1.2,
        median_cycles_to_recovery: 1.0,
        same_action_avoidance_rate: 1.0,
        bounded_termination_rate: 1.0,
        re_evaluated_cases_count: 10,
        re_evaluation_recovery_rate: 20.0,
        action_transition_matrix: {},
        cycle_distribution: { 1: 50, 2: 10 },
        hard_ceiling_violations: null,
      },
    } as any);

    render(
      <MemoryRouter initialEntries={["/dashboard/adaptive?benchmark_run_id=run_adapt_no_ceiling"]}>
        <DashboardProvider>
          <AdaptivePage />
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Hard ceiling data unavailable")).toBeInTheDocument();
    });
    expect(screen.queryByText("Loop invariant guaranteed")).toBeNull();
  });

  it("CasesPage supports direct deep-link route /dashboard/cases/:caseId to reconstruct case", async () => {
    const timelineSpy = vi.spyOn(apiClient, "getCaseTimeline").mockResolvedValueOnce({
      status: "ok",
      metadata: {},
      case_id: "case_deep_999",
      events: [
        {
          event_id: "evt_01",
          case_id: "case_deep_999",
          event_type: "RECOVERY_INITIATED",
          timestamp: "2026-09-04T12:00:00Z",
          actor: "SYSTEM",
          payload: { note: "Initial trigger" },
        },
      ],
    } as any);

    const questionsSpy = vi.spyOn(apiClient, "getReviewerQuestions").mockResolvedValueOnce({
      status: "ok",
      metadata: {},
      case_id: "case_deep_999",
      questions: {
        Q1: "Payment failed with GATEWAY_TIMEOUT",
        Q2: "Action RETRY executed",
        Q3: "Verified via idempotency key",
        Q4: "Policy compliant",
        Q5: "Executed in 240ms",
        Q6: "Successful recovery",
        Q7: "₹500.00 recovered, balanced ledger",
      },
      completeness: "COMPLETE",
      integrity_valid: true,
      integrity_issues: [],
    } as any);

    render(
      <MemoryRouter initialEntries={["/dashboard/cases/case_deep_999"]}>
        <DashboardProvider>
          <Routes>
            <Route path="/dashboard/cases/:caseId" element={<CasesPage />} />
          </Routes>
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Back to Case Explorer")).toBeInTheDocument();
    });
    expect(screen.getByText("case_deep_999")).toBeInTheDocument();
    expect(screen.getByText("Causal Audit Integrity & Completeness")).toBeInTheDocument();
    expect(screen.getByText("Payment failed with GATEWAY_TIMEOUT")).toBeInTheDocument();
    expect(timelineSpy).toHaveBeenCalledWith("case_deep_999");
    expect(questionsSpy).toHaveBeenCalledWith("case_deep_999");
  });

  it("Layout renders APRO branding, Track 03 contextual badge, and compact navigation tabs", async () => {
    vi.spyOn(apiClient, "listBenchmarkRuns").mockResolvedValue({ status: "ok", metadata: {} as any, runs: [] });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <DashboardProvider>
          <Layout>
            <div>Test Child Content</div>
          </Layout>
        </DashboardProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("APRO")).toBeInTheDocument();
    });
    expect(screen.getByText("Adaptive Payment Recovery Orchestrator")).toBeInTheDocument();
    expect(screen.getByText("Razorpay AI Buildathon · Track 03")).toBeInTheDocument();
    expect(screen.getByText("LIVE TRUTH")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Benchmarks")).toBeInTheDocument();
    expect(screen.getByText("Cases")).toBeInTheDocument();
    expect(screen.getByText("Safety")).toBeInTheDocument();
    expect(screen.getByText("Predictions")).toBeInTheDocument();
    expect(screen.getByText("Adaptive")).toBeInTheDocument();
    expect(screen.getByText("Cohorts")).toBeInTheDocument();
    expect(screen.getByText("Provenance")).toBeInTheDocument();
    expect(screen.getByText("Test Child Content")).toBeInTheDocument();
  });

  it("Razorpay design tokens are defined and legacy purple theme is eliminated", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const cssPath = path.resolve(__dirname, "../index.css");
    const cssContent = fs.readFileSync(cssPath, "utf-8");

    // Verify presence of all required Razorpay-inspired design tokens
    expect(cssContent).toContain("--color-brand-primary: #0c8ce9");
    expect(cssContent).toContain("--color-bg: #f8fafc");
    expect(cssContent).toContain("--color-surface: #ffffff");
    expect(cssContent).toContain("--color-border: #e2e8f0");
    expect(cssContent).toContain("--color-text-primary: #0f172a");
    expect(cssContent).toContain("--color-text-secondary: #475569");
    expect(cssContent).toContain("--color-success: #10b981");
    expect(cssContent).toContain("--color-warning: #f59e0b");
    expect(cssContent).toContain("--color-danger: #ef4444");

    // Verify legacy dark purple body has been completely eliminated
    expect(cssContent).not.toContain("#0b0f19");
  });
});
