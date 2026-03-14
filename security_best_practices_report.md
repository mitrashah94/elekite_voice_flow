# VoiceFlow Security Best Practices Report

## Executive Summary

VoiceFlow is a local desktop application, so its primary security risks are local secret exposure, unnecessary persistence of sensitive user content, and weak defaults around files created under the user's home directory. The review found three top-priority issues: the OpenAI API key is stored in plaintext on disk, transcribed user content is written to logs and notifications, and multiple sensitive files are created without enforcing owner-only permissions. These issues increase the chance that other local users, backup/sync systems, endpoint tooling, or shared workstation environments can access credentials or transcript data.

The application does not show evidence of classic remote-code-execution or shell-injection vulnerabilities in the reviewed paths. The main work should focus on privacy-by-default hardening, safe secret handling, and consistent secure file-write behavior across config, logs, recordings, and meeting transcripts.

## Scope and Method

Reviewed code paths:

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/transcriber.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/audio.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/meeting.py`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/clipboard.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/notifications.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/autostart.py`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/windows/notifications.py`

Severity ratings use a desktop-app threat model with a strict privacy-by-default bar.

## Critical Findings

### SBP-001: OpenAI API key is persisted in plaintext in user config

**Severity:** Critical

**Impact:** Any local process, user, backup tool, or sync target that can read `~/.voiceflow/config.json` can recover the OpenAI API key and use it outside the app.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:79`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:81`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:161`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:163`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:416`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:493`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:115`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:117`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:306`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:322`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/transcriber.py:40`

**Details**

The application treats `config.json` as a normal storage location for `api_key`, loads it directly into memory, and rewrites it from both the setup wizard and the settings GUI. This makes the secret durable on disk by default instead of using OS-backed secure storage or requiring an environment variable.

**Recommendation**

- Store the API key in secure storage by default:
  - macOS: Keychain
  - Windows: Credential Manager or DPAPI-backed storage
- Keep `OPENAI_API_KEY` as a supported fallback for headless and developer workflows.
- Migrate existing users explicitly:
  - On startup, if `config.json` contains `api_key`, import it into secure storage.
  - After successful migration, remove `api_key` from `config.json`.
  - If secure storage is unavailable, warn clearly and fall back to environment variable guidance plus restrictive file permissions.
- Update setup and settings flows so they read/write the secure store, not the config file.

## High Findings

### SBP-002: Transcript content is written to persistent logs

**Severity:** High

**Impact:** User speech content, including potentially sensitive dictated text, can be recovered from `~/.voiceflow/voiceflow.log` even after the app finishes processing.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/transcriber.py:83`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/transcriber.py:159`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:290`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:555`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:52`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:58`

**Details**

The app logs raw transcript text, cleaned text, and pasted text previews. This turns transient dictated content into durable local records. In practice, logs often outlive the original clipboard state, survive backups, and are easier for endpoint agents or other users to collect than live process memory.

**Recommendation**

- Remove transcript body content from persistent logs by default.
- Log only operational metadata such as:
  - audio file path or opaque recording/session ID
  - transcript length
  - processing duration
  - model name
  - error class
- If verbose content logging is ever needed for debugging, guard it behind an explicit opt-in debug mode with a strong warning.

### SBP-003: Sensitive app data is written without enforcing restrictive file permissions

**Severity:** High

**Impact:** Config files, logs, recordings, and meeting transcripts may inherit permissive defaults from the process umask or parent directory, exposing sensitive data to other local users or software.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:57`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:58`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:67`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/config.py:81`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:162`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:163`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:518`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:519`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:243`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:269`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:321`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:322`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:297`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:300`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:562`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:565`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/meeting.py:595`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/meeting.py:602`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/audio.py:109`

**Details**

The code creates and writes security-relevant files under `~/.voiceflow`, `~/Library/LaunchAgents`, temporary recording files, and meeting output directories without explicit permission control. On Unix-like systems, this leaves confidentiality dependent on the runtime umask and any pre-existing directory state.

**Recommendation**

- Centralize file and directory creation behind secure helpers.
- Target restrictive defaults where supported:
  - directories: `0700`
  - files: `0600`
- Apply the helper consistently to:
  - `config.json`
  - `dictionary.txt`
  - `voiceflow.log`
  - saved recordings
  - meeting transcript outputs
  - temporary audio files where practical
- On Windows, use the narrowest practical ACL approach available through the chosen storage/write mechanism and avoid assuming POSIX modes are sufficient.

## Medium Findings

### SBP-004: Transcript previews are exposed through system notifications

**Severity:** Medium

**Impact:** Dictated content can appear on screen, in notification history, or in OS-level notification logging surfaces.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:292`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:293`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:557`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:558`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/notifications.py:11`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/windows/notifications.py:19`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/windows/notifications.py:29`

**Details**

The app sends the first 80 characters of transcribed text to notifications. On Windows, the fallback implementation also logs the full notification message, which can further persist that content to disk.

**Recommendation**

- Default notifications to status-only messages such as "Transcription complete".
- If content previews remain available, make them explicit opt-in and warn about privacy impact.
- Remove notification-body logging in the Windows fallback path.

### SBP-005: Clipboard-based paste flow leaves sensitive text in the global clipboard by design

**Severity:** Medium

