# Data Model & Schema Definition

## 1. Input Constraints
*   **Audio Data:** Strictly limited to `16kHz`, `mono`, `.wav` format. Max file size: `25MB` (approx. 15 minutes of speech).
*   **Raw Text:** UTF-8 encoded plain text. Hard limit of 4000 characters to prevent SLM context overflow (aligned with Phi-3-mini-4k).

## 2. Target JSON Schema (Incident & Field Report)
The SLM is prompted to output strictly adhering to this nested JSON schema:

```json
{
  "incident_id": "uuid4",
  "iso_timestamp": "2026-06-28T09:52:23Z",
  "computed_priority_level": "HIGH", 
  "system_summary": "Brief 2-sentence summary of the field report.",
  "identified_entities": {
    "locations": ["Sector 7", "Main Node"],
    "personnel": ["Agent K", "Operative J"]
  },
  "actionable_tasks": [
    {
      "task_desc": "Deploy secondary cooling array",
      "urgency": "CRITICAL"
    }
  ]
}
```
*(Note: `computed_priority_level` must be one of: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)*

## 3. Local SQLite DDL Schema
The local database maps directly to the flattened JSON schema. 

```sql
-- SQLite Database Schema

CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    iso_timestamp TEXT NOT NULL,
    computed_priority_level TEXT NOT NULL,
    system_summary TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identified_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    location_name TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS identified_personnel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    personnel_name TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS actionable_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    task_desc TEXT NOT NULL,
    urgency TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

-- Optimization indexes for local querying
CREATE INDEX idx_incidents_priority ON incidents(computed_priority_level);
CREATE INDEX idx_incidents_timestamp ON incidents(iso_timestamp);
```
