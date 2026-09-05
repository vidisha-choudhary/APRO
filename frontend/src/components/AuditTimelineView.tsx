import React, { useState } from "react";
import { AuditEventDTO } from "../types/dashboard";
import { Clock, User, ChevronDown, ChevronRight, Activity } from "lucide-react";

interface AuditTimelineViewProps {
  events: AuditEventDTO[];
}

export const AuditTimelineView: React.FC<AuditTimelineViewProps> = ({ events }) => {
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  if (!events || events.length === 0) {
    return (
      <div className="text-slate-400 text-xs py-8 text-center bg-white border border-slate-200 rounded-xl">
        No audit events recorded for this case.
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Causal Audit Event Timeline
          </h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {events.length} chronological events
        </span>
      </div>

      <div className="relative border-l-2 border-slate-200 ml-3.5 space-y-6">
        {events.map((event, idx) => {
          const isExpanded = !!expandedEvents[event.audit_event_id];

          return (
            <div key={event.audit_event_id || idx} className="relative pl-6">
              {/* Timeline marker */}
              <div className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-blue-600 border-2 border-white shadow-sm" />

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 hover:border-slate-300 hover:bg-white transition-all shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-blue-700 font-mono">
                      {event.event_type}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-200/80 text-slate-700 flex items-center gap-1 font-mono font-medium">
                      <User className="w-3 h-3 text-slate-500" />
                      {event.actor}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                    <Clock className="w-3 h-3 text-slate-400" />
                    <span>{new Date(event.timestamp).toLocaleString()}</span>
                    <button
                      onClick={() => toggleExpand(event.audit_event_id)}
                      className="ml-2 p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="text-xs text-slate-500 font-mono truncate">
                  Correlation ID: <span className="text-slate-800 font-medium">{event.correlation_id}</span>
                </div>

                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
                      Event Payload
                    </span>
                    <pre className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-[11px] font-mono text-slate-100 overflow-x-auto max-h-48">
                      {JSON.stringify(event.payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
