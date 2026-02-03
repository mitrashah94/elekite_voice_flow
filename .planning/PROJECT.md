# VoiceFlow

## What This Is

A voice-to-text dictation tool that runs in the system tray, letting users press a hotkey to record speech, transcribe it via OpenAI Whisper, and automatically paste the cleaned-up text into any application. Currently macOS-only, being extended to Windows with full feature parity.

## Core Value

Users can dictate text anywhere on their computer with a single hotkey — the transcription appears where their cursor is, no copy-paste required.

## Requirements

### Validated

- ✓ Global hotkey triggers recording (hold or toggle mode) — existing
- ✓ Audio capture and OpenAI Whisper transcription — existing
- ✓ Optional GPT text cleanup (removes filler words, fixes grammar) — existing
- ✓ Auto-paste transcribed text to active application — existing
- ✓ System tray/menu bar UI with status display — existing
- ✓ Notifications showing transcription preview — existing
- ✓ Sound feedback for recording start/stop/error — existing
- ✓ Settings GUI for configuration — existing
- ✓ Custom dictionary for domain-specific terms — existing
- ✓ Optional recording history — existing
- ✓ Auto-start on login option — existing
- ✓ CLI fallback mode — existing

### Active

- [ ] Cross-platform architecture with shared core and platform-specific modules
- [ ] Windows audio capture (sounddevice)
- [ ] Windows global hotkey listener (pynput)
- [ ] Windows clipboard and paste simulation
- [ ] Windows system tray with menu
- [ ] Windows toast notifications
- [ ] Windows sound feedback
- [ ] Windows auto-start (startup folder)
- [ ] Windows setup wizard
- [ ] Platform detection and automatic switching
- [ ] macOS functionality verified after refactor (no regressions)

### Out of Scope

- Voice commands for system control — not a voice assistant, just dictation
- Mobile versions — desktop only for now
- Other languages for the app UI — English only
- Non-Python languages — constraint from user

## Context

The existing macOS implementation uses:
- Python 3.11+ with PyQt6-free stack (rumps for menu bar, pynput for hotkeys)
- OpenAI Whisper API for transcription, GPT for cleanup
- sounddevice for audio capture (backed by PortAudio)
- macOS-specific: osascript for paste/notifications, afplay for sounds, launchctl for auto-start

Windows equivalents exist for all platform-specific features:
- pystray or similar for system tray
- win32api or pyautogui for paste simulation
- win10toast or windows-toasts for notifications
- winsound for audio feedback
- Windows startup folder for auto-start

The codebase is well-structured with clear separation (AudioRecorder, Transcriber, HotkeyManager, VoiceFlowApp classes) which should make the refactor to cross-platform manageable.

## Constraints

- **Language**: Python only — user requirement
- **Feature parity**: Windows version must match macOS UX (hotkey, tray, notifications, auto-paste)
- **Shared codebase**: Single codebase with platform-specific modules, not separate projects
- **No macOS regression**: Existing macOS functionality must remain fully working — refactoring cannot break the current app

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Shared codebase with platform modules | 70% of code already cross-platform (Python, OpenAI API), minimizes maintenance | — Pending |
| Python-only constraint | User preference, keeps stack simple | — Pending |
| Non-destructive refactor | macOS app must keep working throughout — test on macOS after each change | — Pending |

---
*Last updated: 2026-02-03 after initialization*
