"""VoiceFlow configuration and utility functions."""

import json
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------
APP_NAME = "VoiceFlow"
APP_VERSION = "1.0.0"
CONFIG_DIR = Path.home() / ".voiceflow"
CONFIG_FILE = CONFIG_DIR / "config.json"
DICTIONARY_FILE = CONFIG_DIR / "dictionary.txt"
LOG_FILE = CONFIG_DIR / "voiceflow.log"
RECORDING_DIR = CONFIG_DIR / "recordings"

SAMPLE_RATE = 16000  # Whisper expects 16 kHz
CHANNELS = 1

DEFAULT_CONFIG = {
    "api_key": "",
    "hotkey": "fn",               # fn, ctrl, option, cmd, or a letter
    "mode": "hold",               # "hold" = hold-to-record, "toggle" = press to start/stop
    "whisper_model": "whisper-1",
    "language": "",               # empty = auto-detect
    "ai_cleanup": True,           # post-process with GPT to clean filler words
    "cleanup_model": "gpt-4o-mini",
    "auto_paste": True,           # paste result at cursor
    "sound_feedback": True,       # play start/stop sounds
    "show_notification": True,
    "save_recordings": False,
    "custom_prompt": "",          # extra instructions for cleanup
    "whisper_prompt": "",         # prompt/context hint for Whisper
    "max_recording_seconds": 300,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str):
    """Append a timestamped message to the log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")


def load_config() -> dict:
    """Load config from disk, filling in defaults for missing keys."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                user = json.load(f)
            merged = {**DEFAULT_CONFIG, **user}
            return merged
        except Exception as e:
            log(f"Failed to load config: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def load_dictionary() -> list[str]:
    """Load custom dictionary words (one per line)."""
    if DICTIONARY_FILE.exists():
        return [w.strip() for w in DICTIONARY_FILE.read_text().splitlines() if w.strip()]
    return []
