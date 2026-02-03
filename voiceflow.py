#!/usr/bin/env python3
"""
VoiceFlow — A Wispr Flow-inspired voice typing app for macOS.

Hold a hotkey to record your voice, release to transcribe and auto-type
the result wherever your cursor is. Uses OpenAI Whisper for transcription
and optionally cleans up text with GPT.

Usage:
    python voiceflow.py
"""

import os
import sys
import json
import time
import wave
import tempfile
import threading
import subprocess
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Lazy / conditional imports — we check availability at startup
# ---------------------------------------------------------------------------
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

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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
    "save_recordings": False,
    "custom_prompt": "",          # extra instructions for cleanup
    "whisper_prompt": "",         # prompt/context hint for Whisper
    "max_recording_seconds": 300,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def load_config() -> dict:
    """Load config from disk, filling in defaults for missing keys."""
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


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def load_dictionary() -> list[str]:
    """Load custom dictionary words (one per line)."""
    if DICTIONARY_FILE.exists():
        return [w.strip() for w in DICTIONARY_FILE.read_text().splitlines() if w.strip()]
    return []


def play_sound(name: str):
    """Play a system sound (macOS)."""
    sounds = {
        "start": "/System/Library/Sounds/Pop.aiff",
        "stop": "/System/Library/Sounds/Purr.aiff",
        "error": "/System/Library/Sounds/Basso.aiff",
    }
    path = sounds.get(name)
    if path and os.path.exists(path):
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def paste_text(text: str):
    """Copy text to clipboard and simulate Cmd+V to paste at cursor."""
    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    process.communicate(text.encode("utf-8"))
    # Small delay so clipboard is ready
    time.sleep(0.05)
    # Use osascript to simulate Cmd+V
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to keystroke "v" using command down'
    ], capture_output=True)


def send_notification(title: str, message: str):
    """Send a macOS notification."""
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ], capture_output=True)


# ---------------------------------------------------------------------------
# Audio Recorder
# ---------------------------------------------------------------------------

