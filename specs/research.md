# Architectural Research & Resource Constraints

## 1. Model Selection Justification

### Audio Transcription: `faster-whisper` (int8)
*   **Why not standard `whisper`?** Standard OpenAI Whisper relies heavily on PyTorch and is notably slow on CPUs. `faster-whisper` utilizes CTranslate2, which is highly optimized for CPU execution.
*   **Quantization:** Using `int8` quantization reduces the model footprint in RAM from ~1.5GB (Base model) to ~500MB, allowing it to easily fit within our aggressive hardware ceilings while maintaining a negligible degradation in Word Error Rate (WER).

### Semantic Structuring: `Phi-3-mini-4k-instruct-gguf`
*   **Why Phi-3?** Microsoft's Phi-3-mini (3.8B parameters) punches heavily above its weight, rivaling 7B models in reasoning and instruction-following. It is exceptionally capable of adhering to strict JSON output formats.
*   **Format:** We utilize the `.gguf` format running via `llama-cpp-python`. GGUF (GPT-Generated Unified Format) is specifically engineered for CPU inference (mmap support allows loading parts of the model from disk if needed, though we aim for full RAM loading).
*   **Context Window:** The `4k` variant is chosen to cap memory allocation. 4000 tokens are more than sufficient for transcribing a 15-minute field note and the system prompts.

## 2. Resource Constraints Analysis

The absolute system limit is **4GB RAM** and **4 CPU Threads**.

**Memory Budget Allocation:**
1.  **OS Overhead:** ~500MB (Assumed background noise)
2.  **faster-whisper (int8):** ~500MB RAM
3.  **Phi-3-mini-4k (Q4_K_M quant):** ~2.2GB RAM
4.  **App Shell & SQLite Overhead:** ~200MB RAM
*   **Total Expected Peak RAM:** ~3.4GB (Leaves a 600MB buffer before swap/OOM).

**Thread Bounding Rules:**
To prevent laptop freezing (OS lockups during heavy inference), we enforce hard thread caps:
*   Whisper Threading: Set `OMP_NUM_THREADS=2` in `os.environ`.
*   Llama-CPP Threading: Initialize with `n_threads=2`.
By locking each engine to 2 threads, they can run sequentially utilizing 50% of a quad-core CPU, or run concurrently while leaving 2 cores entirely free for the OS and the UI dashboard.
