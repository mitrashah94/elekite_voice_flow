# Coding Conventions

**Analysis Date:** 2026-02-03

## Naming Patterns

**Files:**
- Lowercase with underscores: `voiceflow.py`, `settings_gui.py`, `setup.py`
- Descriptive names reflecting purpose/module

**Functions:**
- snake_case for all functions
- Prefix private functions with underscore: `_callback()`, `_on_press()`, `_process_audio()`
- Public helper functions: `load_config()`, `save_config()`, `play_sound()`
- Callbacks use `_on_*` convention: `_on_press()`, `_on_release()`, `_on_save()`

**Variables:**
- snake_case for all variables
- Constants in UPPER_CASE: `APP_NAME`, `CONFIG_DIR`, `SAMPLE_RATE`, `DEFAULT_CONFIG`
- Boolean variables use `_var` suffix with `tk.BooleanVar`: `self.ai_cleanup_var`, `self.save_recordings_var`
- String variables use `_var` suffix with `tk.StringVar`: `self.api_key_var`, `self.hotkey_var`
- Internal state prefixed with underscore: `self._frames`, `self._recording`, `self._client`, `self._listener`

**Types:**
- Union types use PEP 604 syntax: `str | None` (not `Optional[str]`)
- Type hints on function signatures: `def log(msg: str):`, `def stop(self) -> str | None:`
- Return type hints required for public functions
- Parameter type hints required

**Classes:**
- PascalCase: `AudioRecorder`, `Transcriber`, `HotkeyManager`, `VoiceFlowApp`, `VoiceFlowCLI`, `SettingsApp`
- Suffix with concrete type: `AudioRecorder`, not `Recorder`

## Code Style

**Formatting:**
- No automated formatter configured (no Black, Prettier, etc.)
- 4 spaces for indentation (Python standard)
- Max line length: appears to be ~120 characters based on existing code
- Trailing commas in multi-line structures respected

**Linting:**
- No linter configured (no pylint, flake8, etc.)
- No style enforcement in pipeline

**Imports:**
- Group order (observed pattern in files):
  1. Standard library (os, sys, json, time, etc.)
  2. Third-party packages (rumps, sounddevice, numpy, pynput, openai, tkinter)
  3. Local imports (none in this project)

**Lazy/Conditional Imports:**
Pattern used throughout for optional dependencies:
```python
try:
    import rumps
except ImportError:
    rumps = None

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None
    np = None
```
Allows graceful degradation when packages unavailable.

**Import Aliases:**
- `import sounddevice as sd` - standard alias for sounddevice
- `from pynput import keyboard as pynput_keyboard` - explicit namespace to avoid conflicts

## Error Handling

**Pattern: Broad Exception Handling with Logging**

Silent failures with fallback:
```python
try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line)
except Exception:
    pass  # Silently ignore logging errors
```

**Pattern: Logged Errors with User Messages**

Log + notify user in main processing:
```python
except Exception as e:
    log(f"Error processing audio: {e}")
    self.status_item.title = f"❌  Error: {str(e)[:40]}"
    if self.config.get("sound_feedback"):
        play_sound("error")
    if self.config.get("show_notification"):
        send_notification("VoiceFlow Error", str(e)[:100])
```

**Pattern: Validation Errors**

Raise for configuration issues:
```python
if not api_key:
    raise ValueError("No OpenAI API key configured. Set it in ~/.voiceflow/config.json or OPENAI_API_KEY env var.")
```

**Pattern: Safe Cleanup in Finally Blocks**

Ensure resources cleaned up:
```python
finally:
    self._processing = False
    self.title = self.ICON_IDLE
    try:
        os.unlink(audio_path)
    except Exception:
        pass
```

## Logging

**Framework:** `print()` and custom `log()` function (file-based)

**Pattern:**
```python
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
```

