"use client";

import { useState } from "react";
import { IncidentReport } from "@/lib/extraction-engine";

interface IncidentTableProps {
  incidents: IncidentReport[];
  onSelectIncident: (incident: IncidentReport) => void;
}

export default function IncidentTable({ incidents, onSelectIncident }: IncidentTableProps) {
  const [filter, setFilter] = useState<string>("ALL");

  const filtered = filter === "ALL"
    ? incidents
    : incidents.filter(i => i.computed_priority_level === filter);

  const priorities = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

  const getPriorityClass = (p: string) => {
    switch (p) {
      case "CRITICAL": return "critical";
      case "HIGH": return "high";
      case "MEDIUM": return "medium";
      case "LOW": return "low";
      case "PENDING_REVIEW": return "pending_review";
      default: return "low";
    }
  };

  if (incidents.length === 0) {
    return (
      <div className="glass-card">
        <div className="card-header">
          <span className="card-title">📋 Intelligence Records</span>
        </div>
        <div className="empty-state">
          <div className="empty-icon">📡</div>
          <div className="empty-title">No Intelligence Records</div>
          <div className="empty-desc">
            Ingest field notes via the panel on the left. Text, files, and voice input are all supported. All processing happens locally in your browser.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="card-title">📋 Intelligence Records ({filtered.length})</span>
        <div style={{ display: "flex", gap: "4px" }}>
          {priorities.map(p => (
            <button
              key={p}
              className={`ingest-tab ${filter === p ? "active" : ""}`}
              onClick={() => setFilter(p)}
              style={{ padding: "4px 10px", fontSize: "11px" }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>
      <div className="incidents-table-wrap">
        <table className="incidents-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Timestamp</th>
              <th>Priority</th>
              <th>Locations</th>
              <th>Personnel</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((inc) => (
              <tr
                key={inc.incident_id}
                onClick={() => onSelectIncident(inc)}
                style={{ cursor: "pointer" }}
              >
                <td>
                  <span className="incident-id">
                    {inc.incident_id.slice(0, 8)}…
                  </span>
                </td>
                <td>
                  <span className="incident-timestamp">
                    {new Date(inc.iso_timestamp).toLocaleString("en-US", {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </td>
                <td>
                  <span className={`priority-badge ${getPriorityClass(inc.computed_priority_level)}`}>
                    {inc.computed_priority_level === "CRITICAL" && "🔴 "}
                    {inc.computed_priority_level === "HIGH" && "🟠 "}
                    {inc.computed_priority_level === "MEDIUM" && "🟡 "}
                    {inc.computed_priority_level === "LOW" && "🟢 "}
                    {inc.computed_priority_level}
                  </span>
                </td>
                <td>
                  <div className="tag-list">
                    {inc.identified_entities.locations.map((loc, i) => (
                      <span key={i} className="tag">{loc}</span>
                    ))}
                  </div>
                </td>
                <td>
                  <div className="tag-list">
                    {inc.identified_entities.personnel.map((p, i) => (
                      <span key={i} className="tag person">{p}</span>
                    ))}
                  </div>
                </td>
                <td>
                  <span className="incident-summary">
                    {inc.system_summary.length > 80
                      ? inc.system_summary.slice(0, 80) + "…"
                      : inc.system_summary}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
