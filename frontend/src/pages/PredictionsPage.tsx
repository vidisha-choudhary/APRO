import React, { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { PredictionQualityResponse } from "../types/dashboard";
import { KPICard } from "../components/KPICard";
import { CalibrationChart } from "../components/CalibrationChart";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { Activity, Award, CheckCircle, Crosshair, Target, TrendingUp } from "lucide-react";

export const PredictionsPage: React.FC = () => {
  const { selectedRunId, lastRefreshTime } = useDashboard();
  const [data, setData] = useState<PredictionQualityResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getPredictionQuality(selectedRunId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load prediction quality metrics");
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
        Loading prediction quality and calibration from PostgreSQL truth...
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={fetchData} />;
  }

  if (!data || data.status === "empty") {
    return <EmptyState message="No prediction quality data available for this benchmark run." />;
  }

  const cls = data.classification_metrics;
  const dec = data.decision_quality;

  return (
    <div className="space-y-6">
      {/* Classification Metrics Grid */}
      {cls && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
            <Crosshair className="w-3.5 h-3.5 text-blue-600" />
            Probabilistic Recovery Model Calibration
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="Brier Score"
              value={data.brier_score !== null && data.brier_score !== undefined ? data.brier_score.toFixed(4) : "N/A"}
              subtitle="Mean squared error of probabilities"
              icon={Target}
              variant="primary"
            />
            <KPICard
              title="F1-Score"
              value={cls.f1_score !== null && cls.f1_score !== undefined ? cls.f1_score.toFixed(3) : "N/A"}
              subtitle={`Precision: ${cls.precision !== null && cls.precision !== undefined ? (cls.precision * 100).toFixed(1) + "%" : "N/A"} • Recall: ${cls.recall !== null && cls.recall !== undefined ? (cls.recall * 100).toFixed(1) + "%" : "N/A"}`}
              icon={Activity}
              variant="success"
            />
            <KPICard
              title="ROC-AUC"
              value={cls.roc_auc !== null && cls.roc_auc !== undefined ? cls.roc_auc.toFixed(3) : "N/A"}
              subtitle="Discriminative ranking accuracy"
              icon={TrendingUp}
              variant="success"
            />
            <KPICard
              title="PR-AUC"
              value={cls.pr_auc !== null && cls.pr_auc !== undefined ? cls.pr_auc.toFixed(3) : "N/A"}
              subtitle="Precision-Recall curve area"
              icon={Award}
              variant="success"
            />
          </div>
        </div>
      )}

      {/* Decision Quality Grid */}
      {dec && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
            Decision Engine Precision &amp; Regret Bounds
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KPICard
              title="Best Action Selection Rate"
              value={
                dec.best_action_selection_rate !== null && dec.best_action_selection_rate !== undefined
                  ? `${(dec.best_action_selection_rate * 100).toFixed(1)}%`
                  : "N/A"
              }
              subtitle="Optimal decision selection against counterfactual oracle"
              icon={CheckCircle}
              variant="success"
            />
            <KPICard
              title="Oracle Gap"
              value={
                dec.oracle_gap_avg !== null && dec.oracle_gap_avg !== undefined
                  ? dec.oracle_gap_avg.toFixed(4)
                  : "N/A"
              }
              subtitle="Mean expected value delta vs theoretical oracle"
              icon={Activity}
              variant="default"
            />
            <KPICard
              title="Average Action Regret"
              value={
                dec.action_regret_avg !== null && dec.action_regret_avg !== undefined
                  ? dec.action_regret_avg.toFixed(4)
                  : "N/A"
              }
              subtitle="Counterfactual regret across selected actions"
              icon={Target}
              variant="primary"
            />
          </div>
        </div>
      )}

      {/* Calibration Bins Component */}
      {data.calibration_bins && data.calibration_bins.length > 0 && (
        <CalibrationChart bins={data.calibration_bins} />
      )}
    </div>
  );
};
