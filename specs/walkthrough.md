# Chronological Data Flow Trace (Walkthrough)

This document traces the complete lifecycle of input processing through the LocalSlate full-stack architecture.

---

## Step 1: Input Ingestion
LocalSlate accepts input through two ingestion paths:
1. **File Ingestion (Background Queue)**:
   - A user uploads a file (`report.wav` or `notes.txt`) via the frontend upload panel, sending a `POST /upload` request to the backend.
   - The API writes the file to the `data/cache/` directory.
   - The `backend/src/app/queue_manager.py` daemon detects the file via a filesystem watcher (`watchdog`).
   - The file is hashed to generate a unique `incident_id`, moved to `data/queue/` for processing, and a `.lock` file is created to lock state.
2. **Direct Text Submission (Immediate)**:
   - A user types notes into the field portal and clicks **Run Extraction** (`POST /process`).
   - The API server bypasses the background file queue, running the SLM extraction synchronously on the request thread.

---

## Step 2: Local Audio Transcription (For Audio Files Only)
1. The background queue orchestrator passes the path of the queued `.wav` file to `backend/src/engine/audio_processor.py`.
2. `faster-whisper` (quantized to `int8`, running on 2 threads) transcribes the audio, or falls back to a structured mock transcript if the model is missing.
3. The raw audio file is immediately deleted (`unlinked`) from `data/queue/` to free disk space and prevent data retention risks.

---

## Step 3: SLM Extraction & Schema Structuring
1. The plain text (either from direct submission or audio transcription) is passed to `backend/src/engine/slm_processor.py`.
2. The processor wraps the text in a system prompt specifying the strict target JSON format.
3. `llama-cpp-python` loads the local Phi-3 GGUF model and executes inference (or falls back to mock regex extraction).
4. The model returns a formatted JSON string representing the incident details.

---

## Step 4: Schema Validation & Database Write
1. The JSON string is validated against the Pydantic models in `backend/src/models/models.py`.
2. The validated dictionary is passed to `backend/src/database/db.py`.
3. A transactional write is opened on the SQLite database in **Write-Ahead Logging (WAL)** mode.
4. The incident details, locations, personnel, and actionable tasks are inserted into the database.
5. The connection is committed and closed, the file lock is released, and the frontend updates its stream display on the next polling cycle.
