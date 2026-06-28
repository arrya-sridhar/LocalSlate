# ruff: noqa: E402
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Resolve and add project root to python path to avoid import errors
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.database.db import init_db
from backend.src.app.queue_manager import start_queue_manager, stop_queue_manager
from backend.src.api.routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle events
    try:
        init_db()
    except Exception as e:
        print(f"Failed to initialize database: {e}")

    try:
        start_queue_manager()
    except Exception as e:
        print(f"Failed to start queue manager: {e}")

    yield

    # Shutdown lifecycle events
    try:
        stop_queue_manager()
    except Exception as e:
        print(f"Failed to stop queue manager: {e}")


app = FastAPI(
    title="LocalSlate API",
    description="Refactored, production-ready backend for zero-trust offline-first intelligence processing.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Include routes
app.include_router(router)

# Mount frontend directories as static files
FRONTEND_DIR = PROJECT_ROOT / "frontend"
if FRONTEND_DIR.exists():
    css_dir = FRONTEND_DIR / "css"
    js_dir = FRONTEND_DIR / "js"
    assets_dir = FRONTEND_DIR / "assets"

    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
