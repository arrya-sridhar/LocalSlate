import time
import shutil
import hashlib
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
QUEUE_DIR = DATA_DIR / "queue"

class AudioFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix.lower() in [".wav", ".txt"]:
            self.process_new_file(file_path)

    def process_new_file(self, file_path: Path):
        # Wait a moment for the file to finish writing to disk
        time.sleep(1.0)
        
        if not file_path.exists():
            return

        try:
            # Hash file for unique ID
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            
            file_hash = hasher.hexdigest()
            queued_path = QUEUE_DIR / f"{file_hash}{file_path.suffix}"
            lock_path = QUEUE_DIR / f"{file_hash}.lock"

            # Move file to queue and create lock
            shutil.move(str(file_path), str(queued_path))
            lock_path.touch()

            # Trigger engine callback
            self.callback(queued_path, lock_path)

        except Exception as e:
            logging.error(f"Failed to ingest file {file_path}: {e}")

class QueueManager:
    def __init__(self, process_callback):
        self.process_callback = process_callback
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        self.observer = Observer()

    def start(self):
        handler = AudioFileHandler(self.process_callback)
        self.observer.schedule(handler, str(CACHE_DIR), recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
