import os
import logging
from pathlib import Path

# Enforce 2 CPU thread limit strictly via environment flag
os.environ["OMP_NUM_THREADS"] = "2"

try:
    from faster_whisper import WhisperModel
except ImportError:
    # Allow safe import even if dependencies aren't installed yet
    WhisperModel = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / ".models" / "whisper"
MAX_FILE_SIZE_MB = 25

class AudioProcessorError(Exception):
    pass

class WhisperProcessor:
    def __init__(self):
        if WhisperModel is None:
            raise ImportError("faster-whisper is not installed.")
        
        self.model_path = str(MODELS_DIR)
        
        # Check if model exists (Assuming base model or just checking if dir is populated)
        if not MODELS_DIR.exists() or not any(MODELS_DIR.iterdir()):
            logging.warning(f"Whisper model directory {MODELS_DIR} is empty or missing. Transcription will fail at runtime if not downloaded.")
        
        try:
            # Load model using int8 quantization and strictly enforce CPU threads
            # Using 'base.en' if local model path doesn't have the explicit model files,
            # but aiming to use the local model_path explicitly as per requirements.
            self.model = WhisperModel(
                model_size_or_path=self.model_path if any(MODELS_DIR.iterdir()) else "base.en",
                device="cpu",
                compute_type="int8",
                cpu_threads=2
            )
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            self.model = None

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Error handling for files > 25MB
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise AudioProcessorError(f"Audio file exceeds 25MB limit: {file_size_mb:.2f}MB")
        
        if self.model is None:
            raise AudioProcessorError("Whisper model was not loaded successfully.")

        segments, info = self.model.transcribe(str(audio_path), beam_size=5)
        
        transcription_parts = []
        for segment in segments:
            transcription_parts.append(segment.text.strip())
            
        return " ".join(transcription_parts)
