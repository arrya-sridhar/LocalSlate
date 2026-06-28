import os
import sys
import time
import threading
import sqlite3
from pathlib import Path
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align

# Import engine and pipeline components
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.app.queue_manager import QueueManager
from src.engine.db import DatabaseEngine, DB_PATH
from src.engine.audio_processor import WhisperProcessor
from src.engine.slm_processor import SLMProcessor

class DashboardUI:
    def __init__(self):
        self.status = "Idle"
        self.db = DatabaseEngine()
        
        # We will lazy-load the processors so the UI starts instantly
        self.whisper = None
        self.slm = None

    def initialize_models(self):
        if self.whisper is None:
            self.status = "Loading Whisper (int8)..."
            self.whisper = WhisperProcessor()
        if self.slm is None:
            self.status = "Loading Phi-3 (4k)..."
            self.slm = SLMProcessor()
        self.status = "Idle"

    def process_file(self, file_path: Path, lock_path: Path):
        self.initialize_models()
        try:
            transcription = ""
            if file_path.suffix.lower() == ".wav":
                self.status = f"Transcribing: {file_path.name}"
                transcription = self.whisper.transcribe(file_path)
            elif file_path.suffix.lower() == ".txt":
                transcription = file_path.read_text(encoding="utf-8")
            
            if transcription:
                self.status = "Extracting JSON schema..."
                json_data = self.slm.extract_incident(transcription)
                
                self.status = "Writing to Database..."
                self.db.insert_incident(json_data)
            
        except Exception as e:
            # A robust logger would log to a file here
            pass
        finally:
            self.status = "Idle"
            # Cleanup
            if lock_path.exists():
                lock_path.unlink()
            if file_path.exists():
                file_path.unlink()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main")
        )

        # Header: Queue Length and Status
        queue_dir = PROJECT_ROOT / "data" / "queue"
        queue_len = len(list(queue_dir.glob("*.lock"))) if queue_dir.exists() else 0
        
        header_text = f"Antigravity Dashboard | Queue: {queue_len} | Status: {self.status}"
        layout["header"].update(Panel(Align.center(header_text), style="bold blue"))

        # Main: Recent Incidents Table
        table = Table(title="Recent Incidents (SQLite)", expand=True)
        table.add_column("Timestamp", style="cyan")
        table.add_column("Priority", style="magenta")
        table.add_column("Summary", style="green")

        if DB_PATH.exists():
            try:
                with sqlite3.connect(str(DB_PATH)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT iso_timestamp, computed_priority_level, system_summary FROM incidents ORDER BY created_at DESC LIMIT 5")
                    rows = cursor.fetchall()
                    for row in rows:
                        table.add_row(row[0], row[1], row[2][:50] + "..." if len(row[2]) > 50 else row[2])
            except Exception:
                pass

        layout["main"].update(Panel(table, border_style="green"))
        return layout

if __name__ == "__main__":
    ui = DashboardUI()
    manager = QueueManager(process_callback=ui.process_file)
    manager.start()

    print("Starting Antigravity Dashboard. Press Ctrl+C to exit.")
    try:
        with Live(ui.generate_layout(), refresh_per_second=2) as live:
            while True:
                live.update(ui.generate_layout())
                time.sleep(0.5)
    except KeyboardInterrupt:
        manager.stop()
        print("Shutdown complete.")