**Impact:** Other applications, clipboard history tools, and remote desktop environments may access dictated text after transcription.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:73`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:86`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/app.py:97`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/clipboard.py:12`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/windows/clipboard.py:17`

**Details**

The app intentionally copies text to the system clipboard before simulating paste and leaves it there on paste failure. This is reasonable for usability, but it increases exposure in environments with clipboard managers, shared sessions, or endpoint monitoring.

**Recommendation**

- Document the privacy tradeoff clearly in settings and onboarding.
- Offer an optional "clear clipboard after successful paste" mode when compatible with user expectations.
- Preserve the current failure fallback, but make it explicit to the user that sensitive text remains in the clipboard.

## Low Findings

### SBP-006: LaunchAgent and helper script outputs create additional persistent data surfaces

**Severity:** Low

**Impact:** Autostart logs and helper files can retain operational details and may inherit permissive file permissions.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:221`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:227`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:262`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:265`
- `/Users/mitrashah/Desktop/VoiceFlow/setup.py:269`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/autostart.py:33`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/autostart.py:36`

**Details**

The setup flow creates `start.sh` and optionally a LaunchAgent plist that redirects stdout/stderr to files under `~/.voiceflow`. This expands the set of files that may contain sensitive operational data if transcript logging remains enabled.

**Recommendation**

- Apply the same secure file-write helper to the launcher and LaunchAgent artifacts.
- Prefer minimal stdout/stderr logging in background mode.
- Reassess whether background logs are needed once transcript/body logging is removed.

### SBP-007: User-controlled prompts are forwarded directly to model instructions without trust boundaries or privacy guidance

**Severity:** Low

**Impact:** Users can unintentionally send more contextual or sensitive text to model APIs than expected, especially via cleanup and Whisper prompts.

**Evidence**

- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/transcriber.py:68`
- `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/core/transcriber.py:145`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:297`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:318`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:504`
- `/Users/mitrashah/Desktop/VoiceFlow/settings_gui.py:505`

**Details**

This is not a code-injection issue in the current design; the values are intentionally sent to OpenAI. The risk is privacy and user expectation: custom prompts can include names, project context, or sensitive instructions that increase data disclosure to the API.

**Recommendation**

- Add brief UI guidance that custom prompts are sent to the model provider.
- Keep these values out of logs.
- Consider a short privacy note near the prompt fields and meeting settings.

## Positive Notes

- macOS notification code escapes double quotes before interpolating into AppleScript, which reduces obvious quoting issues in that path: `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/notifications.py:13`
- macOS clipboard paste uses fixed command arguments rather than shell invocation: `/Users/mitrashah/Desktop/VoiceFlow/voiceflow/platform/macos/clipboard.py:21`
- The reviewed subprocess usage generally passes argument arrays rather than shell strings, which avoids common shell-injection risks.

## Remediation Plan

### 1. Secret storage migration

- Add a small credential abstraction with methods like `get_api_key()`, `set_api_key()`, and `delete_api_key()`.
- Provide implementations for:
  - macOS Keychain
  - Windows secure credential storage
  - environment-variable fallback
- Startup behavior:
  - Read secure store first.
  - If empty, check `OPENAI_API_KEY`.
  - If still empty, check legacy `config.json["api_key"]`.
  - If legacy key exists, migrate it into secure storage, then remove it from config.
- Update setup and settings UI to save via the credential abstraction instead of writing plaintext into config.

### 2. Data-minimizing logging

- Replace content-bearing log lines with metadata-only events.
- Remove:
  - raw transcript preview logging
  - cleaned transcript preview logging
  - pasted-text preview logging
  - notification fallback logging that includes message bodies
- Keep:
  - state transitions
  - durations
  - model identifiers
  - exception classes and short operational messages

### 3. Secure file-write policy

- Add shared helpers for secure directory creation and atomic file writing.
- Enforce owner-only permissions on Unix-like systems for:
  - config directory
  - config file
  - dictionary file
  - app log
  - recording outputs
  - meeting transcript outputs
  - temp audio files where possible
- Ensure custom meeting output directories are created securely when VoiceFlow creates them.
- Apply the same policy to LaunchAgent and helper-script generation.

### 4. Privacy-safe output defaults

- Change notifications to status-only by default.
- Keep transcript previews and clipboard retention as explicit, user-visible privacy tradeoffs.
- Add short privacy copy in the settings UI around:
  - auto-paste / clipboard behavior
  - custom prompts
  - meeting transcript file outputs

## Validation Criteria for Future Fixes

- Existing users with `config.json["api_key"]` can still launch successfully and are migrated without manual JSON edits.
- New installs do not persist the API key in plaintext config by default.
- `~/.voiceflow/voiceflow.log` no longer contains transcript text or cleaned output.
- Windows notification fallback does not log transcript-bearing notification bodies.
- Files created for config, logs, recordings, and meeting transcripts are not group/world readable on supported platforms.
- Meeting mode still saves transcripts correctly in both the default directory and a user-selected output directory.
- Paste fallback still leaves text accessible to the user, with accurate messaging about clipboard retention.

## Recommended Fix Order

1. Remove transcript/body logging and notification-body logging.
2. Introduce secure API-key storage with legacy migration.
3. Add secure file/directory creation helpers and apply them consistently.
4. Tighten notification defaults and add privacy guidance in UI/setup text.

