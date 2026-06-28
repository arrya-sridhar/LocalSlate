import os
import shutil
import uuid
import time
import logging
import threading
from pathlib import Path
from src.engine.audio_processor import transcribe_audio, validate_audio_file
from src.engine.slm_processor import structure_text
from src.engine.db import insert_incident

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
QUEUE_DIR = PROJECT_ROOT / "data" / "queue"
FAILED_DIR = PROJECT_ROOT / "data" / "failed_audio"

# Ensure directories exist
for d in [CACHE_DIR, QUEUE_DIR, FAILED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Global status tracking for the dashboard
queue_status = {
    "is_running": False,
    "current_file": None,
    "current_status": "Idle",
    "queue_count": 0,
    "processed_count": 0,
    "failed_count": 0
}

def get_queue_length():
    try:
        # Count non-lock files in queue directory
        files = [f for f in QUEUE_DIR.iterdir() if f.is_file() and not f.name.endswith(".lock")]
        return len(files)
    except Exception:
        return 0

def run_with_timeout(func, args, timeout):
    res = [None]
    err = [None]
    
    def target():
        try:
            res[0] = func(*args)
        except Exception as e:
            err[0] = e
            
    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, TimeoutError(f"Task exceeded timeout of {timeout} seconds")
    if err[0] is not None:
        return None, err[0]
    return res[0], None

def process_file(file_path: Path):
    incident_id = str(uuid.uuid4())
    lock_path = QUEUE_DIR / f"{incident_id}.lock"
    
    # Establish lockfile
    lock_path.touch()
    
    # Determine type and target path
    suffix = file_path.suffix.lower()
    dest_path = QUEUE_DIR / f"{incident_id}{suffix}"
    
    # Move to queue folder
    try:
        shutil.move(str(file_path), str(dest_path))
    except Exception as e:
        logging.error(f"Failed to move file to queue: {e}")
        if lock_path.exists():
            lock_path.unlink()
        return

    queue_status["current_file"] = dest_path.name
    
    try:
        if suffix == ".wav":
            # Audio pipeline
            queue_status["current_status"] = "Transcribing..."
            logging.info(f"Processing audio incident {incident_id}...")
            
            # Transcription with 120s timeout limit
            transcript, err = run_with_timeout(transcribe_audio, (dest_path,), 120.0)
            
            if err:
                logging.error(f"Audio processing error/timeout: {err}")
                raise err
                
            queue_status["current_status"] = "Structuring..."
            report = structure_text(transcript)
            report["incident_id"] = incident_id
            
            queue_status["current_status"] = "Saving to Database..."
            insert_incident(report)
            queue_status["processed_count"] += 1
            
        elif suffix == ".txt":
            # Text pipeline
            queue_status["current_status"] = "Reading Text..."
            logging.info(f"Processing text incident {incident_id}...")
            
            # Read plain text with max 4000 char validation
            with open(dest_path, "r", encoding="utf-8") as f:
                text = f.read(4010)
                
            if len(text) > 4000:
                logging.warning(f"Text file exceeds 4000 char limit. Truncating.")
                text = text[:4000]
                
            queue_status["current_status"] = "Structuring..."
            report = structure_text(text)
            report["incident_id"] = incident_id
            
            queue_status["current_status"] = "Saving to Database..."
            insert_incident(report)
            
            # Delete text file post-processing
            dest_path.unlink()
            queue_status["processed_count"] += 1
            
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
            
    except Exception as e:
        logging.error(f"Failed to process incident {incident_id}: {e}")
        queue_status["failed_count"] += 1
        
        # Save failed files for review
        if dest_path.exists():
            failed_dest = FAILED_DIR / dest_path.name
            try:
                shutil.move(str(dest_path), str(failed_dest))
            except Exception as move_err:
                logging.error(f"Could not move failed file to failed folder: {move_err}")
                
        # Insert PENDING_REVIEW placeholder in database
        try:
            fallback_report = {
                "incident_id": incident_id,
                "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "computed_priority_level": "PENDING_REVIEW",
                "system_summary": f"FAILED PROCESSING: {str(e)[:200]}",
                "identified_entities": {
                    "locations": [],
                    "personnel": []
                },
                "actionable_tasks": []
            }
            insert_incident(fallback_report)
        except Exception as db_err:
            logging.error(f"Failed to write failed record to database: {db_err}")
            
    finally:
        # Release lockfile
        if lock_path.exists():
            lock_path.unlink()
        queue_status["current_file"] = None
        queue_status["current_status"] = "Idle"

def poll_cache():
    while queue_status["is_running"]:
        try:
            # Poll CACHE_DIR for new files
            files = [f for f in CACHE_DIR.iterdir() if f.is_file() and f.suffix.lower() in [".wav", ".txt"]]
            queue_status["queue_count"] = get_queue_length() + len(files)
            
            for file in files:
                # Basic check to avoid reading files while writing is in progress
                initial_size = file.stat().st_size
                time.sleep(0.5)
                if file.exists() and file.stat().st_size == initial_size:
                    process_file(file)
                    
        except Exception as e:
            logging.error(f"Error in poll_cache loop: {e}")
            
        time.sleep(1.0)

def start_queue_manager():
    if not queue_status["is_running"]:
        queue_status["is_running"] = True
        t = threading.Thread(target=poll_cache, name="QueueManagerThread")
        t.daemon = True
        t.start()
        logging.info("Queue Manager started.")

def stop_queue_manager():
    queue_status["is_running"] = False
    logging.info("Queue Manager stopped.")
