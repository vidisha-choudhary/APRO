import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReviewerQuestionsView } from "../components/ReviewerQuestionsView";
import { AuditTimelineView } from "../components/AuditTimelineView";

describe("Reviewer & Audit Components", () => {
  it("ReviewerQuestionsView renders all 7 questions with proof answers", () => {
    const questions = {
      Q1: "Initial soft decline with code insufficient_funds",
      Q2: "Context score 0.85, balance estimation positive",
      Q3: "Retry with optimal timing interval 4 hours",
      Q4: "Policy constraints validated: 0 violations",
      Q5: "Dispatched to Stripe transport, captured successfully",
      Q6: "Transitioned from OPEN to CLOSED_RECOVERED in cycle 1",
      Q7: "Final resolution: $500.00 recovered, ledger balanced",
    };

    render(
      <ReviewerQuestionsView
        questions={questions}
        completeness="COMPLETE"
        integrityValid={true}
        integrityIssues={[]}
      />
    );

    expect(screen.getByText(/Q1: What failed initially/)).toBeInTheDocument();
    expect(screen.getByText(/Q2: What intelligence/)).toBeInTheDocument();
    expect(screen.getByText(/Q3: Which recovery action/)).toBeInTheDocument();
    expect(screen.getByText(/Q4: How were safety policy/)).toBeInTheDocument();
    expect(screen.getByText(/Q5: How was the recovery dispatch/)).toBeInTheDocument();
    expect(screen.getByText(/Q6: What state transitions/)).toBeInTheDocument();
    expect(screen.getByText(/Q7: What was the final case/)).toBeInTheDocument();
    expect(screen.getByText("COMPLETE")).toBeInTheDocument();
    expect(screen.getByText("VALID (0 Breaks)")).toBeInTheDocument();
  });

  it("AuditTimelineView renders chronological events with actors", () => {
    const events = [
      {
        audit_event_id: "evt_001",
        case_id: "case_001",
        event_type: "EVENT_INGESTED",
        actor: "SYSTEM",
        timestamp: "2026-09-04T12:00:00Z",
        payload: { payment_id: "pay_123" },
        correlation_id: "corr_001",
      },
      {
        audit_event_id: "evt_002",
        case_id: "case_001",
        event_type: "POLICY_EVALUATED",
        actor: "POLICY_ENGINE",
        timestamp: "2026-09-04T12:00:01Z",
        payload: { decision: "ALLOW" },
        correlation_id: "corr_001",
      },
    ];

    render(<AuditTimelineView events={events} />);
    expect(screen.getByText("EVENT_INGESTED")).toBeInTheDocument();
    expect(screen.getByText("POLICY_EVALUATED")).toBeInTheDocument();
    expect(screen.getByText("POLICY_ENGINE")).toBeInTheDocument();
  });
});
