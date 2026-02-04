"""VoiceFlow application classes."""

import os
import sys
import time
import threading
import shutil
from datetime import datetime

# Lazy imports for optional dependencies
try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .config import (
    APP_NAME, APP_VERSION, CONFIG_DIR, CONFIG_FILE, DICTIONARY_FILE,
    LOG_FILE, RECORDING_DIR, DEFAULT_CONFIG,
    log, load_config, save_config, load_dictionary,
)
from .audio import AudioRecorder
from .transcriber import Transcriber, TranscriptionError
from .hotkey import get_active_hotkey, get_hotkey_display_name, PRIMARY_HOTKEY, ALTERNATE_HOTKEY

# Import platform services
from voiceflow.platform import clipboard, notifications, sounds, tray


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def paste_transcription(text: str) -> bool:
    """Copy text to clipboard and paste. Handle failures gracefully.

    Per CONTEXT.md:
    - On failure: error sound + notification "Paste failed - text copied to clipboard"
    - Leave transcription in clipboard so user can manually paste

    Args:
        text: The transcription text to paste

    Returns:
        True if paste succeeded, False if it failed (text still in clipboard)
    """
    # Always copy to clipboard first (user decision: leave in clipboard on failure)
    clipboard.copy_to_clipboard(text)

    try:
        clipboard.paste()
        return True
    except Exception as e:
        log(f"Paste failed: {e}")
        sounds.play("error")
        notifications.send(
            "Paste Failed",
            "Paste failed - text copied to clipboard"
        )
        # Don't raise - text is in clipboard, user can paste manually
        return False


# ---------------------------------------------------------------------------
# Hotkey Listener
# ---------------------------------------------------------------------------

class HotkeyManager:
    """Listens for the configured hotkey to trigger recording."""

    # Map config names -> pynput Key objects
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

# Get the base class from tray service
_TrayAppBase = tray.get_app_class()

# Need rumps for menu items even if not using as base
try:
    import rumps
except ImportError:
    rumps = None


class VoiceFlowApp(_TrayAppBase if _TrayAppBase is not None else object):
    """macOS menu-bar application for VoiceFlow."""

    ICON_IDLE = "mic"
    ICON_RECORDING = "mic.fill"

    def __init__(self, config: dict = None, is_fallback_hotkey: bool = False):
        if _TrayAppBase is not None:
            super().__init__(
                APP_NAME,
                title="mic",
                quit_button=None,
            )
        self.config = config if config is not None else load_config()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(self.config)
        self.hotkey_mgr = None
        self._processing = False
        self._is_fallback_hotkey = is_fallback_hotkey

        # Build menu
        if rumps is not None:
            self.status_item = rumps.MenuItem("Ready — waiting for hotkey", callback=None)
            self.status_item.set_callback(None)

            hotkey_display = get_hotkey_display_name(self.config["hotkey"])
            mode_display = "Hold" if self.config["mode"] == "hold" else "Toggle"
            # Show fallback indicator in menu if using fallback hotkey
            fallback_indicator = " (fallback)" if is_fallback_hotkey else ""
            self.hotkey_info = rumps.MenuItem(f"Hotkey: {hotkey_display}{fallback_indicator} ({mode_display})", callback=None)

            self.menu = [
                self.status_item,
                self.hotkey_info,
                None,  # separator
                rumps.MenuItem("Settings...", callback=self.open_settings),
                rumps.MenuItem("View Log", callback=self.view_log),
                rumps.MenuItem("Open Config Folder", callback=self.open_config_folder),
                None,
                rumps.MenuItem("About VoiceFlow", callback=self.show_about),
                rumps.MenuItem("Quit VoiceFlow", callback=self.quit_app),
            ]

    def _start_recording(self):
        if self._processing:
            return
        if self.config.get("sound_feedback"):
            sounds.play("start")
        self.title = self.ICON_RECORDING
        if rumps is not None:
            self.status_item.title = "Recording..."
        self.recorder.start()

    def _stop_recording(self):
        if not self.recorder.is_recording:
            return
        audio_path = self.recorder.stop()
        if self.config.get("sound_feedback"):
            sounds.play("stop")
        self.title = "hourglass"
        if rumps is not None:
            self.status_item.title = "Transcribing..."

        if audio_path:
            # Process in background thread
            threading.Thread(target=self._process_audio, args=(audio_path,), daemon=True).start()
        else:
            self.title = self.ICON_IDLE
            if rumps is not None:
                self.status_item.title = "Ready — waiting for hotkey"

    def _process_audio(self, audio_path: str):
        self._processing = True
        try:
            text = self.transcriber.process(audio_path)
            if text:
                if self.config.get("auto_paste", True):
                    paste_success = paste_transcription(text)
                    if paste_success:
                        log(f"Pasted: {text[:80]}...")
                    # If paste failed, paste_transcription already showed error notification
                if self.config.get("show_notification"):
                    preview = text[:80] + ("..." if len(text) > 80 else "")
                    notifications.send("VoiceFlow", preview)
                # Save recording if configured
                if self.config.get("save_recordings"):
                    RECORDING_DIR.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest = RECORDING_DIR / f"recording_{ts}.wav"
                    shutil.copy2(audio_path, dest)
                if rumps is not None:
                    self.status_item.title = f"Last: {text[:50]}..."
            else:
                if rumps is not None:
                    self.status_item.title = "No speech detected"
                if self.config.get("sound_feedback"):
                    sounds.play("error")
        except TranscriptionError as e:
            # TranscriptionError already played sound and showed notification in transcriber
            log(f"Transcription error: {e}")
            if rumps is not None:
                self.status_item.title = f"Error: {str(e)[:40]}"
        except Exception as e:
            # Unexpected errors - play sound and notify
            log(f"Error processing audio: {e}")
            if rumps is not None:
                self.status_item.title = f"Error: {str(e)[:40]}"
            if self.config.get("sound_feedback"):
                sounds.play("error")
            if self.config.get("show_notification"):
                notifications.send("VoiceFlow Error", str(e)[:100])
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
        import subprocess
        # Ensure config exists
        save_config(self.config)
        subprocess.run(["open", str(CONFIG_FILE)])

    def view_log(self, _):
        import subprocess
        if LOG_FILE.exists():
            subprocess.run(["open", "-a", "Console", str(LOG_FILE)])
        else:
            notifications.send(APP_NAME, "No log file yet.")

    def open_config_folder(self, _):
        import subprocess
        subprocess.run(["open", str(CONFIG_DIR)])

    def show_about(self, _):
        if rumps is not None:
            rumps.alert(
                title=f"About {APP_NAME}",
                message=(
                    f"{APP_NAME} v{APP_VERSION}\n\n"
                    "A Wispr Flow-inspired voice typing tool for macOS.\n"
                    "Hold a hotkey -> speak -> release -> text appears at your cursor.\n\n"
                    "Powered by OpenAI Whisper & GPT.\n"
                    "https://github.com/your-repo/voiceflow"
                ),
            )

    def quit_app(self, _):
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        if rumps is not None:
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
        if _TrayAppBase is not None:
            super().run(**kwargs)


