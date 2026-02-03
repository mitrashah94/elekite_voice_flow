# Testing Patterns

**Analysis Date:** 2026-02-03

## Test Framework

**Status:** Not Configured

**Testing Framework:** None detected

**Test Runner:** Not configured

**Assertion Library:** Not applicable

**Test Files:** No test files found in repository

**Run Commands:**
```bash
# No test commands available
# Testing not implemented
```

## Rationale for No Testing

This is a desktop application with external service dependencies (OpenAI API, audio hardware) and GUI components (macOS menu bar app, tkinter GUI). Testing is not currently set up because:

1. **Hardware Dependencies:** Audio recording via `sounddevice` requires microphone hardware
2. **External Service Dependencies:** Whisper and GPT API calls require OpenAI API keys and network connectivity
3. **GUI Components:** rumps (macOS menu bar) and tkinter (settings window) are difficult to unit test without mocking the entire GUI framework
4. **Keyboard Listening:** pynput keyboard listener integrates directly with OS kernel
5. **System Integration:** Clipboard manipulation, notification sending, and file I/O are system-level operations

## Current Code Structure (Not Optimized for Testing)

### Tightly Coupled Components

**Audio Recording** (`AudioRecorder` class, `voiceflow.py:161-229`):
- Directly uses `sounddevice` library without abstraction
- State management with threading lock
- Callback-based audio data collection

```python
class AudioRecorder:
    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS):
        self._frames: list = []
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()
```

**Transcription** (`Transcriber` class, `voiceflow.py:236-319`):
- Lazy-loads OpenAI client on first use
- Direct file I/O for audio
- Two-stage pipeline: transcribe → cleanup

```python
class Transcriber:
    def __init__(self, config: dict):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(...)
            self._client = OpenAI(api_key=api_key)
        return self._client
```

**Hotkey Listening** (`HotkeyManager` class, `voiceflow.py:326-405`):
- Direct OS-level keyboard integration via pynput
- Callback-based event handling

```python
class HotkeyManager:
    def _on_press(self, key):
        if not self._matches(key):
            return
        if self.mode == "hold":
            if not self._pressed:
                self._pressed = True
                self.on_start()
```

**UI Integration** (`VoiceFlowApp` class, `voiceflow.py:412-558`):
- Directly inherits from `rumps.App`
- Threading for background processing
- State management mixed with UI updates

```python
class VoiceFlowApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title="🎙️", quit_button=None)
        self.config = load_config()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(self.config)
        self._processing = False

    def _process_audio(self, audio_path: str):
        self._processing = True
        try:
            text = self.transcriber.process(audio_path)
            # UI updates mixed with business logic
```

## Suggested Testing Approach (If Implemented)

### Layer 1: Configuration Management (Testable)

File: `voiceflow.py:97-122`

Would test:
- `load_config()` with missing file
- `load_config()` with corrupted JSON
- `load_config()` merges defaults correctly
- `save_config()` writes valid JSON
- `load_dictionary()` handles missing file

Example test structure:
```python
def test_load_config_with_defaults():
    # Arrange: no config file exists
    # Act: load_config()
    # Assert: returns DEFAULT_CONFIG values

def test_load_config_merge():
    # Arrange: partial config file with subset of keys
    # Act: load_config()
    # Assert: missing keys filled from DEFAULT_CONFIG

def test_save_config_creates_directory():
    # Arrange: config dir doesn't exist
    # Act: save_config({...})
    # Assert: directory created and valid JSON written
```

### Layer 2: Text Processing (Testable)

File: `voiceflow.py:279-311`

Would test:
- `Transcriber.cleanup()` disabled returns raw text unchanged
- `Transcriber.cleanup()` enabled calls GPT with proper prompt
- Prompt building includes custom instructions
- Dictionary terms included in Whisper prompt

Example test structure:
```python
def test_cleanup_disabled():
    config = {"ai_cleanup": False}
    transcriber = Transcriber(config)
    result = transcriber.cleanup("raw text with um and like")
    assert result == "raw text with um and like"  # unchanged

def test_cleanup_enabled_with_mock_gpt(mock_openai_client):
    config = {"ai_cleanup": True, "cleanup_model": "gpt-4o-mini"}
    transcriber = Transcriber(config)
    transcriber._client = mock_openai_client

    result = transcriber.cleanup("um, hello like world")
    assert mock_openai_client.chat.completions.create.called
```

### Layer 3: Key Matching (Testable with Mocks)

File: `voiceflow.py:351-368`

Would test:
- Key matching for special keys (fn, ctrl, option, etc.)
- Key matching for character keys
- Invalid key names return None

Example test structure:
```python
def test_matches_special_key():
    mgr = HotkeyManager("fn", "hold", lambda: None, lambda: None)
    target = mgr._get_target_key()
    assert target == pynput_keyboard.Key.f13

def test_matches_character_key():
    mgr = HotkeyManager("a", "hold", lambda: None, lambda: None)
    target = mgr._get_target_key()
    assert isinstance(target, pynput_keyboard.KeyCode)
```

