import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { BenchmarkRunSummaryDTO } from "../types/dashboard";
import { apiClient } from "../api/client";

interface DashboardContextType {
  selectedRunId: string | null;
  setSelectedRunId: (runId: string | null) => void;
  availableRuns: BenchmarkRunSummaryDTO[];
  refreshRuns: () => Promise<void>;
  lastRefreshTime: Date;
  triggerRefresh: () => void;
  autoRefreshEnabled: boolean;
  setAutoRefreshEnabled: (enabled: boolean) => void;
  isBackendConnected: boolean;
  backendError: string | null;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlRunId = searchParams.get("benchmark_run_id");

  const [selectedRunId, setSelectedRunIdState] = useState<string | null>(urlRunId);
  const [availableRuns, setAvailableRuns] = useState<BenchmarkRunSummaryDTO[]>([]);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date>(new Date());
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState<boolean>(true);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(true);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  useEffect(() => {
    if (urlRunId !== selectedRunId) {
      setSelectedRunIdState(urlRunId);
    }
  }, [urlRunId]);

  const setSelectedRunId = useCallback(
    (runId: string | null) => {
      setSelectedRunIdState(runId);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (runId) {
            next.set("benchmark_run_id", runId);
          } else {
            next.delete("benchmark_run_id");
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const triggerRefresh = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1);
    setLastRefreshTime(new Date());
  }, []);

  const refreshRuns = useCallback(async () => {
    try {
      const res = await apiClient.listBenchmarkRuns();
      setAvailableRuns(res.runs || []);
      setIsBackendConnected(true);
      setBackendError(null);
    } catch (err: any) {
      console.warn("Failed to fetch benchmark runs list:", err);
      setIsBackendConnected(false);
      setBackendError(err.message || "Failed to reach backend API");
    }
  }, []);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns, refreshTrigger]);

  useEffect(() => {
    if (!autoRefreshEnabled) return;
    const interval = setInterval(() => {
      triggerRefresh();
    }, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, [autoRefreshEnabled, triggerRefresh]);

  return (
    <DashboardContext.Provider
      value={{
        selectedRunId,
        setSelectedRunId,
        availableRuns,
        refreshRuns,
        lastRefreshTime,
        triggerRefresh,
        autoRefreshEnabled,
        setAutoRefreshEnabled,
        isBackendConnected,
        backendError,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = (): DashboardContextType => {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
};
