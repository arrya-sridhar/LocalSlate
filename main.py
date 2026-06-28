import sys
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional

# Add project root to python path to avoid import errors
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe imports
init_db: Optional[Callable[[], Any]] = None
get_latest_incidents: Optional[Callable[..., Any]] = None
start_queue_manager: Optional[Callable[[], None]] = None
stop_queue_manager: Optional[Callable[[], None]] = None
queue_status: Optional[Dict[str, Any]] = None
get_queue_length: Optional[Callable[[], int]] = None

try:
    from src.engine.db import (
        init_db as _init_db,
        get_latest_incidents as _get_latest_incidents,
    )

    init_db = _init_db
    get_latest_incidents = _get_latest_incidents
except Exception:
    pass

try:
    from src.app.queue_manager import (
        start_queue_manager as _start_queue_manager,
        stop_queue_manager as _stop_queue_manager,
        queue_status as _queue_status,
        get_queue_length as _get_queue_length,
    )

    start_queue_manager = _start_queue_manager
    stop_queue_manager = _stop_queue_manager
    queue_status = _queue_status
    get_queue_length = _get_queue_length
except Exception:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and start queue manager if available
    if init_db is not None:
        try:
            init_db()
        except Exception as e:
            print(f"Failed to initialize database: {e}")

    if start_queue_manager is not None:
        try:
            start_queue_manager()
        except Exception as e:
            print(f"Failed to start queue manager: {e}")

    yield

    # Shutdown: Stop queue manager if available
    if stop_queue_manager is not None:
        try:
            stop_queue_manager()
        except Exception as e:
            print(f"Failed to stop queue manager: {e}")


app = FastAPI(
    title="LocalSlate API",
    description="Minimal FastAPI web wrapper demo for LocalSlate offline-first pipeline",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {
        "app": "LocalSlate",
        "status": "online",
        "message": "This is a local, offline-first incident processing pipeline demo. Offline AI inference runs locally.",
    }


@app.get("/health")
def health_check():
    return {"ok": True}


@app.get("/status")
def get_status():
    if queue_status is None:
        return {"error": "Queue manager is not available or failed to import."}
    try:
        status_copy = dict(queue_status)
        if get_queue_length is not None:
            status_copy["queue_count"] = get_queue_length()
        return status_copy
    except Exception as e:
        return {"error": f"Failed to retrieve queue status: {str(e)}"}


@app.get("/incidents")
def get_incidents(limit: int = 5):
    if get_latest_incidents is None:
        return {"error": "Database engine is not available or failed to import."}
    try:
        incidents = get_latest_incidents(limit=limit)
        return incidents
    except Exception as e:
        return {"error": f"Failed to fetch incidents: {str(e)}"}
