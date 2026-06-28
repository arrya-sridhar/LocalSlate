# System Architecture Specification

LocalSlate is structured as a zero-trust, offline-first intelligence processing application. It consists of three decoupled layers:
1. **Frontend Viewport**: A vanilla SPA displaying live database telemetry, queue monitoring, and manual file uploads.
2. **REST Application Server**: A FastAPI server driving file ingestion, background queues, and data management.
3. **Local Inference Engine**: Quantized execution of speech-to-text (Whisper) and structured extraction (Phi-3 SLM) models.

---

## 1. Structural Layer Map

```
+-------------------------------------------------------------+
|                     Frontend Client SPA                     |
|              (HTML5 / CSS / Vanilla JavaScript)             |
+-------------------------------------------------------------+
                               |
                       REST API (Fetch)
                               |
                               v
+-------------------------------------------------------------+
|                 FastAPI Application Server                  |
|  - Ingestion Endpoints (/process, /upload)                  |
|  - Telemetry Monitor (/status, /health)                      |
|  - Queue Manager Daemon (Watchdog thread)                   |
+-------------------------------------------------------------+
          |                               |
          | Read / Write                  | Call Inference
          v                               v
+-------------------+           +-----------------------------+
|  SQLite Database  |           |   Offline Inference Engine  |
|  (WAL Mode Enabled|           |   - faster-whisper (Int8)   |
|   Timeout=30s)    |           |   - Phi-3 Instruct (Llama)  |
+-------------------+           +-----------------------------+
```

---

## 2. Component Directory Responsibilities

* **`backend/src/models/`**: Houses Pydantic structural validators representing the strict data contract.
* **`backend/src/database/`**: Manages connection pooling, WAL journal mode tuning, index declarations, and multi-table transactions.
* **`backend/src/engine/`**: Manages low-level CPU execution parameters for Whisper and llama.cpp, implementing OOM guardrails and mock fallbacks.
* **`backend/src/app/`**: Orchestrates file watching, handles lock states, and handles system resources statistics.
* **`backend/src/api/`**: Exposes dependency injectors and defines endpoints for user interactions.

---

## 3. Data Storage Strategy
To maintain performance on commodity hardware under concurrent reads and writes, SQLite is tuned to:
- Open in **Write-Ahead Logging (WAL)** mode, allowing readers to query database records without blocking writers.
- Establish database query connection context timeouts to prevent deadlocks and file corruption.