**When to Log:**
- State transitions: `log("Recording started")`, `log("Recording stopped — {duration:.1f}s of audio")`
- Processing steps: `log(f"Transcribing {audio_path} ...")`, `log(f"Cleaning up transcript with AI ...")`
- Results: `log(f"Raw transcript: {text[:120]}...")`, `log(f"Cleaned text: {cleaned[:120]}...")`
- Configuration: `log(f"Hotkey listener started — key={self.hotkey_name}, mode={self.mode}")`
- App lifecycle: `log(f"{APP_NAME} v{APP_VERSION} started")`
- Errors: `log(f"Failed to load config: {e}")`

**Truncation for Privacy:** Log output truncated for long values to avoid excessive logging

## Comments

**When to Comment:**
- Class docstrings with purpose: `"""Records audio from the default input device using sounddevice."""`
- Function docstrings with purpose and return: `"""Stop recording and return the path to a WAV file, or None."""`
- Section separators with hash lines: `# ---------------------------------------------------------------------------`
- Inline comments for non-obvious logic

**Documentation:**
Module-level docstrings included:
```python
"""
VoiceFlow — A Wispr Flow-inspired voice typing app for macOS.

Hold a hotkey to record your voice, release to transcribe and auto-type
the result wherever your cursor is. Uses OpenAI Whisper for transcription
and optionally cleans up text with GPT.

Usage:
    python voiceflow.py
"""
```

**No JSDoc/TSDoc:** Python project, no type documentation comments needed

## Function Design

**Size:** Functions are generally 10-40 lines, larger methods (30-50 lines) for UI building and processing pipelines

**Parameters:**
- Minimal parameters (1-4), sometimes self in methods
- Configuration passed as dict: `def __init__(self, config: dict):`
- Callbacks as function references: `on_start`, `on_stop`

**Return Values:**
- Explicit return types in signature
- `None` for void operations
- Union types for optional values: `def stop(self) -> str | None:`
- Dicts returned for loaded config: `def load_config() -> dict:`

**Private Implementation Methods:**
- Prefixed with `_` to hide implementation
- Used for callbacks, internal processing: `_callback()`, `_on_press()`, `_process_audio()`
- Single responsibility: each does one clear thing

## Module Design

**Exports:**
- Module-level functions for utilities: `log()`, `load_config()`, `save_config()`, `load_dictionary()`, `play_sound()`, `paste_text()`, `send_notification()`, `check_dependencies()`
- Classes for stateful components: `AudioRecorder`, `Transcriber`, `HotkeyManager`, `VoiceFlowApp`, `VoiceFlowCLI`, `SettingsApp`
- Entry point via `if __name__ == "__main__": main()` pattern

**Barrel Files:** Not used (single-file modules)

**Module Organization in voiceflow.py:**
1. Imports and conditional imports (lines 13-47)
2. Constants and paths (lines 49-78)
3. Helper functions (lines 83-155)
4. Core classes: AudioRecorder (lines 161-229), Transcriber (lines 236-319), HotkeyManager (lines 326-405)
5. App classes: VoiceFlowApp (lines 412-558), VoiceFlowCLI (lines 565-636)
6. Entry point (lines 643-681)

**Module Organization in settings_gui.py:**
1. Imports (lines 7-18)
2. Configuration paths and defaults (lines 20-79)
3. Single class: SettingsApp (lines 82-402)
4. Entry point (lines 400-402)

## Configuration Management

**Pattern:** Dictionary-based config with defaults

**Loading:**
```python
def load_config() -> dict:
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
```

**Merging:** User config merged with defaults using dict spread: `{**DEFAULT_CONFIG, **user}`

**Constants:**
Path-based: `CONFIG_DIR = Path.home() / ".voiceflow"`, `CONFIG_FILE = CONFIG_DIR / "config.json"`

## Thread Safety

**Pattern:** Explicit locks for shared state

Used in `AudioRecorder` class:
```python
def __init__(self):
    self._lock = threading.Lock()

def start(self):
    with self._lock:
        if self._recording:
            return
        # ... start recording
```

Lock prevents concurrent state modification during recording lifecycle.

---

*Convention analysis: 2026-02-03*
