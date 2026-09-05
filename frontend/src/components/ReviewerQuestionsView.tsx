import React from "react";
import { CheckCircle, ShieldCheck, HelpCircle } from "lucide-react";

interface ReviewerQuestionsViewProps {
  questions: Record<string, any>;
  completeness: string;
  integrityValid: boolean;
  integrityIssues: string[];
}

export const ReviewerQuestionsView: React.FC<ReviewerQuestionsViewProps> = ({
  questions,
  completeness,
  integrityValid,
  integrityIssues,
}) => {
  const questionTitles: Record<string, string> = {
    Q1: "Q1: What failed initially and what triggered recovery?",
    Q2: "Q2: What intelligence and context were evaluated prior to action?",
    Q3: "Q3: Which recovery action was selected and why?",
    Q4: "Q4: How were safety policy and compliance constraints validated?",
    Q5: "Q5: How was the recovery dispatch executed and what was the outcome?",
    Q6: "Q6: What state transitions and adaptive cycles occurred?",
    Q7: "Q7: What was the final case resolution and financial reconciliation?",
  };

  const getCompletenessBadge = () => {
    const comp = (completeness || "UNKNOWN").toUpperCase();
    if (comp === "COMPLETE") {
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    }
    if (comp === "CORRUPT") {
      return "bg-red-50 text-red-700 border-red-200";
    }
    return "bg-amber-50 text-amber-700 border-amber-200";
  };

  return (
    <div className="space-y-6">
      {/* Integrity & Completeness Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Causal Audit Integrity &amp; Completeness
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Cryptographic chain verification and seven reviewer proofs
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className={`text-xs font-mono px-3 py-1 rounded-md border font-semibold ${getCompletenessBadge()}`}>
            Completeness: <strong>{completeness}</strong>
          </span>
          <span
            className={`text-xs font-mono px-3 py-1 rounded-md border font-semibold ${
              integrityValid
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-red-50 text-red-700 border-red-200"
            }`}
          >
            Audit Hash Chain: <strong>{integrityValid ? "VALID (0 Breaks)" : "INVALID"}</strong>
          </span>
        </div>
      </div>

      {integrityIssues && integrityIssues.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-xs text-red-800">
          <strong>Integrity Issues Detected:</strong>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            {integrityIssues.map((issue, idx) => (
              <li key={idx}>{issue}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 7 Questions Grid */}
      <div className="grid grid-cols-1 gap-4">
        {Object.entries(questionTitles).map(([key, title]) => {
          const answer = questions ? questions[key] : null;

          return (
            <div
              key={key}
              className="bg-white border border-slate-200 hover:border-slate-300 rounded-xl p-5 transition-all shadow-sm hover:shadow-md"
            >
              <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    {key}
                  </span>
                  <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
                </div>
                {answer ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Answered
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-200">
                    <HelpCircle className="w-3.5 h-3.5" />
                    No Record
                  </span>
                )}
              </div>

              {answer ? (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs font-mono text-slate-800 whitespace-pre-wrap overflow-x-auto max-h-60 leading-relaxed">
                  {typeof answer === "string" ? answer : JSON.stringify(answer, null, 2)}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No audit event data available for this question stage.</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
