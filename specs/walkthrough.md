# Chronological Data Flow Trace (Walkthrough)

This document traces the complete lifecycle of a raw audio input through the Antigravity offline architecture.

## Step 1: File Drop & Ingestion
1.  A user (or an external offline device like a USB stick) drops a file named `field_report_alpha.wav` into the `data/cache/` directory.
2.  `src/app/queue_manager.py` detects the new file via a filesystem watcher (`watchdog`).
3.  The file is hashed to generate a unique ID (`uuid4` mapped to `incident_id`), moved to `data/queue/`, and a `.lock` file is established.

## Step 2: Local Audio Transcription
1.  The orchestrator passes the absolute `Path` of the queued `.wav` file to `src/engine/audio_processor.py`.
2.  `faster-whisper` (limited to 2 threads) loads the file and chunks it.
3.  The model outputs raw transcribed text. Example: *"Arrived at Sector 7. Found the secondary cooling array offline. Priority is high. Agent K and Operative J are investigating."*
4.  The `.wav` file is moved out of the queue and securely deleted to free disk space.

## Step 3: Prompt Construction & SLM Inference
1.  The transcribed text string is passed to `src/engine/slm_processor.py`.
2.  The engine wraps the text in the strict system prompt:
    *"You are an intelligence extractor. Read the following field note and output strictly a JSON object conforming to this schema... [SCHEMA INJECTED]... TEXT: [TRANSCRIPT INJECTED]"*
3.  `llama-cpp-python` loads the Phi-3 GGUF model and executes inference.
4.  The model streams back a raw string containing the JSON structure.

## Step 4: JSON Validation & Storage
1.  The raw string is stripped of any markdown formatting (e.g., ```json ... ```).
2.  The string is parsed via Python's `json.loads()` and validated using a Pydantic model enforcing our `data-model.md` definitions.
3.  If validation passes, the JSON object is passed to `src/engine/db.py`.
4.  A local SQLite transaction is initiated. The incident is inserted into the `incidents` table.
5.  Foreign key relationships are inserted: locations ("Sector 7") into `identified_locations`, personnel ("Agent K", "Operative J") into `identified_personnel`, and tasks ("Deploy secondary cooling array") into `actionable_tasks`.
6.  The transaction commits, the file lock is released, and the CLI dashboard flashes a success notification.
