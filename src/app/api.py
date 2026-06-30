"""
LocalSlate API Server
FastAPI wrapper around the existing engine modules.
Provides REST endpoints for the web dashboard frontend.
"""
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Add project root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, UploadFile, File  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from src.engine.db import DatabaseEngine, init_db, get_latest_incidents  # noqa: E402
from src.engine.slm_processor import mock_extraction, IncidentReport  # noqa: E402

# Initialize logging
log_dir = PROJECT_ROOT / "data"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "localslate.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# Initialize database
init_db()

app = FastAPI(
    title="LocalSlate API",
    description="Zero-trust, offline-first intelligence processing pipeline API",
    version="1.0.0",
)

# CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "*",  # Allow all for hackathon demo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track startup time
START_TIME = time.time()


class TextIngestRequest(BaseModel):
    text: str
    source: Optional[str] = "web_upload"


class StatusResponse(BaseModel):
    is_running: bool
    uptime_seconds: float
    total_incidents: int
    pipeline_mode: str


@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


@app.get("/api/status")
def get_status():
    """Get system status for the dashboard."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_info = {
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "percent": mem.percent,
        }
        cpu_percent = psutil.cpu_percent(interval=0.1)
    except ImportError:
        ram_info = {"used_gb": 0, "total_gb": 0, "percent": 0}
        cpu_percent = 0

    incidents = get_latest_incidents(1000)
    total = len(incidents)

    return {
        "is_running": True,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_incidents": total,
        "pipeline_mode": "mock" if not (PROJECT_ROOT / ".models" / "slm" / "phi3-mini-4k.gguf").exists() else "live",
        "ram": ram_info,
        "cpu_percent": cpu_percent,
        "max_threads": 4,
    }


@app.get("/api/incidents")
def list_incidents(limit: int = 20):
    """Get the latest incidents from the database."""
    incidents = get_latest_incidents(limit)
    return {"incidents": incidents, "count": len(incidents)}


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    """Get a specific incident by ID."""
    incidents = get_latest_incidents(1000)
    for inc in incidents:
        if inc["incident_id"] == incident_id:
            return inc
    raise HTTPException(status_code=404, detail="Incident not found")


@app.post("/api/ingest/text")
def ingest_text(request: TextIngestRequest):
    """Process a text field note through the pipeline."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(text) > 4000:
        text = text[:4000]
        logging.warning("Input text truncated to 4000 characters")

    try:
        report_data = mock_extraction(text)
        report = IncidentReport(**report_data)
        validated = report.model_dump()

        db = DatabaseEngine()
        db.insert_incident(validated)

        logging.info(f"Ingested text report: {validated['incident_id'][:8]}...")
        return {
            "status": "success",
            "incident_id": validated["incident_id"],
            "priority": validated["computed_priority_level"],
            "summary": validated["system_summary"],
        }
    except Exception as e:
        logging.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Upload a .txt file for processing."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported via web upload")

    content = await file.read()
    text = content.decode("utf-8", errors="replace").strip()

    if not text:
        raise HTTPException(status_code=400, detail="File is empty")

    return ingest_text(TextIngestRequest(text=text, source=file.filename))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
