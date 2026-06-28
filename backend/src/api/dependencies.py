from backend.src.database.db import DatabaseService, get_db_service
from backend.src.engine.slm_processor import SLMService, get_slm_service
from backend.src.engine.audio_processor import AudioService, get_audio_service


def get_db() -> DatabaseService:
    return get_db_service()


def get_slm() -> SLMService:
    return get_slm_service()


def get_audio() -> AudioService:
    return get_audio_service()
