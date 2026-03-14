"""VoiceFlow configuration and utility functions."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


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
MEETING_DIR = CONFIG_DIR / "meetings"

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
    "notification_preview": False,
    "save_recordings": False,
    "custom_prompt": "",          # extra instructions for cleanup
    "whisper_prompt": "",         # prompt/context hint for Whisper
    "max_recording_seconds": 300,
    # Meeting transcription settings
    "meeting_chunk_seconds": 240,       # 4 min chunks (well under 25MB Whisper limit)
    "meeting_overlap_seconds": 10,      # overlap between chunks for continuity
    "meeting_mix_audio": False,         # False = separate mic/system, True = mix
    "meeting_output_format": "markdown",  # "markdown" or "text"
    "meeting_output_dir": "",           # empty = ~/.voiceflow/meetings/
    "meeting_cost_warning": True,       # show cost estimate on start
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ensure_private_dir(path: Path) -> Path:
    """Create an app-owned directory and tighten permissions when supported."""
    path.mkdir(parents=True, exist_ok=True)
    ensure_private_permissions(path)
    return path


def ensure_private_permissions(path: Path | str):
    """Best-effort permission tightening for private app files."""
    if os.name == "nt":
        return

    try:
        target = Path(path)
        mode = 0o700 if target.is_dir() else 0o600
        target.chmod(mode)
    except Exception:
        pass


def write_secure_text(path: Path, content: str, private_parent: bool = False):
    """Write text with restrictive permissions."""
    parent = path.parent
    if private_parent:
        ensure_private_dir(parent)
    else:
        parent.mkdir(parents=True, exist_ok=True)

    tmp_path = parent / f".{path.name}.tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(tmp_path, path)
    ensure_private_permissions(path)


def write_secure_bytes(path: Path, content: bytes, private_parent: bool = False):
    """Write bytes with restrictive permissions."""
    parent = path.parent
    if private_parent:
        ensure_private_dir(parent)
    else:
        parent.mkdir(parents=True, exist_ok=True)

    tmp_path = parent / f".{path.name}.tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)
    os.replace(tmp_path, path)
    ensure_private_permissions(path)


def write_secure_json(path: Path, payload: dict, private_parent: bool = False):
    """Write JSON with restrictive permissions."""
    write_secure_text(path, json.dumps(payload, indent=2), private_parent=private_parent)


def append_secure_log_line(path: Path, line: str):
    """Append a line to a private log file."""
    ensure_private_dir(path.parent)
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(line)
    ensure_private_permissions(path)


def secure_copy_file(source: Path | str, destination: Path):
    """Copy a file into a private destination path."""
    with open(source, "rb") as src:
        content = src.read()
    write_secure_bytes(destination, content, private_parent=True)


def sanitize_config(cfg: dict) -> dict:
    """Strip secrets from persisted config."""
    safe_cfg = dict(cfg)
    safe_cfg.pop("api_key", None)
    return safe_cfg


def log(msg: str):
    """Append a timestamped message to the log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        append_secure_log_line(LOG_FILE, line)
    except Exception:
        pass
    print(line, end="")


def load_config() -> dict:
    """Load config from disk, filling in defaults for missing keys."""
    ensure_private_dir(CONFIG_DIR)
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
    write_secure_json(CONFIG_FILE, sanitize_config(cfg), private_parent=True)


def load_dictionary() -> list[str]:
    """Load custom dictionary words (one per line)."""
    if DICTIONARY_FILE.exists():
        return [w.strip() for w in DICTIONARY_FILE.read_text().splitlines() if w.strip()]
    return []


def save_dictionary(words: str):
    """Persist dictionary contents with restrictive permissions."""
    normalized = words.rstrip() + "\n" if words.strip() else ""
    write_secure_text(DICTIONARY_FILE, normalized, private_parent=True)
