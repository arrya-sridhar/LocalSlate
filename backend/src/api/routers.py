import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.src.api.dependencies import get_db, get_slm
from backend.src.database.db import DatabaseService
from backend.src.engine.slm_processor import SLMService
from backend.src.app.queue_manager import queue_status, get_queue_length, CACHE_DIR

router = APIRouter()

# Root paths resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


class ProcessRequest(BaseModel):
    text: str = Field(
        ..., max_length=4000, description="Field report text note to process"
    )


@router.get("/")
def read_root():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        status_code=404,
        content={
            "app": "LocalSlate",
            "status": "online",
            "message": "Frontend index.html was not found. API is fully running.",
        },
    )


@router.get("/health")
def health_check(db: DatabaseService = Depends(get_db)):
    try:
        # Check SQLite connection
        conn = db.get_connection()
        conn.close()
        db_ok = True
    except Exception as e:
        logging.error(f"Health check failed database check: {e}")
        db_ok = False

    return {
        "ok": db_ok,
        "database": "connected" if db_ok else "error",
        "offline_mode": True,
    }


@router.get("/status")
def get_status(db: DatabaseService = Depends(get_db)):
    try:
        # Load CPU & RAM metrics safely
        cpu_usage = 0.0
        ram_percent = 0.0
        ram_used = 0.0
        ram_total = 0.0
        try:
            import psutil

            cpu_usage = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            ram_percent = mem.percent
            ram_used = mem.used / (1024**3)
            ram_total = mem.total / (1024**3)
        except Exception:
            pass

        # Load SQLite stats
        stats = db.get_db_stats()

        status_copy = dict(queue_status)
        status_copy["queue_count"] = get_queue_length()
        status_copy["cpu_utilization"] = cpu_usage
        status_copy["ram_percent"] = ram_percent
        status_copy["ram_gb_used"] = ram_used
        status_copy["ram_gb_total"] = ram_total
        status_copy["db_stats"] = stats
        return status_copy
    except Exception as e:
        logging.error(f"Failed to fetch queue status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to retrieve queue status: {str(e)}"},
        )


@router.get("/incidents")
def get_incidents(limit: int = 10, db: DatabaseService = Depends(get_db)):
    try:
        incidents = db.get_latest_incidents(limit=limit)
        return incidents
    except Exception as e:
        logging.error(f"Failed to fetch incidents: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch incidents: {str(e)}"},
        )


@router.delete("/incidents")
def clear_incidents(db: DatabaseService = Depends(get_db)):
    try:
        db.clear_db()
        return {
            "status": "success",
            "message": "Database records cleared successfully.",
        }
    except Exception as e:
        logging.error(f"Failed to clear incidents: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to clear incidents: {str(e)}"},
        )


@router.post("/process")
def process_text(
    request: ProcessRequest,
    db: DatabaseService = Depends(get_db),
    slm: SLMService = Depends(get_slm),
):
    try:
        report = slm.extract_incident(request.text)
        db.insert_incident(report)
        return report
    except Exception as e:
        logging.error(f"Failed to process text incident directly: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process text report: {str(e)}"},
        )


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in [".txt", ".wav"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix}. Only .txt and .wav files are allowed.",
        )

    # Validate file size for wav
    if suffix == ".wav":
        # We write to temp or stream validation. We'll validate after saving to CACHE_DIR.
        pass

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        filename = file.filename if file.filename else "uploaded_file"
        dest_path = CACHE_DIR / filename

        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logging.info(f"File {filename} uploaded and saved to ingestion cache.")
        return {"filename": filename, "status": "queued"}
    except Exception as e:
        logging.error(f"Failed to upload file: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"File upload failed: {str(e)}"},
        )
