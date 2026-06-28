# ruff: noqa: E402
import sys
import time
import logging
from pathlib import Path

# Add project root to python path to avoid import errors
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Disable interactive outputs for child engines
log_dir = PROJECT_ROOT / "data"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "localslate.log", encoding="utf-8"),
    ],
)

from backend.src.database.db import (
    init_db,
    get_latest_incidents,
    DatabaseEngine,
    get_db_stats,
    clear_db,
)
from backend.src.app.queue_manager import (
    start_queue_manager,
    stop_queue_manager,
    queue_status,
    get_queue_length,
)
from backend.src.engine.audio_processor import WhisperProcessor
from backend.src.engine.slm_processor import SLMProcessor

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.align import Align

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class DashboardUI:
    def __init__(self):
        self.status = "Idle"
        self.db = DatabaseEngine()
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
                self.status = "Writing to database..."
                self.db.insert_incident(json_data)
        except Exception as e:
            logging.error(f"DashboardUI process_file error: {e}")
        finally:
            if lock_path.exists():
                lock_path.unlink()
            self.status = "Idle"


def generate_mock_text_file():
    cache_dir = PROJECT_ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report_text_alpha_{int(time.time())}.txt"
    filepath = cache_dir / filename
    content = (
        "FIELD NOTES: Temperature spike in Sector 7. Main node cooling array is offline. "
        "Agent K and Operative J are investigating the primary malfunction. "
        "Need to deploy secondary cooling array immediately."
    )
    filepath.write_text(content, encoding="utf-8")
    return filename


