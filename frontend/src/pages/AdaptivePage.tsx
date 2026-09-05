import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { AdaptiveRecoveryResponse } from "../types/dashboard";
import { KPICard } from "../components/KPICard";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { RefreshCw, Repeat, ArrowUpRight, Shield } from "lucide-react";

export const AdaptivePage: React.FC = () => {
  const { selectedRunId, lastRefreshTime } = useDashboard();
  const [data, setData] = useState<AdaptiveRecoveryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getAdaptive(selectedRunId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load adaptive loop metrics");
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
        Loading adaptive loop progression from PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!data || data.status === "empty") {
    return <EmptyState message="No adaptive recovery data available for this benchmark run." />;
  }

  return (
    <div className="space-y-6">
      {/* Adaptive Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KPICard
          title="Multi-Cycle Recovery Rate"
          value={`${((data.multi_cycle_recovery_rate ?? 0) * 100).toFixed(1)}%`}
          subtitle={`${data.multi_cycle_recovery_count ?? 0} cases recovered in cycle 2+`}
          icon={ArrowUpRight}
          variant="success"
        />

        <KPICard
          title="Re-Evaluated Cases"
          value={(data.re_evaluated_cases_count ?? 0).toLocaleString()}
          subtitle={`Recovery rate on retry: ${((data.re_evaluation_recovery_rate ?? 0) * 100).toFixed(1)}%`}
          icon={Repeat}
          variant="primary"
        />

        <KPICard
          title="Bounded Termination"
          value={`${((data.bounded_termination_rate ?? 0) * 100).toFixed(1)}%`}
          subtitle={
            data.hard_ceiling_violations !== null && data.hard_ceiling_violations !== undefined
              ? `Hard ceiling violations: ${data.hard_ceiling_violations}`
              : "Hard ceiling data unavailable"
          }
          icon={Shield}
          variant="default"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KPICard
          title="Single-Cycle Recovery Rate"
          value={`${((data.single_cycle_recovery_rate ?? 0) * 100).toFixed(1)}%`}
          subtitle={`${data.single_cycle_recovery_count ?? 0} cases recovered in cycle 1`}
          icon={Repeat}
          variant="default"
        />

        <KPICard
          title="Mean Cycles to Recovery"
          value={
            data.mean_cycles_to_recovery !== null &&
            data.mean_cycles_to_recovery !== undefined &&
            data.mean_cycles_to_recovery > 0
              ? data.mean_cycles_to_recovery.toFixed(2)
              : "N/A"
          }
          subtitle={
            data.median_cycles_to_recovery !== null &&
            data.median_cycles_to_recovery !== undefined &&
            data.median_cycles_to_recovery > 0
              ? `Median cycles: ${data.median_cycles_to_recovery.toFixed(2)}`
              : "Median cycles: N/A"
          }
          icon={RefreshCw}
          variant="default"
        />

        <KPICard
          title="Same-Action Avoidance"
          value={`${(data.same_action_avoidance_rate * 100).toFixed(1)}%`}
          subtitle="Non-repeating recovery action policy"
          icon={Shield}
          variant="success"
        />
      </div>

      {/* Cycle Progression Section */}
      {data.cycle_distribution && data.cycle_distribution.length > 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-blue-600" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                Cycle-by-Cycle Adaptive Progression
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              {data.cycle_distribution.length} active cycles recorded
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <th className="py-3 px-4 font-semibold">Cycle</th>
                  <th className="py-3 px-4 font-semibold">Cases Attempted</th>
                  <th className="py-3 px-4 font-semibold">Proportion of Total</th>
                  <th className="py-3 px-4 font-semibold">Cycle Distribution Bar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {data.cycle_distribution.map((cycle) => {
                  const pct = cycle.percentage.toFixed(1);

                  return (
                    <tr key={cycle.cycle_number} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-bold text-blue-600">
                        Cycle {cycle.cycle_number}
                      </td>
                      <td className="py-3 px-4 text-slate-700 font-medium">
                        {cycle.case_count.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-emerald-600 font-bold">
                        {pct}%
                      </td>
                      <td className="py-3 px-4 w-48">
                        <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                          <div
                            className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full"
                            style={{ width: `${Math.min(parseFloat(pct), 100)}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl p-6 text-center text-slate-500 text-xs shadow-sm">
          <p className="font-semibold text-slate-800 mb-1">
            Authoritative Single vs Multi-Cycle Summary
          </p>
          <p>
            Cycle-level breakdown is not disaggregated in this benchmark run. Single-cycle and multi-cycle recovery metrics are authoritatively reflected above.
          </p>
        </div>
      )}
    </div>
  );
};
