import React from "react";
import { CalibrationBinDTO } from "../types/dashboard";
import { TrendingUp } from "lucide-react";

interface CalibrationChartProps {
  bins: CalibrationBinDTO[];
}

export const CalibrationChart: React.FC<CalibrationChartProps> = ({ bins }) => {
  if (!bins || bins.length === 0) {
    return (
      <div className="text-slate-400 text-xs py-8 text-center bg-white border border-slate-200 rounded-xl">
        No calibration bin data available.
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Recovery Prediction Calibration
          </h3>
        </div>
        <span className="text-xs text-slate-500 font-medium">
          Predicted vs Empirical Success Rate
        </span>
      </div>

      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600">
              <th className="py-2.5 px-4 font-semibold">Bin Range</th>
              <th className="py-2.5 px-4 font-semibold">Samples</th>
              <th className="py-2.5 px-4 font-semibold">Mean Predicted Prob</th>
              <th className="py-2.5 px-4 font-semibold">Empirical Recovery Rate</th>
              <th className="py-2.5 px-4 font-semibold">Visual Calibration</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono">
            {bins.map((bin) => {
              const predPct = (bin.mean_predicted_prob * 100).toFixed(1);
              const empPct = (bin.empirical_recovery_rate * 100).toFixed(1);

              return (
                <tr key={bin.bin_index} className="hover:bg-slate-50/80 transition">
                  <td className="py-2.5 px-4 text-slate-700">
                    [{bin.bin_lower.toFixed(2)} – {bin.bin_upper.toFixed(2)}]
                  </td>
                  <td className="py-2.5 px-4 text-slate-500">{bin.sample_count}</td>
                  <td className="py-2.5 px-4 text-blue-600 font-semibold">{predPct}%</td>
                  <td className="py-2.5 px-4 text-emerald-600 font-semibold">{empPct}%</td>
                  <td className="py-2.5 px-4 w-48">
                    <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden relative border border-slate-200">
                      <div
                        className="h-full bg-blue-300 absolute top-0 left-0"
                        style={{ width: `${predPct}%` }}
                      />
                      <div
                        className="h-full bg-emerald-500 absolute top-0 left-0 opacity-80"
                        style={{ width: `${empPct}%` }}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-4 mt-3 text-[11px] text-slate-500 font-medium">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 bg-blue-400 rounded-sm"></span>
          <span>Mean Predicted Probability</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm"></span>
          <span>Empirical Recovery Rate</span>
        </div>
      </div>
    </div>
  );
};
