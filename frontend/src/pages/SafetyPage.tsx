import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { SafetyResponse } from "../types/dashboard";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { ShieldCheck, ShieldAlert } from "lucide-react";

export const SafetyPage: React.FC = () => {
  const { selectedRunId, lastRefreshTime } = useDashboard();
  const [data, setData] = useState<SafetyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getSafety(selectedRunId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load safety invariant metrics");
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
        Verifying safety invariants against PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!data || data.status === "empty" || !data.invariants || data.invariants.length === 0) {
    return <EmptyState message="No safety invariant evaluation data available for this benchmark run." />;
  }

  const isAllPass = data.overall_safety_status === "PASS";
  const totalViolations = data.unsafe_dispatch_count + data.policy_bypass_count + data.stale_policy_reuse_count + data.duplicate_execution_count;

  return (
    <div className="space-y-6">
      {/* Safety Summary Banner */}
      <div
        className={`border rounded-xl p-6 shadow-sm flex flex-wrap items-center justify-between gap-4 ${
          isAllPass
            ? "bg-emerald-50/60 border-emerald-200"
            : "bg-red-50/60 border-red-200"
        }`}
      >
        <div className="flex items-center gap-3.5">
          <div
            className={`p-3 rounded-xl shadow-sm ${
              isAllPass
                ? "bg-emerald-100 text-emerald-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {isAllPass ? (
              <ShieldCheck className="w-8 h-8" />
            ) : (
              <ShieldAlert className="w-8 h-8" />
            )}
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              System Invariant Safety Verification:
              <span
                className={`font-bold ${
                  isAllPass ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {data.overall_safety_status}
              </span>
            </h2>
            <p className="text-xs text-slate-500 font-medium">
              Deterministic verification of all Phase 10 &amp; Phase 15 safety guardrails
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
          <div className="bg-white px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 shadow-sm font-medium">
            Invariants Evaluated: <strong className="text-slate-900 font-bold">{data.invariants.length}</strong>
          </div>
          <div
            className={`px-3 py-1.5 rounded-lg border shadow-sm font-semibold ${
              totalViolations === 0
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-red-50 text-red-700 border-red-200"
            }`}
          >
            Total Critical Violations: <strong>{totalViolations}</strong>
          </div>
        </div>
      </div>

      {/* Invariant Verification Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.invariants.map((inv) => {
          const isPass = inv.status === "PASS";

          return (
            <div
              key={inv.invariant_name}
              className={`bg-white border ${
                isPass ? "border-slate-200" : "border-red-200"
              } rounded-xl p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between`}
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    {inv.invariant_name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 font-medium">
                    {inv.description}
                  </p>
                </div>
                <StatusBadge status={inv.status} size="sm" />
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex items-center justify-between font-mono text-xs mt-2">
                <span className="text-slate-500 font-medium">Recorded Violations:</span>
                <span
                  className={`font-bold ${
                    inv.violation_count === 0 ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {inv.violation_count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
