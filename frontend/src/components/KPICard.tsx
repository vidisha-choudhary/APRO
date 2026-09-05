import React from "react";
import { LucideIcon } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  variant?: "default" | "success" | "danger" | "warning" | "primary";
  tooltip?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  tooltip,
}) => {
  const getBorderColor = () => {
    switch (variant) {
      case "success":
        return "border-emerald-200/80 hover:border-emerald-400";
      case "danger":
        return "border-red-200/80 hover:border-red-400";
      case "warning":
        return "border-amber-200/80 hover:border-amber-400";
      case "primary":
        return "border-blue-200/80 hover:border-blue-400";
      default:
        return "border-slate-200 hover:border-slate-300";
    }
  };

  const getValueColor = () => {
    switch (variant) {
      case "success":
        return "text-emerald-600";
      case "danger":
        return "text-red-600";
      case "warning":
        return "text-amber-600";
      case "primary":
        return "text-blue-600";
      default:
        return "text-slate-900";
    }
  };

  const getIconContainer = () => {
    switch (variant) {
      case "success":
        return "bg-emerald-50 text-emerald-600 border border-emerald-100";
      case "danger":
        return "bg-red-50 text-red-600 border border-red-100";
      case "warning":
        return "bg-amber-50 text-amber-600 border border-amber-100";
      case "primary":
        return "bg-blue-50 text-blue-600 border border-blue-100";
      default:
        return "bg-slate-50 text-slate-600 border border-slate-100";
    }
  };

  return (
    <div
      title={tooltip}
      className={`bg-white border ${getBorderColor()} rounded-xl p-5 transition-all duration-200 shadow-sm hover:shadow-md flex flex-col justify-between`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </span>
        {Icon && (
          <div className={`p-2 rounded-lg ${getIconContainer()}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <div>
        <div className={`text-2xl sm:text-3xl font-bold tracking-tight ${getValueColor()}`}>
          {value}
        </div>
        {subtitle && (
          <div className="text-xs text-slate-500 mt-1.5 flex items-center gap-1 font-medium">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};
