import React from "react";
import { Database } from "lucide-react";
import { useDashboard } from "../context/DashboardContext";

export const BenchmarkRunSelector: React.FC = () => {
  const { selectedRunId, setSelectedRunId, availableRuns } = useDashboard();

  return (
    <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1 text-xs shadow-sm">
      <Database className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
      <span className="text-slate-500 font-medium">Benchmark Run:</span>
      <select
        value={selectedRunId || ""}
        onChange={(e) => setSelectedRunId(e.target.value ? e.target.value : null)}
        className="bg-slate-50 hover:bg-white text-slate-800 border border-slate-200 rounded px-2 py-0.5 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono transition"
      >
        <option value="">Latest Immutable Run (Auto)</option>
        {availableRuns.map((run) => (
          <option key={run.benchmark_run_id} value={run.benchmark_run_id}>
            {run.benchmark_run_id} ({run.dataset_id} • {(run.recovery_rate * 100).toFixed(1)}%)
          </option>
        ))}
      </select>
    </div>
  );
};