def generate_mock_audio_file():
    import wave
    import struct

    cache_dir = PROJECT_ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report_audio_beta_{int(time.time())}.wav"
    filepath = cache_dir / filename

    with wave.open(str(filepath), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        for _ in range(16000):
            wav.writeframesraw(struct.pack("<h", 0))
    return filename


def get_keypress():
    if sys.platform == "win32":
        import msvcrt

        if msvcrt.kbhit():
            ch = msvcrt.getch()
            try:
                if ch in (b"\x00", b"\xe0"):
                    msvcrt.getch()
                    return None
                return ch.decode("utf-8").lower()
            except UnicodeDecodeError:
                return None
    return None


def make_progress_bar(percentage: float, width: int = 15) -> str:
    filled = int(max(0.0, min(100.0, percentage)) / 100 * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    color = "green"
    if percentage > 85:
        color = "red"
    elif percentage > 60:
        color = "yellow"
    return f"[{color}]{bar}[/{color}] {percentage:.1f}%"


def check_ram_string():
    try:
        import psutil

        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        return f"{used_gb:.2f}/{total_gb:.2f} GB ({mem.percent}%)"
    except ImportError:
        return "Unknown"


def draw_header() -> Panel:
    table = Table.grid(expand=True)
    table.add_column("title")
    table.add_column("status", justify="right")

    title_text = Text.assemble(
        Text("🌌 LocalSlate  ", style="bold magenta"),
        Text("⬢  Zero-Trust Offline Incident Pipeline", style="cyan dim"),
    )
    status_text = Text.assemble(
        Text("🚫 NETWORK DISCONNECTED ", style="bold red"),
        Text(" ❘  ⚙️  threads: 4 max", style="dim white"),
        Text(" ❘  🕒 "),
        Text(time.strftime("%Y-%m-%d %H:%M:%S"), style="bold green"),
    )
    table.add_row(title_text, status_text)
    return Panel(table, border_style="magenta")


def draw_system_stats() -> Panel:
    text = Text()
    text.append("⚙️  SYSTEM MONITOR\n", style="bold yellow")

    try:
        import psutil

        cpu_usage = psutil.cpu_percent()
    except Exception:
        cpu_usage = 0.0
    text.append("• CPU Utilization: ", style="bold")
    text.append(f"{cpu_usage:.1f}%\n")
    text.append(f"  {make_progress_bar(cpu_usage)}\n\n")

    try:
        import psutil

        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_str = f"{mem.used / (1024**3):.2f}/{mem.total / (1024**3):.2f} GB"
    except Exception:
        ram_percent = 0.0
        ram_str = "Unknown"
    text.append("• RAM Allocation: ", style="bold")
    text.append(f"{ram_str}\n")
    text.append(f"  {make_progress_bar(ram_percent)}\n\n")

    text.append("📊 DATABASE STORAGE\n", style="bold yellow")
    stats = get_db_stats()
    text.append(f"• Total Saved Incidents: {stats['total']}\n", style="bold cyan")
    text.append("  ↳ ")
    text.append("🔴 Crit: ", style="red")
    text.append(f"{stats['CRITICAL']}  ")
    text.append("🟠 High: ", style="orange3")
    text.append(f"{stats['HIGH']}  ")
    text.append("🟡 Med: ", style="yellow")
    text.append(f"{stats['MEDIUM']}  ")
    text.append("🟢 Low: ", style="green")
    text.append(f"{stats['LOW']}\n")

    return Panel(
        text,
        border_style="yellow",
        title="[bold yellow]Resources & Storage[/bold yellow]",
    )


def draw_pipeline() -> Panel:
    text = Text()
    text.append("⚡ PIPELINE ORCHESTRATOR\n", style="bold cyan")

    manager_state = "ACTIVE 🟢" if queue_status["is_running"] else "STOPPED 🔴"
    manager_color = "green" if queue_status["is_running"] else "red"
    text.append("• Ingest Service: ", style="bold")
    text.append(manager_state + "\n", style=manager_color)

    q_len = get_queue_length()
    text.append("• Ingest Queue: ", style="bold")
    text.append(
        f"{q_len} files pending\n", style="bold yellow" if q_len > 0 else "white"
    )

    curr_file = queue_status["current_file"]
    text.append("• Active File:  ", style="bold")
    if curr_file:
        text.append(f"{curr_file}\n", style="bold magenta")
    else:
        text.append("Idle\n", style="dim white")

    stage_obj = queue_status.get("current_stage", 0)
    stage = int(stage_obj) if isinstance(stage_obj, (int, float)) else 0
    text.append("\n📈 PROCESSING TIMELINE\n", style="bold cyan")

    s1_style = (
        "bold blink cyan" if stage == 1 else ("bold cyan" if stage > 1 else "dim white")
    )
    text.append(" Ingest 📥 ", style=s1_style)
    text.append("➔", style="dim white")

    s2_style = (
        "bold blink magenta"
        if stage == 2
        else ("bold magenta" if stage > 2 else "dim white")
    )
    text.append(" Whisper 🎙️ ", style=s2_style)
    text.append("➔", style="dim white")

    s3_style = (
        "bold blink yellow"
        if stage == 3
        else ("bold yellow" if stage > 3 else "dim white")
    )
    text.append(" Phi-3 🧠 ", style=s3_style)
    text.append("➔", style="dim white")

    s4_style = (
        "bold blink green"
        if stage == 4
        else ("bold green" if stage > 4 else "dim white")
    )
    text.append(" Store 💾 \n\n", style=s4_style)

    status_msg = queue_status["current_status"]
    text.append("• Current Action: ", style="bold")
    if status_msg != "Idle":
        text.append(f"{status_msg} ", style="bold yellow")
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spin_idx = int(time.time() * 5) % len(spinners)
        text.append(spinners[spin_idx], style="bold yellow")
        text.append("\n")
    else:
        text.append("Awaiting input...\n", style="dim white")

    text.append("\n📊 PIPELINE METRICS\n", style="bold cyan")
    text.append("✓ Processed Success: ", style="bold green")
    text.append(f"{queue_status['processed_count']}\n")
    text.append("✗ Processed Failures: ", style="bold red")
    text.append(f"{queue_status['failed_count']}\n")

    return Panel(
        text, border_style="cyan", title="[bold cyan]Pipeline Monitor[/bold cyan]"
    )


def draw_incidents() -> Panel:
    incidents = get_latest_incidents(5)

    if not incidents:
        text = Text("\n\n📭 Database is Empty\n", style="bold yellow justify=center")
        text.append(
            "Drop text/audio files, or press [T]/[A] to ingest mock data.",
            style="dim white justify=center",
        )
        return Panel(
            Align.center(text, vertical="middle"),
            border_style="green",
            title="[bold green]Database Stream[/bold green]",
        )

    table = Table(expand=True)
    table.add_column("ID (Hash)", style="dim", width=10)
    table.add_column("Timestamp", width=19)
    table.add_column("Priority", width=12)
    table.add_column("Locations", width=16)
    table.add_column("Personnel", width=16)
    table.add_column("System Summary", style="white")

    for inc in incidents:
        priority = inc["computed_priority_level"]
        if priority == "CRITICAL":
            p_text = Text("🔴 CRITICAL", style="bold red")
        elif priority == "HIGH":
            p_text = Text("🟠 HIGH", style="bold orange3")
        elif priority == "MEDIUM":
            p_text = Text("🟡 MEDIUM", style="yellow")
        elif priority == "LOW":
            p_text = Text("🟢 LOW", style="green")
        else:
            p_text = Text(f"⚪ {priority}", style="white")

        locations = ", ".join(inc["identified_entities"]["locations"])
        personnel = ", ".join(inc["identified_entities"]["personnel"])

        table.add_row(
            inc["incident_id"][:8] + "...",
            inc["iso_timestamp"][:19].replace("T", " "),
            p_text,
            locations if locations else "N/A",
            personnel if personnel else "N/A",
            inc["system_summary"],
        )

    return Panel(
        table,
        border_style="green",
        title="[bold green]Database Stream (Latest 5)[/bold green]",
    )


def draw_footer(message: str = "") -> Panel:
    table = Table.grid(expand=True)
    table.add_column("shortcuts")
    table.add_column("msg", justify="right")

    shortcuts = Text()
    shortcuts.append("[Q]", style="bold red")
    shortcuts.append(" Quit  ❘  ", style="white")
    shortcuts.append("[T]", style="bold green")
    shortcuts.append(" Ingest Text  ❘  ", style="white")
    shortcuts.append("[A]", style="bold blue")
    shortcuts.append(" Ingest WAV Audio  ❘  ", style="white")
    shortcuts.append("[C]", style="bold yellow")
    shortcuts.append(" Clear Database 🧹", style="white")

    msg_text = Text(
        message,
        style=(
            "bold green"
            if ("Success" in message or "Cleared" in message or "Purged" in message)
            else "bold yellow"
        ),
    )

    table.add_row(shortcuts, msg_text)
    return Panel(table, border_style="cyan")


def main():
    if not HAS_RICH:
        print("Error: The 'rich' library is required to run the LocalSlate Dashboard.")
        print("Please install dependencies: pip install rich psutil pydantic")
        sys.exit(1)

    init_db()
    start_queue_manager()

    console = Console()
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="system", ratio=5),
        Layout(name="pipeline", ratio=6),
        Layout(name="incidents", ratio=11),
    )

    console.print("[green]Launching LocalSlate CLI Dashboard...[/green]")

    message = ""
    message_time = 0.0

    try:
        with Live(layout, screen=True, refresh_per_second=4):
            while True:
                layout["header"].update(draw_header())
                layout["system"].update(draw_system_stats())
                layout["pipeline"].update(draw_pipeline())
                layout["incidents"].update(draw_incidents())

                msg_display = message if time.time() - message_time < 3.0 else ""
                layout["footer"].update(draw_footer(msg_display))

                kp = get_keypress()
                if kp == "q":
                    break
                elif kp == "t":
                    fname = generate_mock_text_file()
                    message = f"Success: Ingested {fname} into cache."
                    message_time = time.time()
                elif kp == "a":
                    fname = generate_mock_audio_file()
                    message = f"Success: Ingested WAV {fname} into cache."
                    message_time = time.time()
                elif kp == "c":
                    clear_db()
                    message = "Success: Purged database records."
                    message_time = time.time()

                time.sleep(0.1)
    finally:
        stop_queue_manager()
        console.clear()
        print("LocalSlate ingestion background pipeline stopped. Goodbye.")


if __name__ == "__main__":
    main()
