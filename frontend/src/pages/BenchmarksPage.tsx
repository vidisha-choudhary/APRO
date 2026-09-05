import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { BenchmarksResponse } from "../types/dashboard";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { BarChart3, CheckCircle2 } from "lucide-react";

export const BenchmarksPage: React.FC = () => {
  const { selectedRunId, lastRefreshTime } = useDashboard();
  const [data, setData] = useState<BenchmarksResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getBenchmarks(selectedRunId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load benchmark baseline comparisons");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedRunId, lastRefreshTime]);

  if (loading && !data) {
    return (
      <div className="py-20 text-center text-slate-500 text-sm animate-pulse">
        Loading baseline statistical proofs from PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!data || data.status === "empty" || !data.data || data.data.length === 0) {
    return <EmptyState message="No baseline comparison data available for this benchmark run." />;
  }

  return (
    <div className="space-y-6">
      {/* Overview & Statistical Rigor Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-slate-900">
              Statistical Superiority vs Industry Baselines
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-500">
            <span className="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
              Multiplicity Policy: <strong>{data.multiplicity_policy || "HOLM"}</strong>
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 border border-slate-200 rounded-lg p-4">
          <div>
            <span className="text-xs text-slate-500 font-medium">APRO Recovery Rate</span>
            <div className="text-2xl font-bold text-emerald-600 font-mono">
              {(data.data[0].apro_recovery_rate * 100).toFixed(2)}%
            </div>
          </div>
          <div>
            <span className="text-xs text-slate-500 font-medium">APRO Net Recovered Revenue</span>
            <div className="text-2xl font-bold text-emerald-600 font-mono">
              ₹{(data.data[0].apro_net_recovered / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Paired Baseline Performance Comparisons
          </h3>
          <span className="text-xs text-slate-500 font-mono">
            {data.data.length} competitive baselines evaluated
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600">
                <th className="py-3 px-4 font-semibold">Baseline</th>
                <th className="py-3 px-4 font-semibold">Baseline Rec Rate</th>
                <th className="py-3 px-4 font-semibold">Delta Rec Rate</th>
                <th className="py-3 px-4 font-semibold">95% CI (Delta Rate)</th>
                <th className="py-3 px-4 font-semibold">Net Rev Delta</th>
                <th className="py-3 px-4 font-semibold">P-Value</th>
                <th className="py-3 px-4 font-semibold">Significance</th>
                <th className="py-3 px-4 font-semibold">Label</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {data.data.map((b) => {
                const deltaRatePct = (b.absolute_recovery_delta * 100).toFixed(2);
                const isPositiveDelta = b.absolute_recovery_delta > 0;
                const netRevDelta = b.incremental_net_revenue;

                return (
                  <tr key={b.baseline_name} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-sans">
                      <div className="font-semibold text-slate-900">{b.baseline_name}</div>
                      <div className="text-[11px] text-slate-500">{b.baseline_type} (v{b.baseline_version})</div>
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {(b.baseline_recovery_rate * 100).toFixed(2)}%
                    </td>
                    <td className={`py-3 px-4 font-semibold ${isPositiveDelta ? "text-emerald-600" : "text-red-600"}`}>
                      {isPositiveDelta ? `+${deltaRatePct}%` : `${deltaRatePct}%`}
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {b.delta_recovery_ci_95 ? `[${(b.delta_recovery_ci_95[0] * 100).toFixed(2)}%, ${(b.delta_recovery_ci_95[1] * 100).toFixed(2)}%]` : "N/A"}
                    </td>
                    <td className={`py-3 px-4 font-semibold ${netRevDelta >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {netRevDelta >= 0 ? `+₹${(netRevDelta / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : `-₹${Math.abs(netRevDelta / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                    </td>
                    <td className="py-3 px-4 text-blue-600 font-semibold">
                      {b.p_value !== null && b.p_value !== undefined
                        ? b.p_value < 0.001 ? "< 0.001" : b.p_value.toFixed(4)
                        : "N/A"}
                    </td>
                    <td className="py-3 px-4">
                      {b.is_statistically_significant ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold">
                          <CheckCircle2 className="w-3 h-3" />
                          Significant
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200 text-[10px] font-semibold">
                          Not Sig
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <StatusBadge status={b.comparison_label} size="sm" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
