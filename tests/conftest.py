import pytest
import backend.src.database.db as db_mod
import backend.src.engine.audio_processor as audio_mod
import backend.src.engine.slm_processor as slm_mod
import backend.src.app.queue_manager as qm_mod


@pytest.fixture(autouse=True)
def reset_singletons():
    # Reset all caching singletons before each test run
    db_mod._global_db_service = None
    audio_mod._global_audio_service = None
    slm_mod._global_slm_service = None

    # Ensure queue manager is stopped if running
    if qm_mod.global_queue_manager is not None:
        try:
            qm_mod.global_queue_manager.stop()
        except Exception:
            pass
        qm_mod.global_queue_manager = None

    # Reset queue manager status to default values
    qm_mod.queue_status.update(
        {
            "is_running": False,
            "current_file": None,
            "current_status": "Idle",
            "current_stage": 0,
            "queue_count": 0,
            "processed_count": 0,
            "failed_count": 0,
        }
    )

    yield
