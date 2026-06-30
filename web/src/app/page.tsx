"use client";

import { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import StatusPanel from "@/components/StatusPanel";
import IngestPanel from "@/components/IngestPanel";
import IncidentTable from "@/components/IncidentTable";
import IncidentModal from "@/components/IncidentModal";
import { extractIncident, IncidentReport } from "@/lib/extraction-engine";
import { saveIncident, getIncidents, getIncidentCount } from "@/lib/store";

export default function Home() {
  const [incidents, setIncidents] = useState<IncidentReport[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [processedCount, setProcessedCount] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<IncidentReport | null>(null);
  const [toasts, setToasts] = useState<{ id: string; message: string; type: "success" | "error" | "info" }[]>([]);

  // Load incidents from IndexedDB on mount
  const loadIncidents = useCallback(async () => {
    try {
      const data = await getIncidents(50);
      const count = await getIncidentCount();
      setIncidents(data);
      setTotalCount(count);
    } catch {
      // IndexedDB might not be available in SSR
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadIncidents();
  }, [loadIncidents]);

  // Record session start time
  useEffect(() => {
    (window as unknown as Record<string, number>).__localslate_start = Date.now();
  }, []);

  const showToast = (message: string, type: "success" | "error" | "info") => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const handleIngest = async (text: string, source: string) => {
    setIsProcessing(true);

    try {
      // Simulate realistic processing delay
      await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 700));

      // Extract structured data — runs entirely in-browser
      const report = extractIncident(text);

      // Save to IndexedDB
      await saveIncident(report);

      // Update state
      setProcessedCount(prev => prev + 1);
      await loadIncidents();

      showToast(
        `✓ Extracted ${report.computed_priority_level} priority incident from ${source}. ID: ${report.incident_id.slice(0, 8)}…`,
        "success"
      );
    } catch (err) {
      showToast(`✗ Failed to process: ${err}`, "error");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <>
      <Header incidentCount={totalCount} />

      <div className="app-container">
        <div className="dashboard">
          {/* Sidebar */}
          <div className="dashboard-sidebar">
            <StatusPanel
              totalIncidents={totalCount}
              processedCount={processedCount}
            />
            <IngestPanel
              onIngest={handleIngest}
              isProcessing={isProcessing}
            />
          </div>

          {/* Main content */}
          <div className="dashboard-main">
            <IncidentTable
              incidents={incidents}
              onSelectIncident={setSelectedIncident}
            />
          </div>
        </div>
      </div>

      {/* Incident detail modal */}
      {selectedIncident && (
        <IncidentModal
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
        />
      )}

      {/* Toast notifications */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map(toast => (
            <div key={toast.id} className={`toast ${toast.type}`}>
              {toast.message}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