# ---------------------------------------------------------------------------
# CLI fallback (no rumps / non-macOS)
# ---------------------------------------------------------------------------

class VoiceFlowCLI:
    """Terminal-based fallback for systems without rumps."""

    def __init__(self, config: dict = None, is_fallback_hotkey: bool = False):
        self.config = config if config is not None else load_config()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(self.config)
        self._processing = False
        self._is_fallback_hotkey = is_fallback_hotkey

    def _start_recording(self):
        if self._processing:
            return
        print("\nRecording... (release hotkey to stop)")
        self.recorder.start()

    def _stop_recording(self):
        if not self.recorder.is_recording:
            return
        audio_path = self.recorder.stop()
        print("Transcribing...")
        if audio_path:
            threading.Thread(target=self._process_audio, args=(audio_path,), daemon=True).start()
        else:
            print("No audio captured")

    def _process_audio(self, audio_path: str):
        self._processing = True
        try:
            text = self.transcriber.process(audio_path)
            if text:
                print(f"\nTranscription:\n{text}\n")
                if self.config.get("auto_paste", True):
                    paste_success = paste_transcription(text)
                    if paste_success:
                        print("Pasted to cursor!")
                    else:
                        print("Paste failed - text copied to clipboard")
            else:
                print("No speech detected")
        except TranscriptionError as e:
            # TranscriptionError already played sound and showed notification
            print(f"Transcription error: {e}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self._processing = False
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def run(self):
        log(f"{APP_NAME} v{APP_VERSION} started (CLI mode)")
        hotkey_display = get_hotkey_display_name(self.config['hotkey'])
        fallback_indicator = " (fallback)" if self._is_fallback_hotkey else ""
        print(f"""
+------------------------------------------------------+
|              VoiceFlow v{APP_VERSION}                    |
|                                                      |
|   Hotkey : {hotkey_display + fallback_indicator:<20s}               |
|   Mode   : {self.config['mode']:<10s}                        |
|   AI Cleanup : {'On' if self.config.get('ai_cleanup') else 'Off':<5s}                              |
|                                                      |
|   Press Ctrl+C to quit                               |
+------------------------------------------------------+
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
            print("\nVoiceFlow stopped.")


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
        print(f"Missing required packages: {', '.join(missing)}")
        print(f"   Install them with: pip install {' '.join(missing)}")
        sys.exit(1)


def check_microphone() -> bool:
    """Check if a microphone is available. Warn if not.

    Returns True if microphone is available, False otherwise.
    Does not exit - user might connect a mic later.
    """
    try:
        sd.check_input_settings()
        log("Microphone check passed")
        return True
    except sd.PortAudioError as e:
        print(f"Warning: No microphone detected - {e}")
        print("VoiceFlow requires a microphone for voice recording.")
        print("Please connect a microphone and restart the application.")
        # Log the full device list for debugging
        log(f"No microphone detected. Error: {e}")
        try:
            log(f"Available audio devices: {sd.query_devices()}")
        except Exception:
            log("Could not query audio devices")
        return False


def main():
    check_dependencies()
    if not check_microphone():
        # Continue anyway - user might connect mic later
        # But they've been warned
        pass

    # Ensure config directory exists with defaults
    cfg = load_config()
    save_config(cfg)

    # Create dictionary file if it doesn't exist
    if not DICTIONARY_FILE.exists():
        DICTIONARY_FILE.write_text("# Add custom words/names here, one per line\n# These help Whisper recognize uncommon terms\n")

    # Detect available hotkey with fallback
    active_hotkey, is_fallback = get_active_hotkey()

    if is_fallback:
        # Notify user about fallback (one-time notification per CONTEXT.md)
        fallback_display = get_hotkey_display_name(active_hotkey)
        notifications.send(
            "Hotkey Changed",
            f"Primary hotkey unavailable. Using {fallback_display} instead."
        )
        log(f"Using fallback hotkey: {active_hotkey}")

    # Override config hotkey with active hotkey
    cfg["hotkey"] = active_hotkey

    # Choose menu-bar app or CLI
    if tray.is_available() and sys.platform == "darwin":
        app = VoiceFlowApp(config=cfg, is_fallback_hotkey=is_fallback)
        app.run()
    else:
        cli = VoiceFlowCLI(config=cfg, is_fallback_hotkey=is_fallback)
        cli.run()


if __name__ == "__main__":
    main()
