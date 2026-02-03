# Codebase Structure

**Analysis Date:** 2026-02-03

## Directory Layout

```
/Users/mitrashah/Desktop/VoiceFlow/
├── voiceflow.py            # Main application (menu bar or CLI)
├── settings_gui.py         # Settings editor GUI (tkinter)
├── setup.py                # Installation & setup wizard
├── requirements.txt        # Python dependencies
├── index.html              # Marketing/documentation page (static)
├── start.sh                # Generated launch script
├── README.md               # User documentation
├── .gitignore              # Git ignore rules
├── .planning/              # GSD planning directory
│   └── codebase/           # Codebase analysis documents
└── .git/                   # Git repository

~/.voiceflow/               # User home config directory (created at runtime)
├── config.json             # Application settings
├── dictionary.txt          # Custom words for Whisper recognition
├── voiceflow.log           # Application log file
└── recordings/             # Optional saved audio files
```

## Directory Purposes

**Project Root:**
- Purpose: Source code, configuration, and documentation
- Contains: Python entry points, UI scripts, setup automation, static website
- Key files: `voiceflow.py` (main app), `setup.py` (installer), `README.md` (docs)

**~/.voiceflow/ (User Config Directory):**
- Purpose: Runtime configuration, user data, logs
- Contains: Settings, custom dictionary, logs, optional recordings
- Key files: `config.json` (all settings), `dictionary.txt` (custom terms), `voiceflow.log` (app events)

**.planning/codebase/:**
- Purpose: GSD codebase mapping documents
- Contains: Architecture, structure, conventions, testing, concerns analysis
- Key files: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

## Key File Locations

**Entry Points:**
- `voiceflow.py`: Main application entry point (runs as menu bar app or CLI)
  - Execution: `python3 voiceflow.py`
  - Main function at lines 660-677
  - Platform detection: Lines 672-677 (rumps menu bar if macOS + available, else CLI)

- `settings_gui.py`: Settings GUI launcher
  - Execution: `python3 settings_gui.py`
  - Main function at lines 400-402
  - SettingsApp class at lines 82-402

- `setup.py`: Setup wizard (first-time installation)
  - Execution: `python3 setup.py`
  - Main function at lines 275-369
  - Guides through: Python check, dependencies, API key, hotkey, mode, LaunchAgent setup

- `start.sh`: Shell script launcher (created by setup.py)
  - Execution: `./start.sh`
  - Generated at line 222 of setup.py
  - Wraps `python3 voiceflow.py`

**Configuration:**
- `requirements.txt`: Python package dependencies (lines 1-12)
  - Core packages: openai, sounddevice, numpy, pynput
  - Optional: rumps (for menu bar, falls back to CLI)

- `~/.voiceflow/config.json`: Runtime settings (created by setup.py or load_config)
  - Schema defined in DEFAULT_CONFIG (voiceflow.py lines 63-78)
  - Keys: api_key, hotkey, mode, whisper_model, language, ai_cleanup, cleanup_model, auto_paste, sound_feedback, show_notification, save_recordings, custom_prompt, whisper_prompt, max_recording_seconds

- `~/.voiceflow/dictionary.txt`: Custom terms for Whisper
  - Format: One word per line, comments with #
  - Loaded by load_dictionary() (voiceflow.py lines 117-121)
  - Merged into Whisper prompt (lines 268-272)

**Core Logic:**
- `voiceflow.py` - AudioRecorder class (lines 161-229)
  - Records audio from default input device
  - Uses sounddevice library with numpy array buffering
  - Thread-safe with locks for stream lifecycle
  - Saves to temporary WAV file at 16kHz mono (Whisper format)

- `voiceflow.py` - Transcriber class (lines 236-319)
  - Manages OpenAI API client (lazy initialization)
  - transcribe() method: Sends audio to Whisper API
  - cleanup() method: Optional GPT post-processing to remove filler words
  - process() method: Combined pipeline
  - Builds Whisper prompt from dictionary + user hints

- `voiceflow.py` - HotkeyManager class (lines 326-405)
  - Listens for system-wide hotkey using pynput
  - SPECIAL_KEYS mapping (lines 330-340): fn, ctrl, option, cmd, shift, caps_lock
  - Supports "hold" mode (press = start, release = stop)
  - Supports "toggle" mode (press = start/stop alternating)
  - Thread-safe listener started in daemon thread

- `voiceflow.py` - VoiceFlowApp class (lines 412-558)
  - macOS menu bar application using rumps library
  - Menu items: Status, Hotkey info, Settings, Log viewer, Config folder, About, Quit
  - Coordinates AudioRecorder, Transcriber, HotkeyManager components
  - _start_recording() and _stop_recording() callbacks (lines 450-473)
  - _process_audio() background thread (lines 475-512)
  - Paste at cursor, show notification, save recordings logic

- `voiceflow.py` - VoiceFlowCLI class (lines 565-636)
  - Terminal-based fallback for non-macOS or no-rumps
  - Same recorder/transcriber/hotkey components
  - Simpler I/O: print() instead of menu bar, no notifications
  - Useful for headless/CI systems

