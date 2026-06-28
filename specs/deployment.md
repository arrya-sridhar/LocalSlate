# Deployment Specification

LocalSlate is optimized to deploy across three different execution modes: local offline runs (with full AI binaries), headless server runs, and lightweight cloud deployments (e.g. Render).

---

## 1. Local Offline Deployment
This is the high-performance offline deployment mode using local hardware:
- **Prerequisites**: Python 3.11, local folders created, and model binaries placed in `.models/`.
- **Command**:
  ```bash
  .venv\Scripts\uvicorn backend.main:app --reload
  ```
- **Inference Hardware Bounds**:
  - Whisper uses 2 threads (`OMP_NUM_THREADS=2`).
  - Phi-3 uses 2 threads (`n_threads=2`).
  - Total Peak RAM: ~3400 MB.

---

## 2. Render Cloud Deployment
Render represents an API showcase and web demo wrapper deployment:
- **Platform Strategy**: Because cloud containers typically lack CPU threads or memory capacity for heavy GGUF and faster-whisper execution, Render utilizes the structured mock extraction fallback.
- **Render Configurations**:
  - **Build Command**: `pip install uv && uv pip install -r backend/requirements-render.txt`
  - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
  - **Environment Variables**: Set `PORT` to bind correctly.
- **轻量级 Dependencies**: Utilizes `backend/requirements-render.txt`, preventing compile failures of `llama-cpp-python` and resource-heavy downloads.
