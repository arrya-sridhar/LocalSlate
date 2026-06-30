# Project Plan & Team Parity Strategy

## 1. Environment Parity Strategy (2-Man Distributed Team)
Working offline requires strict guarantees that code behaving correctly on Developer 1's laptop behaves identically on Developer 2's laptop.
*   **Dependency Pinning:** The project uses `uv` for lightning-fast deterministic builds. A `requirements.txt` with absolute hashes is mandatory.
*   **Python Version:** Strictly pinned to Python 3.11.x to ensure native C-bindings for SQLite and `llama-cpp-python` compile identically.
*   **Virtual Environments:** Both devs must run in a `.venv` located at the project root.

## 2. Cross-Platform Path Portability (The Pathlib Rule)
Hardcoded paths (`/Users/..` or `C:\...`) are strictly prohibited. 
*   **Rule:** All file I/O must utilize Python's `pathlib.Path`.
*   **Base Anchor:** The project root is dynamically determined at runtime:
```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
MODELS_DIR = PROJECT_ROOT / ".models"
DB_PATH = PROJECT_ROOT / "data" / "localslate.db"
```
This guarantees the code executes flawlessly regardless of where the repo is cloned locally.

## 3. Git-Ignore & State Isolation Strategy
Model binaries and local DB states are massive, environment-specific, and conflict-prone. They must never enter Git history.

**`.gitignore` Definition:**
```gitignore
# Python
__pycache__/
*.py[cod]
.venv/

# LocalSlate Local State
data/*.db
data/*.sqlite3
data/cache/
data/queue/
data/failed_audio/

# Massive Model Binaries
.models/whisper/*
.models/slm/*

# OS generated files
.DS_Store
Thumbs.db
```

By ensuring `.models/` and `data/` are git-ignored, we achieve **zero-conflict Git integration**, allowing Developer 1 to update DB schemas while Developer 2 works on the UI, with neither accidentally overriding the other's local state.