class AudioRecorder:
    """Records audio from the default input device using sounddevice."""

    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list = []
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._callback,
                blocksize=1024,
            )
            self._stream.start()
            log("Recording started")

    def _callback(self, indata, frames, time_info, status):
        if status:
            log(f"Audio status: {status}")
        self._frames.append(indata.copy())

    def stop(self) -> str | None:
        """Stop recording and return the path to a WAV file, or None."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        if not self._frames:
            log("No audio frames captured")
            return None

        audio_data = np.concatenate(self._frames, axis=0)
        duration = len(audio_data) / self.sample_rate
        log(f"Recording stopped — {duration:.1f}s of audio")

        if duration < 0.3:
            log("Recording too short, discarding")
            return None

        # Write to a temp WAV file
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        log(f"Saved recording to {tmp.name}")
        return tmp.name


# ---------------------------------------------------------------------------
# Transcription & AI cleanup
# ---------------------------------------------------------------------------

class Transcriber:
    """Handles Whisper transcription and optional GPT text cleanup."""

    def __init__(self, config: dict):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("No OpenAI API key configured. Set it in ~/.voiceflow/config.json or OPENAI_API_KEY env var.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def transcribe(self, audio_path: str) -> str:
        """Send audio to Whisper and return raw transcript."""
        log(f"Transcribing {audio_path} ...")
        kwargs = {
            "model": self.config.get("whisper_model", "whisper-1"),
            "file": open(audio_path, "rb"),
            "response_format": "text",
        }
        lang = self.config.get("language")
        if lang:
            kwargs["language"] = lang

        # Build prompt from dictionary + user prompt
        prompt_parts = []
        if self.config.get("whisper_prompt"):
            prompt_parts.append(self.config["whisper_prompt"])
        dictionary = load_dictionary()
        if dictionary:
            prompt_parts.append("Custom terms: " + ", ".join(dictionary))
        if prompt_parts:
            kwargs["prompt"] = " | ".join(prompt_parts)

        result = self.client.audio.transcriptions.create(**kwargs)
        text = result.strip() if isinstance(result, str) else str(result).strip()
        log(f"Raw transcript: {text[:120]}...")
        return text

    def cleanup(self, raw_text: str) -> str:
        """Use GPT to clean up filler words, fix grammar, and format."""
        if not self.config.get("ai_cleanup", True):
            return raw_text

        log("Cleaning up transcript with AI ...")
        system_prompt = (
            "You are a voice-to-text post-processor. The user dictated the following text. "
            "Clean it up by:\n"
            "1. Removing filler words (um, uh, like, you know, so, basically, etc.)\n"
            "2. Fixing obvious grammar and punctuation\n"
            "3. Preserving the speaker's intended meaning and tone exactly\n"
            "4. Keeping the same level of formality\n"
            "5. Adding proper paragraph breaks if the text is long\n"
            "6. NOT changing the content, rephrasing, or adding information\n"
            "7. If the text looks like code or a command, preserve it exactly\n"
            "Return ONLY the cleaned text, nothing else."
        )
        if self.config.get("custom_prompt"):
            system_prompt += f"\n\nAdditional instructions: {self.config['custom_prompt']}"

        response = self.client.chat.completions.create(
            model=self.config.get("cleanup_model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        cleaned = response.choices[0].message.content.strip()
        log(f"Cleaned text: {cleaned[:120]}...")
        return cleaned

    def process(self, audio_path: str) -> str:
        """Full pipeline: transcribe → cleanup → return final text."""
        raw = self.transcribe(audio_path)
        if not raw:
            return ""
        final = self.cleanup(raw)
        return final


# ---------------------------------------------------------------------------
# Hotkey Listener
# ---------------------------------------------------------------------------

class HotkeyManager:
    """Listens for the configured hotkey to trigger recording."""

    # Map config names → pynput Key objects
    SPECIAL_KEYS = {
        "fn": pynput_keyboard.Key.f13 if pynput_keyboard else None,  # fn remapped
        "ctrl": pynput_keyboard.Key.ctrl if pynput_keyboard else None,
        "ctrl_r": pynput_keyboard.Key.ctrl_r if pynput_keyboard else None,
        "option": pynput_keyboard.Key.alt if pynput_keyboard else None,
        "option_r": pynput_keyboard.Key.alt_r if pynput_keyboard else None,
        "cmd": pynput_keyboard.Key.cmd if pynput_keyboard else None,
        "cmd_r": pynput_keyboard.Key.cmd_r if pynput_keyboard else None,
        "shift": pynput_keyboard.Key.shift if pynput_keyboard else None,
        "caps_lock": pynput_keyboard.Key.caps_lock if pynput_keyboard else None,
    }

    def __init__(self, hotkey_name: str, mode: str, on_start, on_stop):
        self.hotkey_name = hotkey_name.lower()
        self.mode = mode  # "hold" or "toggle"
        self.on_start = on_start
        self.on_stop = on_stop
        self._listener = None
        self._is_active = False
        self._pressed = False

    def _get_target_key(self):
        if self.hotkey_name in self.SPECIAL_KEYS:
            return self.SPECIAL_KEYS[self.hotkey_name]
        # Single character key
        try:
            return pynput_keyboard.KeyCode.from_char(self.hotkey_name)
        except Exception:
            return None

    def _matches(self, key) -> bool:
        target = self._get_target_key()
        if target is None:
            return False
        # Compare by value for special keys
        try:
            return key == target or (hasattr(key, 'value') and hasattr(target, 'value') and key.value == target.value)
        except Exception:
            return key == target

    def _on_press(self, key):
        if not self._matches(key):
            return
        if self.mode == "hold":
            if not self._pressed:
                self._pressed = True
                self.on_start()
        elif self.mode == "toggle":
            if not self._is_active:
                self._is_active = True
                self.on_start()
            else:
                self._is_active = False
                self.on_stop()

    def _on_release(self, key):
        if not self._matches(key):
            return
        if self.mode == "hold":
            if self._pressed:
                self._pressed = False
                self.on_stop()

    def start(self):
        log(f"Hotkey listener started — key={self.hotkey_name}, mode={self.mode}")
        self._listener = pynput_keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None


# ---------------------------------------------------------------------------
# Menu-bar App (rumps)
# ---------------------------------------------------------------------------

class VoiceFlowApp(rumps.App):
    """macOS menu-bar application for VoiceFlow."""

    ICON_IDLE = "🎙️"
    ICON_RECORDING = "🔴"

    def __init__(self):
        super().__init__(
            APP_NAME,
            title="🎙️",
            quit_button=None,
        )
        self.config = load_config()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(self.config)
        self.hotkey_mgr = None
        self._processing = False

        # Build menu
        self.status_item = rumps.MenuItem("Ready — waiting for hotkey", callback=None)
        self.status_item.set_callback(None)

        hotkey_display = self.config["hotkey"].capitalize()
        mode_display = "Hold" if self.config["mode"] == "hold" else "Toggle"
        self.hotkey_info = rumps.MenuItem(f"Hotkey: {hotkey_display} ({mode_display})", callback=None)

        self.menu = [
            self.status_item,
            self.hotkey_info,
            None,  # separator
            rumps.MenuItem("⚙️  Settings...", callback=self.open_settings),
            rumps.MenuItem("📖  View Log", callback=self.view_log),
            rumps.MenuItem("📂  Open Config Folder", callback=self.open_config_folder),
            None,
            rumps.MenuItem("About VoiceFlow", callback=self.show_about),
            rumps.MenuItem("Quit VoiceFlow", callback=self.quit_app),
        ]

    def _start_recording(self):
        if self._processing:
            return
        if self.config.get("sound_feedback"):
            play_sound("start")
        self.title = self.ICON_RECORDING
        self.status_item.title = "🔴  Recording..."
        self.recorder.start()

    def _stop_recording(self):
        if not self.recorder.is_recording:
            return
        audio_path = self.recorder.stop()
        if self.config.get("sound_feedback"):
            play_sound("stop")
        self.title = "⏳"
        self.status_item.title = "⏳  Transcribing..."

        if audio_path:
            # Process in background thread
            threading.Thread(target=self._process_audio, args=(audio_path,), daemon=True).start()
        else:
            self.title = self.ICON_IDLE
            self.status_item.title = "Ready — waiting for hotkey"

    def _process_audio(self, audio_path: str):
        self._processing = True
        try:
            text = self.transcriber.process(audio_path)
            if text:
                if self.config.get("auto_paste", True):
                    paste_text(text)
                    log(f"Pasted: {text[:80]}...")
                if self.config.get("show_notification"):
                    preview = text[:80] + ("..." if len(text) > 80 else "")
                    send_notification("VoiceFlow", preview)
                # Save recording if configured
                if self.config.get("save_recordings"):
                    RECORDING_DIR.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest = RECORDING_DIR / f"recording_{ts}.wav"
                    import shutil
                    shutil.copy2(audio_path, dest)
                self.status_item.title = f"✅  Last: {text[:50]}..."
            else:
                self.status_item.title = "⚠️  No speech detected"
                if self.config.get("sound_feedback"):
                    play_sound("error")
        except Exception as e:
            log(f"Error processing audio: {e}")
            self.status_item.title = f"❌  Error: {str(e)[:40]}"
            if self.config.get("sound_feedback"):
                play_sound("error")
            if self.config.get("show_notification"):
                send_notification("VoiceFlow Error", str(e)[:100])
        finally:
            self._processing = False
            self.title = self.ICON_IDLE
            # Clean up temp file
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    # --- Menu callbacks ---

    def open_settings(self, _):
        """Open the settings editor (launches the config file in default editor)."""
        # Ensure config exists
        save_config(self.config)
        subprocess.run(["open", str(CONFIG_FILE)])

    def view_log(self, _):
        if LOG_FILE.exists():
            subprocess.run(["open", "-a", "Console", str(LOG_FILE)])
        else:
            send_notification(APP_NAME, "No log file yet.")

    def open_config_folder(self, _):
        subprocess.run(["open", str(CONFIG_DIR)])

    def show_about(self, _):
        rumps.alert(
            title=f"About {APP_NAME}",
            message=(
                f"{APP_NAME} v{APP_VERSION}\n\n"
                "A Wispr Flow-inspired voice typing tool for macOS.\n"
                "Hold a hotkey → speak → release → text appears at your cursor.\n\n"
                "Powered by OpenAI Whisper & GPT.\n"
                "https://github.com/your-repo/voiceflow"
            ),
        )

    def quit_app(self, _):
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        rumps.quit_application()

    def run(self, **kwargs):
        """Override run to also start the hotkey listener."""
        self.hotkey_mgr = HotkeyManager(
            hotkey_name=self.config["hotkey"],
            mode=self.config["mode"],
            on_start=self._start_recording,
            on_stop=self._stop_recording,
        )
        self.hotkey_mgr.start()
        log(f"{APP_NAME} v{APP_VERSION} started")
        super().run(**kwargs)


# ---------------------------------------------------------------------------
# CLI fallback (no rumps / non-macOS)
# ---------------------------------------------------------------------------

class VoiceFlowCLI:
    """Terminal-based fallback for systems without rumps."""

    def __init__(self):
        self.config = load_config()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(self.config)
        self._processing = False

    def _start_recording(self):
        if self._processing:
            return
        print("\n🔴  Recording... (release hotkey to stop)")
        self.recorder.start()

    def _stop_recording(self):
        if not self.recorder.is_recording:
            return
        audio_path = self.recorder.stop()
        print("⏳  Transcribing...")
        if audio_path:
            threading.Thread(target=self._process_audio, args=(audio_path,), daemon=True).start()
        else:
            print("⚠️  No audio captured")

    def _process_audio(self, audio_path: str):
        self._processing = True
        try:
            text = self.transcriber.process(audio_path)
            if text:
                print(f"\n✅  Transcription:\n{text}\n")
                if self.config.get("auto_paste", True):
                    paste_text(text)
                    print("📋  Pasted to cursor!")
            else:
                print("⚠️  No speech detected")
        except Exception as e:
            print(f"❌  Error: {e}")
        finally:
            self._processing = False
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def run(self):
        log(f"{APP_NAME} v{APP_VERSION} started (CLI mode)")
        print(f"""
