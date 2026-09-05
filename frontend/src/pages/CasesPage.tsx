import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import { apiClient } from "../api/client";
import { CaseListResponse, AuditEventDTO, ReviewerQuestionsResponse } from "../types/dashboard";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { ReviewerQuestionsView } from "../components/ReviewerQuestionsView";
import { AuditTimelineView } from "../components/AuditTimelineView";
import { Search, ChevronLeft, ChevronRight, FolderKanban, Eye, ArrowLeft } from "lucide-react";

export const CasesPage: React.FC = () => {
  const { caseId } = useParams<{ caseId?: string }>();
  const navigate = useNavigate();
  const { lastRefreshTime } = useDashboard();
  const [data, setData] = useState<CaseListResponse | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selected case state for detail inspection
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(caseId || null);
  const [caseDetailLoading, setCaseDetailLoading] = useState<boolean>(false);
  const [caseTimeline, setCaseTimeline] = useState<AuditEventDTO[]>([]);
  const [reviewerQuestions, setReviewerQuestions] = useState<ReviewerQuestionsResponse | null>(null);
  const [caseDetailError, setCaseDetailError] = useState<string | null>(null);

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.listCases(
        page,
        pageSize,
        statusFilter || undefined,
        searchQuery || undefined
      );
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load recovery cases");
    } finally {
      setLoading(false);
    }
  };

  const loadCaseDetail = async (targetCaseId: string) => {
    try {
      setSelectedCaseId(targetCaseId);
      setCaseDetailLoading(true);
      setCaseDetailError(null);
      const [tlRes, qRes] = await Promise.all([
        apiClient.getCaseTimeline(targetCaseId),
        apiClient.getReviewerQuestions(targetCaseId),
      ]);
      setCaseTimeline(tlRes.events || []);
      setReviewerQuestions(qRes);
    } catch (err: any) {
      setCaseDetailError(err.message || `Failed to reconstruct case ${targetCaseId}`);
    } finally {
      setCaseDetailLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      loadCaseDetail(caseId);
    } else {
      setSelectedCaseId(null);
      setReviewerQuestions(null);
      setCaseTimeline([]);
      setCaseDetailError(null);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCases();
  }, [page, statusFilter, lastRefreshTime]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchCases();
  };

  // If a case is selected, render the full Causal Reconstruction View
  if (selectedCaseId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate("/dashboard/cases")}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition shadow-sm"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-slate-500" />
            Back to Case Explorer
          </button>
          <div className="text-xs font-mono text-slate-500">
            Case ID: <strong className="text-blue-600 font-bold">{selectedCaseId}</strong>
          </div>
        </div>

        {caseDetailLoading ? (
          <div className="py-20 text-center text-slate-500 text-sm animate-pulse">
            Reconstructing deterministic causal audit graph...
          </div>
        ) : caseDetailError ? (
          <ErrorState error={caseDetailError} onRetry={() => loadCaseDetail(selectedCaseId)} />
        ) : (
          <div className="space-y-8">
            {reviewerQuestions && (
              <ReviewerQuestionsView
                questions={reviewerQuestions.questions}
                completeness={reviewerQuestions.completeness}
                integrityValid={reviewerQuestions.integrity_valid}
                integrityIssues={reviewerQuestions.integrity_issues}
              />
            )}

            <AuditTimelineView events={caseTimeline} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls & Filter Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-slate-900">
              Recovery Case Explorer
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 text-slate-800 border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono font-medium"
            >
              <option value="">All Case States</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="CLOSED_RECOVERED">CLOSED_RECOVERED</option>
              <option value="CLOSED_EXHAUSTED">CLOSED_EXHAUSTED</option>
            </select>

            {/* Search Input */}
            <form onSubmit={handleSearchSubmit} className="relative">
              <input
                type="text"
                placeholder="Search case or payment ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-50 text-slate-800 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 w-60 font-mono transition"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            </form>
          </div>
        </div>
      </div>

      {loading && !data ? (
        <div className="py-20 text-center text-slate-500 text-sm animate-pulse">
          Loading case records from PostgreSQL truth...
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={fetchCases} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="No Recovery Cases Found" message="No case records matched the current search or filter." />
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <th className="py-3 px-4 font-semibold">Case ID</th>
                  <th className="py-3 px-4 font-semibold">Payment ID</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Cycles</th>
                  <th className="py-3 px-4 font-semibold">Recovered Amount</th>
                  <th className="py-3 px-4 font-semibold">Opened</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {data.items.map((item) => (
                  <tr key={item.case_id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-bold text-blue-600">
                      {item.case_id}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {item.payment_id}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <StatusBadge status={item.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      Cycle {item.cycle_count}
                    </td>
                    <td className="py-3 px-4 text-emerald-600 font-bold">
                      ₹{(item.recovered_amount / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {new Date(item.opened_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <button
                        onClick={() => navigate(`/dashboard/cases/${item.case_id}`)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold border border-blue-200 shadow-sm transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Audit Proof (Q1-Q7)
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/60 flex items-center justify-between text-xs text-slate-600">
            <span className="font-medium">
              Showing {data.items.length} of {data.total_count} cases (Page {data.page} of {data.total_pages})
            </span>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                className="p-1 rounded-md bg-white hover:bg-slate-100 border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 shadow-sm transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-mono text-slate-800 font-semibold">
                {data.page} / {data.total_pages}
              </span>
              <button
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="p-1 rounded-md bg-white hover:bg-slate-100 border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 shadow-sm transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