- `settings_gui.py` - SettingsApp class (lines 82-402)
  - Tkinter GUI for editing all config options
  - Sections: API key, Recording (hotkey/mode/duration), Transcription (language/prompts), AI Cleanup, Output, Custom Dictionary
  - Bidirectional sync: load from config.json, save changes
  - Dark theme for macOS (lines 91-97)

**Testing:**
- None detected - no automated tests in codebase

**Utilities & Helpers:**
- `voiceflow.py` - Top-level helper functions (lines 84-154):
  - log() - Timestamped logging to file and stdout
  - load_config() - Read ~/.voiceflow/config.json with defaults fallback
  - save_config() - Write config.json
  - load_dictionary() - Read ~/.voiceflow/dictionary.txt
  - play_sound() - macOS system sounds (Pop, Purr, Basso)
  - paste_text() - Copy to clipboard + Cmd+V simulation
  - send_notification() - macOS notification via osascript

## Naming Conventions

**Files:**
- Pattern: `snake_case.py` for modules
- Examples: `voiceflow.py`, `settings_gui.py`, `setup.py`

**Classes:**
- Pattern: PascalCase, descriptive names
- Examples: AudioRecorder, Transcriber, HotkeyManager, VoiceFlowApp, SettingsApp

**Functions:**
- Pattern: snake_case
- Public: load_config(), save_config(), play_sound()
- Private: _on_press(), _callback(), _get_target_key()

**Constants:**
- Pattern: UPPER_SNAKE_CASE
- Examples: APP_NAME, CONFIG_DIR, SAMPLE_RATE, CHANNELS, DEFAULT_CONFIG, SPECIAL_KEYS

**Variables:**
- Pattern: snake_case, prefixed with underscore if private to class
- Private: _frames, _stream, _recording, _lock, _listener, _pressed, _is_active

**Config Keys:**
- Pattern: lower_snake_case
- Examples: api_key, hotkey, mode, ai_cleanup, cleanup_model, auto_paste, sound_feedback

**Types (Python type hints):**
- Pattern: Used in function signatures
- Examples: `def load_config() -> dict:`, `def play_sound(name: str):`, `@property def is_recording(self) -> bool:`

## Where to Add New Code

**New Feature (e.g., new recording mode):**
- Primary code: Add to `voiceflow.py` top-level functions and classes
- Configuration: Add new key to DEFAULT_CONFIG (line 63-78) and settings_gui.py DEFAULT_CONFIG (lines 24-39)
- UI: Add section to settings_gui.py _build_sections() (lines 180-290)
- Tests: Create test file `test_voiceflow.py` (None exist currently)

**New Component/Module (e.g., language detection):**
- Implementation: Create new `.py` file in root (e.g., `language_detector.py`)
- Integration: Import and use in voiceflow.py Transcriber class
- Configuration: If user-configurable, add to DEFAULT_CONFIG and settings_gui.py
- Documentation: Update README.md and code docstrings

**Utilities/Helpers:**
- Shared helpers: Add to top-level functions in `voiceflow.py` (lines 84-154)
- Specialized utilities: Create new file if >100 LOC or used by multiple modules

**UI/Settings:**
- Menu bar additions: Modify VoiceFlowApp.menu (lines 438-448)
- Settings GUI sections: Extend _build_sections() in settings_gui.py (lines 180-290)
- CLI output: Modify VoiceFlowCLI.run() print statements (lines 612-621)

**Setup/Installation:**
- Dependency changes: Update requirements.txt and setup.py REQUIRED_PACKAGES
- Configuration steps: Add functions to setup.py main() (lines 275-369)
- LaunchAgent setup: Modify create_launchd_plist() (lines 232-272)

## Special Directories

**~/.voiceflow/ (created at runtime):**
- Purpose: Persistent user configuration and data
- Generated: Yes, by load_config() and save_config()
- Committed: No, lives in user home directory
- Ownership: User (created with default umask)

**.planning/codebase/:**
- Purpose: GSD analysis documents
- Generated: By GSD mapping commands
- Committed: Yes, checked into git
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**.git/:**
- Purpose: Version control history
- Generated: Yes, by git init
- Committed: Repository metadata
- Notes: .gitignore excludes ~/.voiceflow/ configs and __pycache__/

## Code Organization Principles

**Layering (Separation of Concerns):**
- Audio capture isolated in AudioRecorder class
- Transcription/cleanup isolated in Transcriber class
- UI (menu bar/CLI) isolated in VoiceFlowApp/VoiceFlowCLI classes
- Hotkey listening isolated in HotkeyManager class
- Configuration and system integration in top-level functions

**Dependency Injection Pattern:**
- VoiceFlowApp receives config dict, creates recorder/transcriber instances
- HotkeyManager receives callbacks (on_start, on_stop) from VoiceFlowApp
- Transcriber receives config dict for API key and model selection

**Graceful Degradation:**
- Rumps unavailable → Falls back to CLI (lines 672-677)
- Non-macOS system → CLI mode works, menu bar/paste/sounds skipped
- Missing audio library → Helpful error message at startup (lines 643-657)

---

*Structure analysis: 2026-02-03*
