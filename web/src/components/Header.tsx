"use client";

interface HeaderProps {
  incidentCount: number;
}

export default function Header({ incidentCount }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-brand">
          <span className="header-logo">🌌</span>
          <div>
            <div className="header-title">LocalSlate</div>
            <div className="header-subtitle">Zero-Cloud Intelligence Pipeline</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div className="header-status">
            <span className="status-dot" />
            Browser-Only • {incidentCount} Records
          </div>
        </div>
      </div>
    </header>
  );
}
