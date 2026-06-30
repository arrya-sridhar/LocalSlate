# REST API Specification

This document details all API endpoints exposed by the LocalSlate backend server.

---

## 1. Endpoints Reference

### GET `/`
- **Description**: Serves the single-page application frontend.
- **Response**: `200 OK` (HTML) or `404 Not Found` (JSON, if `index.html` is missing).

### GET `/health`
- **Description**: Verifies API server and database connection health.
- **Response**: `200 OK` (JSON)
  ```json
  {
    "ok": true,
    "database": "connected",
    "offline_mode": true
  }
  ```

### GET `/status`
- **Description**: Returns live system resource metrics, queue statistics, and database priority tallies.
- **Response**: `200 OK` (JSON)
  ```json
  {
    "is_running": true,
    "current_file": "report.wav",
    "current_status": "Transcribing...",
    "current_stage": 2,
    "queue_count": 0,
    "processed_count": 5,
    "failed_count": 0,
    "cpu_utilization": 24.5,
    "ram_percent": 68.2,
    "ram_gb_used": 2.72,
    "ram_gb_total": 4.0,
    "db_stats": {
      "total": 5,
      "CRITICAL": 1,
      "HIGH": 2,
      "MEDIUM": 1,
      "LOW": 1
    }
  }
  ```

### GET `/incidents`
- **Description**: Retrieves a paginated stream of extracted incident reports from SQLite.
- **Parameters**: `limit` (int, default=10)
- **Response**: `200 OK` (JSON Array)

### POST `/process`
- **Description**: Submits plain text notes for immediate extraction and DB write.
- **Request Body**:
  ```json
  {
    "text": "High temperature detected in Sector 7."
  }
  ```
- **Response**: `200 OK` (Structured Incident JSON)

### POST `/upload`
- **Description**: Uploads a text (`.txt`) or audio (`.wav`) file for watchdog queue ingestion.
- **Request Body**: Multipart form data with field `file`.
- **Response**: `200 OK`
  ```json
  {
    "filename": "report.wav",
    "status": "queued"
  }
  ```

### DELETE `/incidents`
- **Description**: Purges all SQLite records.
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "message": "Database records cleared successfully."
  }
  ```
