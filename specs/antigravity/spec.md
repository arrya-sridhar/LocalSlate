# Antigravity - Technical Core Specification

## 1. System Boundaries and Scope Constraints
Antigravity is engineered as a zero-trust, offline-first application. The core objective is processing unstructured field notes (audio and text) into structured actionable intelligence strictly on local commodity hardware.

### Constraints:
*   **Network Isolation:** The system must operate with zero outbound network calls during runtime execution. All model weights, binaries, and inference logic must reside locally.
*   **Hardware Ceiling:** Target execution environment is a standard dual-core or quad-core laptop. The entire application stack (UI, DB, Inference engines) must fit within a **4GB RAM** overhead and utilize a maximum of **4 CPU threads**.
*   **Storage:** Ephemeral data (raw audio) is aggressively pruned post-processing. Persistent data lives exclusively in a local SQLite database (`.db` files).

## 2. Process Flow: CPU-Bound Inference Architecture
The system employs a tandem offline-inference pipeline:
1.  **Ingestion:** The local Python daemon watches the cache directory for `.wav` or `.txt` inputs.
2.  **Transcription (Audio only):** Audio is routed to `faster-whisper` (int8 quantized). Execution is pinned to a maximum of 2 CPU threads using `OMP_NUM_THREADS=2`.
3.  **Semantic Structuring:** Raw text (or transcribed text) is passed to `Phi-3-mini-4k-instruct-gguf` via `llama-cpp-python`. The wrapper enforces strict JSON output schema generation. The SLM is allocated a maximum of 2 CPU threads.
4.  **Storage:** The structured JSON is parsed, validated against the Pydantic model, and written to the SQLite DB via parameterized queries.

## 3. Fallback Behaviors and Offline Caching
Spikes in local processing latency are handled through a resilient disk-backed queue:
*   **Queuing:** If the system is currently processing a file and another is ingested, the new file is hashed and placed in a local `queue/` directory.
*   **Timeout & Degradation:** If Whisper transcription exceeds 120 seconds for a file < 5MB, the system gracefully degrades by storing the raw file in a `failed_audio/` bucket and logging an incomplete entry to the DB with priority `PENDING_REVIEW`.
*   **OOM Protection:** A background watchdog monitors the process RAM. If it approaches the 3.8GB threshold, the SLM context window is aggressively truncated, or the current inference is aborted and pushed back to the queue with a backoff flag.
