import React from "react";
import { FunnelStageData } from "../types/dashboard";
import { ArrowDownRight, Layers } from "lucide-react";

interface FunnelChartProps {
  stages: FunnelStageData[];
}

export const FunnelChart: React.FC<FunnelChartProps> = ({ stages }) => {
  if (!stages || stages.length === 0) {
    return (
      <div className="text-slate-400 text-xs py-8 text-center bg-white border border-slate-200 rounded-xl">
        No funnel stage data available.
      </div>
    );
  }

  const maxCount = Math.max(...stages.map((s) => s.count ?? 0), 1);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Recovery Funnel Conversion
          </h3>
        </div>
        <span className="text-xs text-slate-500 font-medium">
          End-to-End Pipeline Health
        </span>
      </div>

      <div className="space-y-4">
        {stages.map((stage, idx) => {
          const hasCount = stage.count !== null && stage.count !== undefined;
          const widthPercent = hasCount ? Math.max(((stage.count ?? 0) / maxCount) * 100, 8) : 0;
          const isFinal = idx === stages.length - 1;

          return (
            <div key={stage.stage_name} className="relative">
              <div className="flex justify-between items-center text-xs mb-1.5 font-medium">
                <span className="text-slate-800 font-semibold">{stage.stage_name}</span>
                <div className="flex items-center gap-3">
                  {hasCount ? (
                    <>
                      <span className="font-mono text-slate-700 font-medium">
                        {(stage.count ?? 0).toLocaleString()} cases
                      </span>
                      {stage.percentage !== null && stage.percentage !== undefined && (
                        <span className="text-blue-600 font-mono font-semibold text-[11px]">
                          {stage.percentage.toFixed(1)}% of total
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="text-slate-400 font-mono text-xs italic">
                      N/A / Not reported by benchmark
                    </span>
                  )}
                </div>
              </div>

              {/* Funnel Bar */}
              <div className="h-6 w-full bg-slate-100 rounded-lg overflow-hidden flex items-center px-1.5 border border-slate-200/70">
                {hasCount ? (
                  <div
                    className={`h-3.5 rounded-md transition-all duration-500 shadow-sm ${
                      isFinal
                        ? "bg-gradient-to-r from-emerald-500 to-teal-500"
                        : "bg-gradient-to-r from-[#0c8ce9] to-[#0066f5]"
                    }`}
                    style={{ width: `${widthPercent}%` }}
                  />
                ) : (
                  <div className="h-1 w-full bg-slate-200 rounded border border-dashed border-slate-300" />
                )}
              </div>

              {idx < stages.length - 1 && (
                <div className="flex justify-center my-0.5">
                  <ArrowDownRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
