# Work Breakdown & Tasks

The project is split cleanly into two domains: `src/engine/` (Inference & Storage) and `src/app/` (Shell & Pipelines).

## Task Distribution Matrix

| Developer | Domain | Core Responsibilities | Target Directory |
| :--- | :--- | :--- | :--- |
| **Developer 1** | Engine Core | Whisper Transcription, Phi-3 Structuring, SQLite ORM/Execution | `src/engine/` |
| **Developer 2** | App Shell | CLI/Dashboard UI, Queueing, Caching, CI/CD DevOps rules | `src/app/` |

---

## Granular GitLab Issues

### Developer 1: AI Inference Core (Issues 1-3)

**Issue 1: Implement Local Whisper Engine Wrapper**
*   **Description:** Build the `faster-whisper` ingestion wrapper in `src/engine/audio_processor.py`. Ensure model loading uses `int8` quantization and strictly enforces the 2 CPU thread limit via environment flags. Must include error handling for files > 25MB.
*   **Assignee:** Developer 1
*   **Effort:** 3 Hours
*   **Due Date:** Today

**Issue 2: SLM JSON Constraint Wrapper**
*   **Description:** Implement `src/engine/slm_processor.py` utilizing `llama-cpp-python` and the Phi-3-mini GGUF. Construct the precise prompt template to force the output into the defined JSON Incident Schema. Implement a retry loop (max 3 tries) if the output fails JSON parsing.
*   **Assignee:** Developer 1
*   **Effort:** 4 Hours
*   **Due Date:** Today

**Issue 3: SQLite Storage & DDL Execution**
*   **Description:** Implement `src/engine/db.py`. Write the initialization function that executes the `CREATE TABLE` blocks on startup if the `.db` file doesn't exist. Implement the `insert_incident(json_data)` function using safe parameterized SQL to prevent injection.
*   **Assignee:** Developer 1
*   **Effort:** 2 Hours
*   **Due Date:** Today

---

### Developer 2: App Shell & Pipelines (Issues 4-6)

**Issue 4: Local Caching & Ingestion Queue Pipeline**
*   **Description:** Build `src/app/queue_manager.py`. Create the logic to monitor the `data/cache/` directory. When a file arrives, hash it, move it to `data/queue/`, and pass the Path to the Engine. Handle lockfiles to prevent concurrent reads.
*   **Assignee:** Developer 2
*   **Effort:** 3 Hours
*   **Due Date:** Today

**Issue 5: App Shell Dashboard CLI**
*   **Description:** Build a clean, curses-based or Rich-based CLI dashboard in `src/app/dashboard.py`. It should display real-time queue length, current inference status (e.g., "Transcribing...", "Structuring..."), and a stream of the latest 5 incidents written to the DB.
*   **Assignee:** Developer 2
*   **Effort:** 4 Hours
*   **Due Date:** Today

**Issue 6: 10-Check DevOps CI Configuration (Local Pre-commit)**
*   **Description:** Configure a `.pre-commit-config.yaml` with 10 strict checks (e.g., black formatting, ruff linting, trailing whitespaces, end-of-file fixers, large file size checks to prevent accidental model commits). This ensures zero garbage gets committed to the shared git history.
*   **Assignee:** Developer 2
*   **Effort:** 2 Hours
*   **Due Date:** Today
