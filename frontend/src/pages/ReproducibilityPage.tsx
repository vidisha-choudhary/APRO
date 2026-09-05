import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { ReproducibilityResponse } from "../types/dashboard";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { History, Hash, Copy, Check, Terminal } from "lucide-react";

export const ReproducibilityPage: React.FC = () => {
  const { selectedRunId, availableRuns, lastRefreshTime } = useDashboard();
  const [data, setData] = useState<ReproducibilityResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const activeRunId = selectedRunId || (availableRuns.length > 0 ? availableRuns[0].benchmark_run_id : null);

  const fetchData = async () => {
    if (!activeRunId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getReproducibility(activeRunId);
      setData(res);
    } catch (err: any) {
      setError(err.message || `Failed to load reproducibility manifest for run ${activeRunId}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeRunId, lastRefreshTime]);

  const copyManifest = () => {
    if (!data) return;
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading && !data) {
    return (
      <div className="py-20 text-center text-slate-500 text-sm animate-pulse">
        Loading cryptographic reproducibility manifest from PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!data) {
    return <EmptyState message="No reproducibility record available. Select or load a benchmark run." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Benchmark Reproducibility &amp; Provenance Manifest
            </h2>
            <p className="text-xs text-slate-500 font-medium">
              Cryptographic hashes, deterministic parameters, and immutable configuration
            </p>
          </div>
        </div>

        <button
          onClick={copyManifest}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold border border-blue-200 shadow-sm transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied Manifest JSON" : "Copy Manifest JSON"}
        </button>
      </div>

      {/* Cryptographic Hashes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 text-slate-700 mb-2.5 font-sans font-semibold">
            <Hash className="w-4 h-4 text-blue-600" />
            Report SHA-256 Hash (Immutable Run Proof)
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-blue-900 font-mono text-xs break-all select-all leading-relaxed">
            {data.report_hash}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 text-slate-700 mb-2.5 font-sans font-semibold">
            <Hash className="w-4 h-4 text-emerald-600" />
            Dataset Snapshot SHA-256 Hash
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-emerald-900 font-mono text-xs break-all select-all leading-relaxed">
            {data.snapshot_hash}
          </div>
        </div>
      </div>

      {/* Provenance Metadata Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Deterministic Execution Parameters
          </h3>
        </div>

        <div className="divide-y divide-slate-100 font-mono text-xs">
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Benchmark Run ID</span>
            <span className="text-slate-900 font-bold">{data.benchmark_run_id}</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Dataset ID &amp; Version</span>
            <span className="text-slate-800">{data.dataset_id} (v{data.dataset_version})</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Evaluation Config Version</span>
            <span className="text-slate-800">{data.evaluation_config_version}</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Metric Schema Version</span>
            <span className="text-slate-800">{data.metric_schema_version}</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Code Revision (Git SHA)</span>
            <span className="text-slate-800">{data.code_revision}</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Bootstrap Seed</span>
            <span className="text-blue-600 font-bold">{data.bootstrap_seed}</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Bootstrap Iterations</span>
            <span className="text-blue-600 font-bold">{data.bootstrap_iterations.toLocaleString()}</span>
          </div>
          <div className="px-6 py-3 flex justify-between">
            <span className="text-slate-500 font-medium">Created At</span>
            <span className="text-slate-800">{new Date(data.created_at).toISOString()}</span>
          </div>
        </div>
      </div>

      {/* Raw Manifest Viewer */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-blue-600" />
          Full Reproducibility Manifest (JSON)
        </h3>
        <pre className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-xs font-mono text-slate-100 overflow-x-auto max-h-80 leading-relaxed">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    </div>
  );
};
