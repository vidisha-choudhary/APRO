import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { OverviewResponse, FunnelResponse } from "../types/dashboard";
import { KPICard } from "../components/KPICard";
import { FunnelChart } from "../components/FunnelChart";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { IndianRupee, Percent, TrendingUp, Wallet } from "lucide-react";

export const OverviewPage: React.FC = () => {
  const { selectedRunId, lastRefreshTime } = useDashboard();
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [funnel, setFunnel] = useState<FunnelResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ovRes, fnRes] = await Promise.all([
        apiClient.getOverview(selectedRunId),
        apiClient.getFunnel(selectedRunId),
      ]);
      setOverview(ovRes);
      setFunnel(fnRes);
    } catch (err: any) {
      setError(err.message || "Failed to load overview metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedRunId, lastRefreshTime]);

  if (loading && !overview) {
    return (
      <div className="py-20 text-center text-slate-500 text-sm animate-pulse">
        Loading live recovery metrics from PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!overview || overview.status === "empty" || !overview.data) {
    return <EmptyState message={overview?.message || undefined} />;
  }

  const kpis = overview.data;

  return (
    <div className="space-y-6">
      {/* Benchmark Metadata Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-slate-500">
            Run ID: <strong className="text-slate-800">{kpis.latest_benchmark_run_id}</strong>
          </span>
          <span className="text-slate-300">•</span>
          <span className="font-mono text-slate-500">
            Dataset: <strong className="text-slate-800">{kpis.dataset_id} (v{kpis.dataset_version})</strong>
          </span>
          <span className="text-slate-300">•</span>
          <span className="font-mono text-slate-500">
            Report Hash: <strong className="text-blue-600">{overview.metadata.report_hash?.substring(0, 12)}...</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          {kpis.is_synthetic_demo ? (
            <span className="px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-mono text-[10px] font-semibold">
              SYNTHETIC DEMO DATASET
            </span>
          ) : (
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono text-[10px] font-semibold">
              CANONICAL PRODUCTION SNAPSHOT
            </span>
          )}
          <StatusBadge status={kpis.safety_status} size="sm" />
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Recovery Rate"
          value={`${(kpis.recovery_rate * 100).toFixed(1)}%`}
          subtitle={`${kpis.recovered_cases.toLocaleString()} of ${kpis.eligible_cases.toLocaleString()} eligible cases`}
          icon={Percent}
          variant="primary"
        />

        <KPICard
          title="Gross Recovered"
          value={`₹${(kpis.gross_recovered_revenue / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          subtitle="Total transaction volume saved"
          icon={IndianRupee}
          variant="success"
        />

        <KPICard
          title="Net Recovered Revenue"
          value={`₹${(kpis.net_recovered_revenue / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          subtitle={`After ₹${(kpis.total_intervention_cost / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })} costs`}
          icon={Wallet}
          variant="success"
        />

        <KPICard
          title="Intervention Efficiency"
          value={kpis.cost_per_recovered_rupee !== null && kpis.cost_per_recovered_rupee !== undefined ? `₹${kpis.cost_per_recovered_rupee.toFixed(4)}/₹1` : "N/A"}
          subtitle={kpis.safety_status === "PASS" ? "Safety Invariants: 0 Violations" : "Safety Invariants Violated"}
          icon={TrendingUp}
          variant={kpis.safety_status === "PASS" ? "default" : "danger"}
        />
      </div>

      {/* Funnel Conversion Component */}
      {funnel && funnel.data && funnel.data.length > 0 && (
        <FunnelChart stages={funnel.data} />
      )}
    </div>
  );
};
