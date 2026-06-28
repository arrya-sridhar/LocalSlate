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

## 3. MySQL DDL Schema
The local database maps directly to the flattened JSON schema. 

```sql
-- MySQL Database Schema

CREATE TABLE IF NOT EXISTS incidents (
    incident_id VARCHAR(255) PRIMARY KEY,
    iso_timestamp VARCHAR(255) NOT NULL,
    computed_priority_level VARCHAR(50) NOT NULL,
    system_summary VARCHAR(1000) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identified_locations (
    id INT PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(255) NOT NULL,
    location_name VARCHAR(255) NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS identified_personnel (
    id INT PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(255) NOT NULL,
    personnel_name VARCHAR(255) NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS actionable_tasks (
    id INT PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(255) NOT NULL,
    task_desc VARCHAR(1000) NOT NULL,
    urgency VARCHAR(50) NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

-- Optimization indexes for local querying
CREATE INDEX idx_incidents_priority ON incidents(computed_priority_level);
CREATE INDEX idx_incidents_timestamp ON incidents(iso_timestamp);
```

## 4. Connection Pooling Optimization
To guarantee that background thread writers do not block frontend web socket or fetch readers, the SQLAlchemy Database Engine runs with:
* **Pool Size**: `pool_size = 10`
* **Max Overflow**: `max_overflow = 20`
* **Pool Recycle**: 3600 seconds
* **Connection Pre-ping**: `pool_pre_ping = True` (detects stale connections automatically)

