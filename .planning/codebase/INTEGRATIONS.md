# External Integrations

**Analysis Date:** 2026-02-03

## APIs & External Services

**OpenAI:**
- Whisper API - Speech-to-text transcription
  - SDK/Client: `openai` package (1.12.0+)
  - Auth: API key from `~/.voiceflow/config.json` → `api_key` field or `OPENAI_API_KEY` env var
  - Usage: `voiceflow.py` lines 244-277 (Transcriber.transcribe method)
  - Model: Configurable via `whisper_model` config (default: "whisper-1")

- Chat Completions API (GPT) - AI text cleanup
  - SDK/Client: `openai` package
  - Auth: Same as above (api_key)
  - Usage: `voiceflow.py` lines 279-311 (Transcriber.cleanup method)
  - Model: Configurable via `cleanup_model` config (default: "gpt-4o-mini", options: gpt-4o, gpt-3.5-turbo)
  - Purpose: Removes filler words, fixes grammar, formats text

**API Key Management:**
- Primary source: `config.json` (`api_key` field) - `voiceflow.py` line 246
- Fallback: `OPENAI_API_KEY` environment variable - `voiceflow.py` line 246
- Setup wizard collects key: `setup.py` lines 112-144
- Settings GUI allows editing: `settings_gui.py` lines 185-193

## Data Storage

**Local Files Only:**
- No remote database integration
- Configuration: JSON file at `~/.voiceflow/config.json`
- Custom dictionary: Plain text at `~/.voiceflow/dictionary.txt`
- Logs: Plain text at `~/.voiceflow/voiceflow.log`
- Recordings (optional): WAV files in `~/.voiceflow/recordings/` (user-configurable, default: disabled)

**Audio Data Flow:**
1. Record to memory (NumPy arrays in `voiceflow.py` AudioRecorder class)
2. Write temporary WAV to system temp directory
3. Send to OpenAI Whisper API via `openai` client
4. Audio deleted locally after API returns (line 510: `os.unlink(audio_path)`)
5. No persistent local storage of audio unless `save_recordings: true`

## Authentication & Identity

**Auth Provider:**
- Custom: OpenAI API key only
- Implementation: Direct API key passed to OpenAI client constructor
- No user authentication framework (stateless, API-key-based)
- API key checked at startup: `voiceflow.py` lines 246-250

**Config Persistence:**
- API key stored in plaintext in `~/.voiceflow/config.json` (user-accessible file)
- Warning in setup wizard: `setup.py` lines 125-126 (masked display in UI)
- GUI masks key input in settings_gui.py lines 186-188

## Monitoring & Observability

**Error Tracking:**
- None (no external service)

**Logs:**
- Local file-based logging to `~/.voiceflow/voiceflow.log`
- Append-only log function: `voiceflow.py` lines 84-94
- Format: `[YYYY-MM-DD HH:MM:SS] {message}`
- Accessible via menu: "View Log" opens in Console app (`voiceflow.py` line 524)
- Setup creates log file in config directory: `setup.py` line 17

**Status Feedback:**
- macOS menu bar title updates (recording state, status)
- macOS notifications with transcription preview
- Sound feedback (start/stop/error) via afplay
- CLI output to terminal

## macOS System Integrations

**Accessibility Framework:**
- Global keyboard listener via pynput - `voiceflow.py` lines 326-406
- Requires: System Settings → Privacy & Security → Accessibility

**Audio:**
- Microphone input via sounddevice - `voiceflow.py` lines 161-229
- System sounds playback via afplay - `voiceflow.py` lines 124-133
- Requires: System Settings → Privacy & Security → Microphone

**Clipboard & Paste:**
- Clipboard write via pbcopy - `voiceflow.py` line 138
- Paste simulation via osascript/System Events - `voiceflow.py` lines 143-146
- Requires: System Settings → Privacy & Security → Accessibility

**Notifications:**
- macOS native notifications via osascript - `voiceflow.py` lines 149-154
- Display format: notification title + message preview

**Launch Control (Optional):**
- LaunchAgent plist creation for auto-start - `setup.py` lines 232-272
- Plist location: `~/Library/LaunchAgents/com.voiceflow.app.plist`
- Managed via launchctl commands

**Menu Bar:**
- rumps framework integration - `voiceflow.py` lines 412-558
- Menu bar icon, menu items, title updates
- Settings menu with callbacks for file operations

## Incoming Webhooks & Callbacks

**None detected** - Application does not expose webhooks or listen for incoming requests from external services.

## Outgoing Webhooks & Callbacks

**None** - No outgoing webhooks. Only direct API calls to OpenAI services.

## CI/CD & Deployment

**Hosting:**
- Standalone desktop application (no server)
- Runs locally on user's macOS machine

**CI Pipeline:**
- None detected - No CI configuration (no GitHub Actions, Travis CI, etc.)

**Distribution:**
- Manual installation via setup wizard
- No package manager distribution (not on PyPI, Homebrew, etc.)

## Secrets & Configuration Management

**API Key Storage:**
- Location: `~/.voiceflow/config.json` (user's home directory)
- Format: JSON plaintext (not encrypted)
- Access control: File permissions on user's home directory
- Environment variable override: `OPENAI_API_KEY` env var supported

**Setup Flow:**
- Wizard prompts for key and stores it: `setup.py` lines 138-144
- Key can be set via environment variable to avoid file storage: `voiceflow.py` line 246

**GUI Management:**
- Settings GUI hides key input with bullet points: `settings_gui.py` line 188
- Toggle to show/hide key in settings: `settings_gui.py` lines 190-295

## Service Dependencies Summary

| Service | Purpose | Required | Auth Method | Fallback |
|---------|---------|----------|-------------|----------|
| OpenAI Whisper | Speech-to-text | Yes | API key | None |
| OpenAI GPT | Text cleanup | Configurable | API key | Raw transcript |
| macOS Accessibility | Hotkey listening | Yes (macOS) | User permissions | CLI mode |
| macOS Microphone | Audio capture | Yes | User permissions | None |
| PortAudio | Audio backend | Yes (macOS) | Installed via Homebrew | Manual install |

---

*Integration audit: 2026-02-03*
