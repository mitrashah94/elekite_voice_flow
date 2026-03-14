# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

VoiceFlow is a voice-to-text dictation application that runs in the system tray/menu bar. Users press a hotkey to record speech, which is transcribed via OpenAI Whisper and automatically pasted at their cursor. Currently supports macOS with Windows support in development.

## Commands

```bash
# Run the application
python3 voiceflow.py

# Alternative entry point
python -m voiceflow

# Open settings GUI
python3 settings_gui.py

# Run setup wizard (first-time setup)
python3 setup.py

# Install dependencies
pip install -r requirements.txt
```

There is no test suite or linting infrastructure.

## Architecture

### Entry Flow

`voiceflow.py` → dependency check → config load (`~/.voiceflow/config.json`) → platform detection → app instantiation → hotkey listener → recording pipeline

### Core Structure

```
voiceflow/
├── core/                    # Cross-platform core logic
│   ├── app.py              # VoiceFlowApp (macOS), WindowsVoiceFlowApp (Windows), VoiceFlowCLI (fallback)
│   ├── audio.py            # AudioRecorder - sounddevice-based capture
│   ├── transcriber.py      # Transcriber - Whisper API + GPT cleanup
│   ├── hotkey.py           # HotkeyManager - pynput-based global hotkeys
│   └── config.py           # Configuration management
└── platform/               # Platform abstraction layer
    ├── interfaces.py       # ABC service contracts (5 services)
    ├── macos/              # macOS implementations (rumps, osascript, afplay)
    └── windows/            # Windows implementations (pystray, win32, winsound)
```

### Platform Abstraction

The `voiceflow/platform/` module implements a backend singleton pattern. At import time, it detects the platform and instantiates the appropriate backend:

- **5 services defined in `interfaces.py`**: `ClipboardService`, `NotificationService`, `SoundService`, `TrayService`, `AutostartService`
- **Exported as module-level singletons**: `clipboard`, `notifications`, `sounds`, `tray`, `autostart`
- **Hotkeys NOT abstracted** - pynput is already cross-platform, handled in `core/app.py`

### Threading Model

- **macOS**: Single-threaded with rumps event loop
- **Windows**: Tray runs in daemon background thread, hotkey listener in main thread (prevents pynput/GUI conflicts)

## Key Patterns

### Error Handling

`TranscriptionError` in `core/transcriber.py` is raised AFTER user feedback (sound + notification). Callers should not duplicate error feedback.

### Paste Failure Fallback

Text is always copied to clipboard first. If paste simulation fails (elevated app, restricted context), text remains in clipboard with error notification. User can manually paste.

### Hotkey Conflict Detection

Primary hotkey can fall back to Right Ctrl if Option is taken by Discord/OBS. See `get_active_hotkey()` in `core/hotkey.py`.

### Lazy Imports

Optional dependencies use try/except pattern for graceful degradation:
```python
try:
    import rumps
except ImportError:
    rumps = None
```

## Configuration

User config: `~/.voiceflow/config.json`
Custom dictionary: `~/.voiceflow/dictionary.txt` (one term per line)
Logs: `~/.voiceflow/voiceflow.log`
Recordings (optional): `~/.voiceflow/recordings/`

## Development Notes

- Planning documents in `.planning/` track project state, roadmap, and phase documentation
- Commit message format: `feat(phase-date): description` (e.g., `feat(03-03): add WindowsVoiceFlowApp`)
- Windows testing is deferred (developer on macOS) - verify with actual Windows hardware before release
