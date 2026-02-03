# Architecture

**Analysis Date:** 2026-02-03

## Pattern Overview

**Overall:** Layered event-driven desktop application with optional UI (menu bar or CLI)

**Key Characteristics:**
- **Single-responsibility modules**: Each class handles one domain (recording, transcription, hotkey listening, UI)
- **Interface abstraction**: Same core logic (recorder, transcriber) used by both rumps menu-bar app and CLI fallback
- **Async audio processing**: Recording and transcription run in background threads to keep UI responsive
- **Configuration-driven**: All behavior controlled by JSON config in `~/.voiceflow/config.json`
- **Graceful degradation**: Falls back to CLI mode if rumps (menu bar) unavailable or non-macOS system

## Layers

**Presentation Layer (UI):**
- Purpose: Display status and accept user interactions
- Location: `voiceflow.py` (VoiceFlowApp class, lines 412-558) and settings_gui.py (SettingsApp class)
- Contains: Menu bar app (macOS-specific), CLI interface, settings GUI (tkinter)
- Depends on: Core layer (recorder, transcriber, config)
- Used by: User directly via menu bar or terminal

**Domain Layer (Core Business Logic):**
- Purpose: Audio capture, transcription, text cleanup, hotkey monitoring
- Location: `voiceflow.py` - AudioRecorder (lines 161-229), Transcriber (lines 236-319), HotkeyManager (lines 326-405)
- Contains: Classes for recording, transcription, hotkey listening
- Depends on: External services (OpenAI API, sounddevice library)
- Used by: Presentation layer to execute user commands

**Configuration & Utilities Layer:**
- Purpose: Configuration loading/saving, system interactions, logging
- Location: `voiceflow.py` (top-level functions: log, load_config, save_config, load_dictionary, play_sound, paste_text, send_notification)
- Contains: Config management, file I/O, macOS system calls (paste, notifications, sounds)
- Depends on: Filesystem, macOS system tools (osascript, pbcopy, afplay)
- Used by: All layers for config and system integration

**Setup & Installation Layer:**
- Purpose: Dependency installation, initial configuration, system setup
- Location: `setup.py` (entire file), requirements.txt
- Contains: Python package installation, API key prompts, hotkey/mode configuration, LaunchAgent setup
- Depends on: pip, Homebrew (for PortAudio), macOS system
- Used by: User during initial setup

## Data Flow

**Recording & Transcription Workflow:**

1. **Hotkey pressed** → HotkeyManager._on_press() detects key match
2. **Start signal** → _start_recording() callback triggered
3. **Recording starts** → AudioRecorder.start() opens stream, _callback() captures frames
4. **Hotkey released** → HotkeyManager._on_release() detects release
5. **Stop signal** → _stop_recording() callback triggered
6. **Audio saved** → AudioRecorder.stop() writes frames to WAV file
7. **Background processing** → _process_audio() runs in daemon thread
8. **Transcription** → Transcriber.transcribe() sends audio to OpenAI Whisper API
9. **Text cleanup** → Transcriber.cleanup() optionally sends raw text to GPT
10. **Output** → paste_text() copies to clipboard and simulates Cmd+V, notification shows preview
11. **Storage** → If enabled, WAV file copied to ~/.voiceflow/recordings/

**Configuration Flow:**

1. **Startup** → load_config() reads ~/.voiceflow/config.json, merges with DEFAULT_CONFIG
2. **User changes settings** → Via settings_gui.py or direct file edit
3. **Save** → _save_config() writes to ~/.voiceflow/config.json
4. **App reload** → Next app launch reads updated config

**State Management:**
- **Config state**: Persistent JSON in `~/.voiceflow/config.json`, loaded at startup
- **Recording state**: In-memory (AudioRecorder._recording, _frames, _stream)
- **UI state**: Menu bar icon and status text in VoiceFlowApp, updated as recording/processing state changes
- **Hotkey state**: HotkeyManager tracks _pressed (for hold mode) and _is_active (for toggle mode)

## Key Abstractions

**AudioRecorder:**
- Purpose: Encapsulates audio capture using sounddevice library
- Examples: `voiceflow.py` lines 161-229
- Pattern: Stateful class with stream lifecycle management; callback-based frame capture; thread-safe with locks

