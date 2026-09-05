import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  FolderKanban,
  ShieldCheck,
  TrendingUp,
  RefreshCw,
  PieChart,
  History,
  Zap,
} from "lucide-react";
import { LiveRefreshBadge } from "./LiveRefreshBadge";
import { BenchmarkRunSelector } from "./BenchmarkRunSelector";
import { useDashboard } from "../context/DashboardContext";

export type NavTab =
  | "overview"
  | "benchmarks"
  | "cases"
  | "safety"
  | "predictions"
  | "adaptive"
  | "cohorts"
  | "reproducibility";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { backendError } = useDashboard();
  const location = useLocation();
  const navigate = useNavigate();

  const navItems: { path: string; label: string; icon: React.FC<{ className?: string }> }[] = [
    { path: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { path: "/dashboard/benchmarks", label: "Benchmarks", icon: BarChart3 },
    { path: "/dashboard/cases", label: "Cases", icon: FolderKanban },
    { path: "/dashboard/safety", label: "Safety", icon: ShieldCheck },
    { path: "/dashboard/predictions", label: "Predictions", icon: TrendingUp },
    { path: "/dashboard/adaptive", label: "Adaptive", icon: RefreshCw },
    { path: "/dashboard/cohorts", label: "Cohorts", icon: PieChart },
    { path: "/dashboard/reproducibility", label: "Provenance", icon: History },
  ];

  const handleNavClick = (path: string) => {
    navigate({
      pathname: path,
      search: location.search,
    });
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200 px-4 sm:px-6 py-2.5 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* APRO Fintech Glyph */}
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-[#0c8ce9] to-[#0052cc] flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20">
              <Zap className="w-5 h-5 fill-white text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight text-slate-900">
                  APRO
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  Razorpay AI Buildathon · Track 03
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Adaptive Payment Recovery Orchestrator
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <BenchmarkRunSelector />
            <LiveRefreshBadge />
          </div>
        </div>
      </header>

      {/* Backend Error Banner */}
      {backendError && (
        <div className="bg-red-50 border-b border-red-200 text-red-700 px-6 py-2 text-xs font-medium flex items-center justify-center gap-2">
          <span>⚠️ {backendError}</span>
        </div>
      )}

      {/* Navigation Subheader */}
      <div className="bg-slate-100/80 border-b border-slate-200 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex overflow-x-auto space-x-1.5 py-1.5 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.path === "/dashboard"
                ? location.pathname === "/dashboard"
                : location.pathname.startsWith(item.path);

            return (
              <button
                key={item.path}
                onClick={() => handleNavClick(item.path)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-150 ${
                  isActive
                    ? "bg-white text-blue-700 shadow-sm border border-slate-200/80 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-600" : "text-slate-500"}`} />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Page Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-4 px-6 bg-white text-center text-xs text-slate-500">
        APRO Live Reviewer Cockpit • Strictly Read-Only Observability Plane • PostgreSQL Backed
      </footer>
    </div>
  );
};