### Layer 4: Settings GUI (GUI Testing - Complex)

File: `settings_gui.py:82-402`

Would require:
- GUI testing framework (pyautogui, tkinter.testing, or similar)
- Mocking tkinter widgets
- Testing config serialization/deserialization through UI

Example test structure:
```python
def test_settings_app_loads_config():
    app = SettingsApp()
    # Assert fields populated from config

def test_settings_app_saves_config():
    app = SettingsApp()
    # Simulate user input
    # Click save
    # Assert config file updated
```

## Dependencies for Testing (If Implemented)

**Testing Framework Options:**
- `pytest` - Most popular, flexible, good for unit and integration tests
- `unittest` - Built-in, verbose but comprehensive

**Mocking:**
- `unittest.mock` - Built-in, sufficient for mocking OpenAI client
- `pytest-mock` - Cleaner syntax with pytest

**Fixtures:**
- `pytest` fixtures for config files, mock APIs, temporary directories

**Integration Testing:**
- Would need actual OpenAI API key or mock server (vcr.py, betamax)
- Would need audio hardware or mock audio stream

## Current Code Characteristics

**Testability Issues:**
1. **Monolithic Classes** - VoiceFlowApp mixes business logic, UI, and threading
2. **Global State** - Config loaded at module level, mutated through app lifetime
3. **External Dependencies** - Direct OpenAI, pynput, rumps, tkinter usage without abstraction layers
4. **No Dependency Injection** - Dependencies created internally, not passed in
5. **Threading** - Background processing makes state verification difficult
6. **File I/O** - Direct filesystem access for config, logs, recordings

**Strengths for Future Testing:**
1. **Modular Classes** - AudioRecorder, Transcriber, HotkeyManager can be unit tested in isolation
2. **Configuration Dict Pattern** - Allows easy test config creation
3. **Clear Separation of Concerns** - Recording, transcription, and hotkey listening are distinct
4. **Error Handling** - Try/except blocks for resilience (though sometimes too broad)

## Recommendations for Testing Implementation

**Phase 1: Configuration & Utilities**
- Add pytest
- Test `load_config()`, `save_config()`, `load_dictionary()`
- Test `play_sound()` with mocked subprocess
- Test `paste_text()` with mocked subprocess
- Target: 70%+ coverage on configuration logic

**Phase 2: Core Classes with Mocking**
- Mock OpenAI client for `Transcriber` testing
- Mock pynput keyboard for `HotkeyManager` testing
- Mock sounddevice for `AudioRecorder` testing (or use numpy arrays)
- Target: Unit tests for each class, integration tests for pipelines

**Phase 3: GUI Integration**
- Separate business logic from GUI (extract to service classes)
- Create `VoiceFlowService` with core recording/transcription logic
- Test service independently
- Mock rumps.App for VoiceFlowApp testing
- Target: Functional tests for UI workflows

**Phase 4: End-to-End**
- Use VCR or betamax to record/replay API calls
- Test full recording → transcription → paste workflow
- Mock audio input and paste output
- Target: Critical path coverage

## Test File Organization (When Implemented)

**Suggested Structure:**
```
VoiceFlow/
├── voiceflow.py
├── settings_gui.py
├── setup.py
├── tests/                    # New
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_config.py       # Configuration loading/saving
│   ├── test_audio.py        # AudioRecorder tests
│   ├── test_transcriber.py  # Transcriber tests (with mocked OpenAI)
│   ├── test_hotkeys.py      # HotkeyManager tests
│   ├── test_settings_gui.py # GUI tests
│   ├── fixtures/            # Test data
│   │   ├── sample_config.json
│   │   ├── sample_dictionary.txt
│   │   └── sample_audio.wav
│   └── mocks/               # Mock objects
│       ├── mock_openai.py
│       └── mock_pynput.py
├── pytest.ini               # Config
└── requirements-dev.txt     # Dev dependencies
```

**Naming Convention:**
- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`
- Test classes (if grouping): `Test*`

Example:
```python
# tests/test_config.py
def test_load_config_with_defaults():
    pass

def test_load_config_merge():
    pass

class TestConfigFile:
    def test_save_creates_directory(self):
        pass
```

## Code Coverage Goals (When Implemented)

**Priority Areas:**
1. Configuration management: 90%+
2. Text processing (cleanup): 85%+
3. Key matching: 80%+
4. Transcription pipeline: 75% (with mocked API)
5. GUI callbacks: 60% (difficult to test)

**Overall target:** 75-80% code coverage for critical paths

---

*Testing analysis: 2026-02-03*

**Note:** This codebase has no automated tests. The analysis above describes where testing could be added and the challenges involved. The application relies on manual testing and user feedback for quality assurance.
