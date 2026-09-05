import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, Clock, HelpCircle } from "lucide-react";

interface StatusBadgeProps {
  status: string | null | undefined;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const normStatus = (status || "UNKNOWN").toUpperCase();

  let bg = "bg-slate-100 text-slate-700 border-slate-200";
  let Icon = HelpCircle;

  if (normStatus === "PASS" || normStatus === "RECOVERED" || normStatus === "CLOSED_RECOVERED" || normStatus === "SUPERIOR") {
    bg = "bg-emerald-50 text-emerald-700 border-emerald-200";
    Icon = CheckCircle2;
  } else if (normStatus === "FAIL" || normStatus === "EXHAUSTED" || normStatus === "CLOSED_EXHAUSTED" || normStatus === "ERROR") {
    bg = "bg-red-50 text-red-700 border-red-200";
    Icon = XCircle;
  } else if (normStatus === "ACTIVE" || normStatus === "IN_PROGRESS" || normStatus === "OPEN") {
    bg = "bg-blue-50 text-blue-700 border-blue-200";
    Icon = Clock;
  } else if (normStatus === "WARNING" || normStatus === "SUSPENDED") {
    bg = "bg-amber-50 text-amber-700 border-amber-200";
    Icon = AlertTriangle;
  }

  const padding = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-full border ${bg} ${padding} shadow-sm`}
    >
      <Icon className="w-3.5 h-3.5 flex-shrink-0" />
      {normStatus}
    </span>
  );
};
