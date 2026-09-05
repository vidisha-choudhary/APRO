import React from "react";
import { Inbox, AlertCircle, RefreshCw } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  message?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No Benchmark Data Available",
  message = "No benchmark evaluation run has been persisted yet. Execute an evaluation runner or load benchmark truth to populate live metrics.",
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 bg-white border border-dashed border-slate-300 rounded-2xl text-center my-6 shadow-sm">
      <div className="p-4 bg-slate-50 rounded-full text-slate-400 mb-4 border border-slate-100">
        <Inbox className="w-8 h-8 text-blue-600" />
      </div>
      <h3 className="text-base font-semibold text-slate-900 mb-1.5">{title}</h3>
      <p className="text-xs text-slate-500 max-w-md mb-6">{message}</p>
      <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono text-blue-700 font-medium">
        python scripts/run_phase_15_acceptance.py
      </div>
    </div>
  );
};

interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 bg-red-50/80 border border-red-200 rounded-2xl text-center my-6 shadow-sm">
      <div className="p-3 bg-red-100 rounded-full text-red-600 mb-3">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-red-900 mb-1">Backend Communication Error</h3>
      <p className="text-xs text-red-700 max-w-md mb-4">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded-lg shadow-sm transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Connection
        </button>
      )}
    </div>
  );
};
