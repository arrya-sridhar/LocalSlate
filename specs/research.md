# Architectural Research & Resource Constraints

## 1. Model Selection Justification

### Audio Transcription: `faster-whisper` (int8)
*   **Why not standard `whisper`?** Standard OpenAI Whisper relies heavily on PyTorch and is slow on CPU hardware. `faster-whisper` utilizes CTranslate2, which is optimized for CPU execution.
*   **Quantization:** Using `int8` quantization reduces the model footprint in RAM to ~500MB, allowing it to fit within our hardware ceilings.

### Semantic Structuring: `Phi-3-mini-4k-instruct-gguf`
*   **Why Phi-3?** Microsoft's Phi-3-mini (3.8B parameters) is capable of adhering to strict JSON output formats.
*   **Format:** We utilize the `.gguf` format running via `llama-cpp-python`. GGUF is engineered for local CPU inference.
*   **Context Window:** The `4k` variant is chosen to cap memory allocation. 4000 tokens are sufficient for transcribing a field note.

## 2. Resource Constraints Analysis

The absolute system limit is **4GB RAM** and **4 CPU Threads**.

**Memory Budget Allocation:**
1.  **OS Overhead:** ~500MB
2.  **faster-whisper (int8):** ~500MB RAM
3.  **Phi-3-mini-4k (Q4_K_M quant):** ~2.2GB RAM
4.  **App Shell & SQLite Overhead:** ~200MB RAM
*   **Total Expected Peak RAM:** ~3.4GB (Leaves a 600MB buffer before OOM).

**Thread Bounding Rules:**
We enforce hard thread caps to prevent CPU starvation:
*   Whisper Threading: Set `OMP_NUM_THREADS=2` in `os.environ`.
*   Llama-CPP Threading: Initialize with `n_threads=2`.
By locking each engine to 2 threads, they can run sequentially utilizing 50% of a quad-core CPU, leaving resources free for the OS and the UI dashboard.