╔══════════════════════════════════════════════════════╗
║              🎙️  VoiceFlow v{APP_VERSION}               ║
║                                                      ║
║   Hotkey : {self.config['hotkey']:<10s}  Mode : {self.config['mode']:<10s}      ║
║   AI Cleanup : {'On' if self.config.get('ai_cleanup') else 'Off':<5s}                              ║
║                                                      ║
║   Press Ctrl+C to quit                               ║
╚══════════════════════════════════════════════════════╝
        """)

        hotkey_mgr = HotkeyManager(
            hotkey_name=self.config["hotkey"],
            mode=self.config["mode"],
            on_start=self._start_recording,
            on_stop=self._stop_recording,
        )
        hotkey_mgr.start()

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            hotkey_mgr.stop()
            print("\n👋  VoiceFlow stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def check_dependencies():
    """Check that required packages are installed."""
    missing = []
    if sd is None:
        missing.append("sounddevice")
    if np is None:
        missing.append("numpy")
    if pynput_keyboard is None:
        missing.append("pynput")
    if OpenAI is None:
        missing.append("openai")
    if missing:
        print(f"❌  Missing required packages: {', '.join(missing)}")
        print(f"   Install them with: pip install {' '.join(missing)}")
        sys.exit(1)


def main():
    check_dependencies()

    # Ensure config directory exists with defaults
    cfg = load_config()
    save_config(cfg)

    # Create dictionary file if it doesn't exist
    if not DICTIONARY_FILE.exists():
        DICTIONARY_FILE.write_text("# Add custom words/names here, one per line\n# These help Whisper recognize uncommon terms\n")

    # Choose menu-bar app or CLI
    if rumps is not None and sys.platform == "darwin":
        app = VoiceFlowApp()
        app.run()
    else:
        cli = VoiceFlowCLI()
        cli.run()


if __name__ == "__main__":
    main()
