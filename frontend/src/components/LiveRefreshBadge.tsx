import React, { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useDashboard } from "../context/DashboardContext";

export const LiveRefreshBadge: React.FC = () => {
  const {
    lastRefreshTime,
    triggerRefresh,
    autoRefreshEnabled,
    setAutoRefreshEnabled,
    isBackendConnected,
    backendError,
  } = useDashboard();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshClick = async () => {
    setIsRefreshing(true);
    triggerRefresh();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const getStatusText = () => {
    if (backendError || !isBackendConnected) return "ERROR";
    if (isRefreshing) return "REFRESHING";
    return "LIVE TRUTH";
  };

  return (
    <div className="flex items-center gap-2.5 bg-white border border-slate-200 rounded-lg px-3 py-1 text-xs text-slate-700 shadow-sm">
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          {isBackendConnected && autoRefreshEnabled && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          )}
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              backendError || !isBackendConnected
                ? "bg-red-500"
                : isRefreshing
                ? "bg-blue-500"
                : "bg-emerald-500"
            }`}
          ></span>
        </span>
        <span className="font-semibold text-slate-800">
          {getStatusText()}
        </span>
      </div>

      <span className="text-slate-300">|</span>

      <span className="text-slate-500 font-mono text-[11px]">
        {lastRefreshTime.toLocaleTimeString()}
      </span>

      <button
        onClick={handleRefreshClick}
        className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-800 transition"
        title="Refresh now"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />
      </button>

      <button
        onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
        className={`px-2 py-0.5 rounded-md font-semibold text-[10px] transition ${
          autoRefreshEnabled
            ? "bg-blue-50 text-blue-700 border border-blue-200"
            : "bg-slate-100 text-slate-500 border border-slate-200"
        }`}
        title="Toggle 10s auto-refresh"
      >
        {autoRefreshEnabled ? "AUTO 10s" : "PAUSED"}
      </button>
    </div>
  );
};
