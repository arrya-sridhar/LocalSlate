import pytest
import sqlite3
from pathlib import Path

from src.engine.db import DatabaseEngine
from src.engine.audio_processor import validate_audio_file
from src.engine.slm_processor import mock_extraction
from src.engine.models import IncidentReport


def test_db_initialization(tmp_path):
    # Test DB path
    test_db_path = tmp_path / "test_localslate.db"

    db_engine = DatabaseEngine()
    db_engine.db_path = test_db_path
    db_engine.initialize()

    assert test_db_path.exists()

    conn = sqlite3.connect(str(test_db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()

    assert "incidents" in tables
    assert "identified_locations" in tables
    assert "identified_personnel" in tables
    assert "actionable_tasks" in tables


def test_pydantic_schema_validation():
    text = "Report from Sector 7 by Agent K. Cooling array offline."
    data = mock_extraction(text)

    report = IncidentReport(**data)

    assert report.computed_priority_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "Sector 7" in report.identified_entities.locations
    assert "Agent K" in report.identified_entities.personnel
    assert len(report.actionable_tasks) > 0


def test_audio_processor_file_not_found():
    non_existent = Path("data/non_existent_file.wav")
    with pytest.raises(FileNotFoundError):
        validate_audio_file(non_existent)


def test_audio_processor_size_limit(tmp_path):
    large_file = tmp_path / "large.wav"
    # Write 26MB of dummy bytes to exceed the 25MB limit
    with open(large_file, "wb") as f:
        f.write(b"\0" * (26 * 1024 * 1024))

    with pytest.raises(ValueError, match="exceeds the 25MB limit"):
        validate_audio_file(large_file)


def test_integration_pipeline_txt(tmp_path, monkeypatch):
    test_cache = tmp_path / "cache"
    test_queue = tmp_path / "queue"
    test_failed = tmp_path / "failed_audio"
    test_db = tmp_path / "localslate.db"

    test_cache.mkdir()
    test_queue.mkdir()
    test_failed.mkdir()

    import src.engine.db as db_mod
    import src.app.queue_manager as qm_mod

    monkeypatch.setattr(db_mod, "DB_PATH", test_db)
    monkeypatch.setattr(qm_mod, "CACHE_DIR", test_cache)
    monkeypatch.setattr(qm_mod, "QUEUE_DIR", test_queue)
    monkeypatch.setattr(qm_mod, "FAILED_DIR", test_failed)

    from src.engine.db import init_db, get_latest_incidents

    init_db()

    test_file = test_cache / "test_report.txt"
    test_file.write_text(
        "FIELD NOTES: High temperature in Sector 7. Cooling array offline. Operative S is on site.",
        encoding="utf-8",
    )

    from src.app.queue_manager import process_file

    process_file(test_file)

    assert not test_file.exists()
    assert len(list(test_queue.iterdir())) == 0

    incidents = get_latest_incidents(1)
    assert len(incidents) == 1
    report = incidents[0]
    assert "Sector 7" in report["identified_entities"]["locations"]


def test_integration_pipeline_wav(tmp_path, monkeypatch):
    import wave
    import struct

    test_cache = tmp_path / "cache"
    test_queue = tmp_path / "queue"
    test_failed = tmp_path / "failed_audio"
    test_db = tmp_path / "localslate.db"

    test_cache.mkdir()
    test_queue.mkdir()
    test_failed.mkdir()

    import src.engine.db as db_mod
    import src.app.queue_manager as qm_mod

    monkeypatch.setattr(db_mod, "DB_PATH", test_db)
    monkeypatch.setattr(qm_mod, "CACHE_DIR", test_cache)
    monkeypatch.setattr(qm_mod, "QUEUE_DIR", test_queue)
    monkeypatch.setattr(qm_mod, "FAILED_DIR", test_failed)

    from src.engine.db import init_db, get_latest_incidents

    init_db()

    test_wav = test_cache / "report_audio_beta.wav"
    with wave.open(str(test_wav), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        for _ in range(16000):
            wav.writeframesraw(struct.pack("<h", 0))

    from src.app.queue_manager import process_file

    process_file(test_wav)

    incidents = get_latest_incidents(1)
    assert len(incidents) == 1
    report = incidents[0]
    assert report["computed_priority_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "Sector 4" in report["identified_entities"]["locations"]
