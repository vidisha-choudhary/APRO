import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DashboardProvider } from "./context/DashboardContext";
import { Layout } from "./components/Layout";
import { OverviewPage } from "./pages/OverviewPage";
import { BenchmarksPage } from "./pages/BenchmarksPage";
import { CasesPage } from "./pages/CasesPage";
import { SafetyPage } from "./pages/SafetyPage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { AdaptivePage } from "./pages/AdaptivePage";
import { CohortsPage } from "./pages/CohortsPage";
import { ReproducibilityPage } from "./pages/ReproducibilityPage";

export const AppContent: React.FC = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<OverviewPage />} />
        <Route path="/dashboard/benchmarks" element={<BenchmarksPage />} />
        <Route path="/dashboard/cases" element={<CasesPage />} />
        <Route path="/dashboard/cases/:caseId" element={<CasesPage />} />
        <Route path="/dashboard/safety" element={<SafetyPage />} />
        <Route path="/dashboard/predictions" element={<PredictionsPage />} />
        <Route path="/dashboard/adaptive" element={<AdaptivePage />} />
        <Route path="/dashboard/cohorts" element={<CohortsPage />} />
        <Route path="/dashboard/reproducibility" element={<ReproducibilityPage />} />
        <Route path="/dashboard/reproducibility/:runId" element={<ReproducibilityPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <DashboardProvider>
        <AppContent />
      </DashboardProvider>
    </BrowserRouter>
  );
};

export default App;