**Transcriber:**
- Purpose: Manages API communication with OpenAI (Whisper + GPT); handles authentication and optional cleanup
- Examples: `voiceflow.py` lines 236-319
- Pattern: Lazy-loads OpenAI client on first use; separate transcribe() and cleanup() methods; process() combines both

**HotkeyManager:**
- Purpose: Listens for system-wide hotkey presses; abstracts keyboard handling across special keys and characters
- Examples: `voiceflow.py` lines 326-405
- Pattern: Callback-based listener; maps config names to pynput Key objects; supports hold and toggle modes

**VoiceFlowApp:**
- Purpose: macOS menu bar application interface
- Examples: `voiceflow.py` lines 412-558
- Pattern: Subclasses rumps.App; orchestrates recorder/transcriber/hotkey components; background threading for audio processing

**VoiceFlowCLI:**
- Purpose: Terminal-based fallback interface for non-macOS or no-rumps scenarios
- Examples: `voiceflow.py` lines 565-636
- Pattern: Mirrors VoiceFlowApp interface; simpler I/O (print/input instead of menu/notifications)

**SettingsApp:**
- Purpose: Tkinter-based GUI for editing configuration
- Examples: `settings_gui.py` lines 82-402
- Pattern: Builds UI sections dynamically; maps config values to tk variables; bidirectional sync with config file

## Entry Points

**Main Application:**
- Location: `voiceflow.py` (main function, lines 660-677)
- Triggers: `python3 voiceflow.py` or `./start.sh`
- Responsibilities: Checks dependencies, loads/creates config, branches to VoiceFlowApp (menu bar) or VoiceFlowCLI based on environment

**Settings GUI:**
- Location: `settings_gui.py` (main block, lines 400-402)
- Triggers: `python3 settings_gui.py` or menu bar "⚙️ Settings..." callback
- Responsibilities: Loads config, builds UI, handles save/load of config.json and dictionary.txt

**Setup Wizard:**
- Location: `setup.py` (main function, lines 275-369)
- Triggers: `python3 setup.py`
- Responsibilities: Guides user through Python version check, dependency installation, API key prompt, hotkey selection, mode choice, LaunchAgent setup

## Error Handling

**Strategy:** Defensive with silent fallback where possible; logs all errors; prevents crashes from taking down app

**Patterns:**
- **Missing dependencies**: check_dependencies() (lines 643-657) exits with helpful message before running
- **API failures**: try/except in Transcriber.transcribe() and cleanup() (lines 252-311); caught by _process_audio() which updates UI with error message
- **Config load failure**: Graceful fallback to DEFAULT_CONFIG (line 107-108)
- **Audio capture errors**: Logged but don't halt; AudioRecorder discards recordings <0.3s (line 216-218)
- **Hotkey mismatches**: _matches() (line 360-368) returns False rather than raising, prevents crashes from unknown key types
- **File operations**: All wrapped in try/except; missing files return empty state rather than crashing (e.g., load_dictionary line 119-121)

## Cross-Cutting Concerns

**Logging:**
- Framework: Custom log() function using file append (lines 84-94)
- Location: `~/.voiceflow/voiceflow.log`
- Pattern: Timestamped entries for startup, recording events, API calls, errors; also prints to stdout

**Validation:**
- Config validation: Merge with defaults ensures all keys present (DEFAULT_CONFIG, line 63-78, 104-105)
- Audio validation: Check duration >= 0.3s before processing (line 216-218)
- Hotkey validation: Validate against SPECIAL_KEYS dict; graceful fallback on unknown keys (line 351-368)
- API key validation: Check in config or OPENAI_API_KEY env var; raise ValueError if missing (line 246-248)

**Authentication:**
- Approach: OpenAI API key stored in `~/.voiceflow/config.json` or OPENAI_API_KEY environment variable
- Lazy loading: API client created only on first transcription attempt (property pattern, lines 243-250)
- Sensitive storage: Config file is user-owned in home directory; never committed to git

---

*Architecture analysis: 2026-02-03*
