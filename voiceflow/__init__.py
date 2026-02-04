"""VoiceFlow - Voice-to-text dictation tool."""
from .core import (
    APP_NAME,
    APP_VERSION,
    load_config,
    save_config,
    AudioRecorder,
    Transcriber,
)

__version__ = APP_VERSION

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "__version__",
    "load_config",
    "save_config",
    "AudioRecorder",
    "Transcriber",
]
