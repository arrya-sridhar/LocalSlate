"use client";
import { useState, useEffect } from "react";

interface StatusPanelProps {
  totalIncidents: number;
  processedCount: number;
}

export default function StatusPanel({ totalIncidents, processedCount }: StatusPanelProps) {
  const [uptime, setUptime] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
    const interval = setInterval(() => {
      const start = (window as unknown as Record<string, number>).__localslate_start || Date.now();
      setUptime(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatUptime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="card-title">⚡ System Status</span>
      </div>
      <div className="card-body">
        <div className="status-grid">
          <div className="status-item">
            <div className="status-label">Engine</div>
            <div className="status-value success">Browser-Local</div>
          </div>
          <div className="status-item">
            <div className="status-label">Network</div>
            <div className="status-value" style={{ color: "#f97316" }}>Isolated</div>
          </div>
          <div className="status-item">
            <div className="status-label">Session</div>
            <div className="status-value accent">{formatUptime(uptime)}</div>
          </div>
          <div className="status-item">
            <div className="status-label">Mode</div>
            <div className="status-value" style={{ color: "#22c55e" }}>Offline-First</div>
          </div>
          <div className="status-item full-width">
            <div className="status-label">Storage</div>
            <div className="status-value accent">IndexedDB (Browser-Persistent)</div>
          </div>
        </div>

        <div className="metrics-row">
          <div className="metric-item">
            <div className="metric-number" style={{ color: "#22c55e" }}>{processedCount}</div>
            <div className="metric-label">Processed</div>
          </div>
          <div className="metric-item">
            <div className="metric-number accent">{totalIncidents}</div>
            <div className="metric-label">Total Records</div>
          </div>
        </div>
      </div>
    </div>
  );
}
