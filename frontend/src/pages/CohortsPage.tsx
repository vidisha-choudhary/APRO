import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { CohortsResponse } from "../types/dashboard";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { PieChart, Filter } from "lucide-react";

export const CohortsPage: React.FC = () => {
  const { selectedRunId, lastRefreshTime } = useDashboard();
  const [data, setData] = useState<CohortsResponse | null>(null);
  const [selectedDimension, setSelectedDimension] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getCohorts(selectedRunId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load cohort breakdown metrics");
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
        Loading disaggregated cohort metrics from PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!data || data.status === "empty" || !data.cohorts || data.cohorts.length === 0) {
    return <EmptyState message="No cohort breakdown data available for this benchmark run." />;
  }

  const dimensions = Array.from(new Set(data.cohorts.map((c) => c.dimension)));
  const filteredCohorts = selectedDimension
    ? data.cohorts.filter((c) => c.dimension === selectedDimension)
    : data.cohorts;

  return (
    <div className="space-y-6">
      {/* Header with Dimension Filter */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <PieChart className="w-5 h-5 text-blue-600" />
          <h2 className="text-base font-semibold text-slate-900">
            Disaggregated Cohort Performance
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={selectedDimension}
            onChange={(e) => setSelectedDimension(e.target.value)}
            className="bg-slate-50 text-slate-800 border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono font-medium"
          >
            <option value="">All Cohort Dimensions</option>
            {dimensions.map((dim) => (
              <option key={dim} value={dim}>
                {dim}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Cohort Breakdown Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600">
                <th className="py-3 px-4 font-semibold">Dimension</th>
                <th className="py-3 px-4 font-semibold">Cohort Name</th>
                <th className="py-3 px-4 font-semibold">Cases</th>
                <th className="py-3 px-4 font-semibold">Recovered</th>
                <th className="py-3 px-4 font-semibold">Recovery Rate</th>
                <th className="py-3 px-4 font-semibold">Gross Recovered</th>
                <th className="py-3 px-4 font-semibold">Net Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {filteredCohorts.map((cohort, idx) => (
                <tr key={`${cohort.dimension}-${cohort.cohort_key}-${idx}`} className="hover:bg-slate-50/80 transition">
                  <td className="py-3 px-4 text-blue-600 font-semibold font-sans">
                    {cohort.dimension}
                  </td>
                  <td className="py-3 px-4 text-slate-800 font-medium">
                    {cohort.cohort_name}
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {cohort.case_count.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-emerald-600">
                    {cohort.recovered_count.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-emerald-600 font-bold">
                    {(cohort.recovery_rate * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 text-slate-800 font-medium">
                    ₹{(cohort.gross_recovered_amount / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="py-3 px-4 text-emerald-600 font-semibold">
                    ₹{(cohort.net_recovered_revenue / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
