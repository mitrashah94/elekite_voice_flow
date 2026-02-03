# Technology Stack

**Analysis Date:** 2026-02-03

## Languages

**Primary:**
- Python 3.10+ - Application logic, CLI, GUI, voice processing pipeline

## Runtime

**Environment:**
- Python 3.10+ (checked at startup in `setup.py` lines 56-59)
- Requires macOS (darwin) for full feature set; falls back to CLI on other platforms

**Package Manager:**
- pip (standard Python package manager)
- Lockfile: `requirements.txt` - pinned with minimum versions (no lock file)

## Frameworks

**Core Application:**
- rumps 0.4.0+ - macOS menu bar application framework (`voiceflow.py` lines 28-30, 412-558)
  - Optional: Falls back to CLI mode if unavailable

**Audio Processing:**
- sounddevice 0.4.6+ - Real-time audio input/output (`voiceflow.py` lines 33-34, 161-229)
- numpy 1.24.0+ - Numerical audio data handling (`voiceflow.py` lines 34, 212)

**Input Handling:**
- pynput 1.7.6+ - Cross-platform keyboard and mouse input (`voiceflow.py` lines 40-42, 326-406)

**GUI:**
- tkinter - Built-in Python GUI toolkit (`settings_gui.py` lines 14-18)
  - Cross-platform; macOS styling in lines 91-96

**API & Transcription:**
- openai 1.12.0+ - Official OpenAI Python client (`voiceflow.py` lines 45-47, 236-319)

## Key Dependencies

**Critical:**
- openai 1.52.2 - Speech-to-text (Whisper) and text cleanup (GPT)
- sounddevice 0.5.5 - Microphone audio capture
- numpy 1.26.4 - Audio frame data handling
- pynput 1.8.1 - Global hotkey detection

**Infrastructure:**
- rumps 0.4.0 - macOS menu bar integration (optional but strongly recommended)

**System-level:**
- PortAudio (installed via Homebrew on macOS) - Required by sounddevice (`setup.py` lines 93-109)

## Configuration

**Environment:**
- Configuration stored in JSON: `~/.voiceflow/config.json`
- Custom dictionary: `~/.voiceflow/dictionary.txt`
- Logs: `~/.voiceflow/voiceflow.log`
- Recordings (optional): `~/.voiceflow/recordings/`

**Environment Variables:**
- `OPENAI_API_KEY` - Can override config file API key (fallback in `voiceflow.py` line 246)

**Key Configs Required:**
- `api_key` - OpenAI API key (required for operation)
- `hotkey` - Recording trigger (default: "option")
- `mode` - Recording mode: "hold" or "toggle" (default: "hold")
- `ai_cleanup` - Post-processing with GPT (default: true)
- `cleanup_model` - GPT model for cleanup (default: "gpt-4o-mini")

## Build & Development

**Setup & Installation:**
- `setup.py` - Interactive setup wizard (`setup.py` lines 275-373)
  - Checks Python version
  - Installs pip packages
  - Installs PortAudio via Homebrew
  - Guides API key configuration
  - Creates config files and launch scripts

**Launch:**
- `start.sh` - Bash launch script (created by setup, referenced in `setup.py` lines 218-229)
- Entry point: `voiceflow.py` main() function (lines 660-678)

**Alternative Launcher:**
- `settings_gui.py` - Standalone settings editor using tkinter

## Platform Requirements

**Development:**
- macOS or Linux/Windows (with reduced feature set)
- Python 3.10+
- pip
- Homebrew (for macOS PortAudio installation)

**Runtime - Full Featured (macOS):**
- macOS (Catalina or later recommended)
- Microphone access
- Accessibility permissions (for keyboard & paste)
- PortAudio library
- OpenAI API account with valid key

**Runtime - Fallback (Non-macOS):**
- Python 3.10+
- Dependencies installed
- OpenAI API key
- Microphone device
- No menu bar UI; CLI mode only

## Conditional Dependencies

**macOS-only:**
- rumps - Gracefully skipped on non-macOS (`voiceflow.py` line 672)
- afplay command - Sound feedback via macOS
- osascript - Paste simulation and notifications (`voiceflow.py` lines 138-154)
- Accessibility framework - Required for global keyboard listener

**Optional:**
- Homebrew - For PortAudio installation (manual install alternative in `setup.py` line 108)

---

*Stack analysis: 2026-02-03*
