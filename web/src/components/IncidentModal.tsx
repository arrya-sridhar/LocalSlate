"use client";

import { IncidentReport } from "@/lib/extraction-engine";

interface IncidentModalProps {
  incident: IncidentReport;
  onClose: () => void;
}

export default function IncidentModal({ incident, onClose }: IncidentModalProps) {
  const getPriorityClass = (p: string) => {
    switch (p) {
      case "CRITICAL": return "critical";
      case "HIGH": return "high";
      case "MEDIUM": return "medium";
      case "LOW": return "low";
      default: return "low";
    }
  };

  const getUrgencyStyle = (u: string) => {
    switch (u) {
      case "CRITICAL": return { background: "var(--priority-critical-bg)", color: "var(--priority-critical)" };
      case "HIGH": return { background: "var(--priority-high-bg)", color: "var(--priority-high)" };
      case "MEDIUM": return { background: "var(--priority-medium-bg)", color: "var(--priority-medium)" };
      default: return { background: "var(--priority-low-bg)", color: "var(--priority-low)" };
    }
  };

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(incident, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `incident_${incident.incident_id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span style={{ fontSize: "16px", fontWeight: 700 }}>Incident Detail</span>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px", fontFamily: "'JetBrains Mono', monospace" }}>
              {incident.incident_id}
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
            <span className={`priority-badge ${getPriorityClass(incident.computed_priority_level)}`}>
              {incident.computed_priority_level}
            </span>
            <span style={{ fontSize: "13px", color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}>
              {new Date(incident.iso_timestamp).toLocaleString()}
            </span>
          </div>

          <div className="detail-section">
            <div className="detail-label">Summary</div>
            <div className="detail-value">{incident.system_summary}</div>
          </div>

          <div className="detail-section">
            <div className="detail-label">Identified Locations</div>
            <div className="tag-list">
              {incident.identified_entities.locations.map((loc, i) => (
                <span key={i} className="tag" style={{ fontSize: "13px", padding: "4px 10px" }}>{loc}</span>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <div className="detail-label">Identified Personnel</div>
            <div className="tag-list">
              {incident.identified_entities.personnel.map((p, i) => (
                <span key={i} className="tag person" style={{ fontSize: "13px", padding: "4px 10px" }}>{p}</span>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <div className="detail-label">Actionable Tasks ({incident.actionable_tasks.length})</div>
            <div className="task-list">
              {incident.actionable_tasks.map((task, i) => (
                <div key={i} className="task-item">
                  <span className="task-desc">{task.task_desc}</span>
                  <span className="task-urgency" style={getUrgencyStyle(task.urgency)}>
                    {task.urgency}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)" }}>
            <button
              className="btn-submit"
              onClick={handleExportJSON}
              style={{ background: "rgba(99, 102, 241, 0.15)", border: "1px solid rgba(99, 102, 241, 0.3)" }}
            >
              📥 Export as JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
