import uvicorn
import sys
from pathlib import Path

# Resolve and add project root to python path to avoid import errors
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    print("Launching LocalSlate FastAPI Backend Server...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
