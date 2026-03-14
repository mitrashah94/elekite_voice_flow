#!/usr/bin/env python3
"""
VoiceFlow Installer & Setup Wizard
Guides the user through installing dependencies and configuring VoiceFlow.
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

from voiceflow.core.config import save_config, save_dictionary, write_secure_text
from voiceflow.core.credentials import (
    describe_api_key_storage,
    get_api_key,
    load_stored_api_key,
    migrate_legacy_api_key,
    save_api_key,
)

APP_NAME = "VoiceFlow"
CONFIG_DIR = Path.home() / ".voiceflow"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "voiceflow.log"

REQUIRED_PACKAGES = [
    "sounddevice",
    "numpy",
    "pynput",
    "openai",
    "rumps",  # macOS only
]

BANNER = r"""
 ╔═══════════════════════════════════════════════════════════╗
 ║                                                           ║
 ║    ██╗   ██╗ ██████╗ ██╗ ██████╗███████╗                 ║
 ║    ██║   ██║██╔═══██╗██║██╔════╝██╔════╝                 ║
 ║    ██║   ██║██║   ██║██║██║     █████╗                   ║
 ║    ╚██╗ ██╔╝██║   ██║██║██║     ██╔══╝                   ║
 ║     ╚████╔╝ ╚██████╔╝██║╚██████╗███████╗                 ║
 ║      ╚═══╝   ╚═════╝ ╚═╝ ╚═════╝╚══════╝                ║
 ║                                                           ║
 ║          ███████╗██╗      ██████╗ ██╗    ██╗              ║
 ║          ██╔════╝██║     ██╔═══██╗██║    ██║              ║
 ║          █████╗  ██║     ██║   ██║██║ █╗ ██║              ║
 ║          ██╔══╝  ██║     ██║   ██║██║███╗██║              ║
 ║          ██║     ███████╗╚██████╔╝╚███╔███╔╝              ║
 ║          ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝              ║
 ║                                                           ║
 ║       🎙️  Voice Typing for macOS — Setup Wizard           ║
 ╚═══════════════════════════════════════════════════════════╝
"""


def print_step(num, total, msg):
    print(f"\n{'─'*60}")
    print(f"  Step {num}/{total}: {msg}")
    print(f"{'─'*60}")


def check_python():
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"❌  Python 3.10+ required (you have {v.major}.{v.minor}.{v.micro})")
        sys.exit(1)
    print(f"✅  Python {v.major}.{v.minor}.{v.micro}")


def check_macos():
    if sys.platform != "darwin":
        print("⚠️   Not running on macOS. Some features (menu bar, paste) won't work.")
        print("    The CLI mode will still function for transcription.\n")
        return False
    print("✅  macOS detected")
    return True


def install_packages():
    """Install required Python packages."""
    print("\nInstalling required packages...\n")
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg if pkg != "sounddevice" else "sounddevice")
            print(f"  ✅  {pkg} (already installed)")
        except ImportError:
            print(f"  📦  Installing {pkg}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  ✅  {pkg} installed")
            else:
                print(f"  ⚠️  Failed to install {pkg}: {result.stderr[:200]}")
                if pkg == "rumps":
                    print("     (rumps is optional — CLI mode will work without it)")


def setup_portaudio():
    """Check / install portaudio (required by sounddevice on macOS)."""
    if sys.platform != "darwin":
        return
    # Check if brew is available
    if shutil.which("brew"):
        print("\n  Checking for PortAudio (required for audio recording)...")
        result = subprocess.run(["brew", "list", "portaudio"], capture_output=True)
        if result.returncode != 0:
            print("  📦  Installing PortAudio via Homebrew...")
            subprocess.run(["brew", "install", "portaudio"])
            print("  ✅  PortAudio installed")
        else:
            print("  ✅  PortAudio (already installed)")
    else:
        print("\n  ⚠️  Homebrew not found. If audio recording fails, install PortAudio:")
        print("     brew install portaudio")


def configure_api_key():
    """Prompt user for their OpenAI API key."""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
        except Exception:
            pass

    migrated_key, _ = migrate_legacy_api_key(config)
    if migrated_key:
        save_config(config)

    existing = load_stored_api_key()

    env_key = os.environ.get("OPENAI_API_KEY", "")

    if existing:
        masked = existing[:8] + "..." + existing[-4:]
        print(f"\n  Current API key: {masked}")
        resp = input("  Keep this key? (Y/n): ").strip().lower()
        if resp in ("", "y", "yes"):
            return existing

    if env_key:
        masked = env_key[:8] + "..." + env_key[-4:]
        print(f"\n  Found OPENAI_API_KEY in environment: {masked}")
        resp = input("  Use this key? (Y/n): ").strip().lower()
        if resp in ("", "y", "yes"):
            return env_key

    print("\n  VoiceFlow needs an OpenAI API key for Whisper transcription.")
    print("  Get one at: https://platform.openai.com/api-keys\n")
    key = input("  Enter your OpenAI API key: ").strip()
    if not key:
        print(f"  ⚠️  No key provided. You can set it later in {describe_api_key_storage()} or OPENAI_API_KEY")
        return ""
    return key


def configure_hotkey():
    """Let user choose their preferred hotkey."""
    print("\n  Choose your recording hotkey:\n")
    options = [
        ("1", "option (⌥)", "option"),
        ("2", "right option (⌥)", "option_r"),
        ("3", "ctrl (⌃)", "ctrl"),
        ("4", "right cmd (⌘)", "cmd_r"),
        ("5", "caps_lock", "caps_lock"),
        ("6", "fn", "fn"),
    ]
    for num, label, _ in options:
        print(f"    [{num}] {label}")

    choice = input("\n  Select (1-6, default=1 for Option): ").strip()
    idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= 6 else 0
    selected = options[idx]
    print(f"  ✅  Hotkey set to: {selected[1]}")
    return selected[2]


def configure_mode():
    """Choose hold-to-record or toggle mode."""
    print("\n  Recording mode:\n")
    print("    [1] Hold — hold the hotkey while speaking, release to transcribe")
    print("    [2] Toggle — press once to start, press again to stop\n")
    choice = input("  Select (1 or 2, default=1): ").strip()
    if choice == "2":
        print("  ✅  Mode: Toggle")
        return "toggle"
    print("  ✅  Mode: Hold")
    return "hold"


def configure_cleanup():
    """Ask if they want AI text cleanup."""
    print("\n  AI Text Cleanup uses GPT to remove filler words (um, uh, like)")
    print("  and fix grammar. This adds ~1s of latency but produces cleaner text.\n")
    resp = input("  Enable AI cleanup? (Y/n): ").strip().lower()
    enabled = resp in ("", "y", "yes")
    print(f"  ✅  AI Cleanup: {'Enabled' if enabled else 'Disabled'}")
    return enabled


def setup_accessibility():
    """Remind user about macOS accessibility permissions."""
    if sys.platform != "darwin":
        return
    print("""
  ┌─────────────────────────────────────────────────────────┐
  │  ⚠️   macOS Permissions Required                        │
  │                                                         │
  │  VoiceFlow needs these permissions:                     │
  │                                                         │
  │  1. 🎤 Microphone Access                                │
  │     System Settings → Privacy & Security → Microphone   │
  │     → Enable for Terminal / your Python app              │
  │                                                         │
  │  2. ⌨️  Accessibility (for keyboard listening & paste)   │
  │     System Settings → Privacy & Security → Accessibility│
  │     → Enable for Terminal / your Python app              │
  │                                                         │
  │  3. 📋 Automation (for Cmd+V paste simulation)           │
  │     macOS will prompt you on first use — click Allow     │
  │                                                         │
  │  You'll be prompted for these when you first run the app│
  └─────────────────────────────────────────────────────────┘
""")
    input("  Press Enter to continue...")


def create_launch_script():
    """Create a convenient launch script."""
    script_dir = Path(__file__).parent.resolve()
    launch_path = script_dir / "start.sh"
    write_secure_text(launch_path, f"""#!/bin/bash
# VoiceFlow launcher
cd "{script_dir}"
python3 voiceflow.py "$@"
""")
    launch_path.chmod(0o755)
    print(f"  ✅  Launch script created: {launch_path}")
    return launch_path


def create_launchd_plist():
    """Optionally create a LaunchAgent for auto-start on login."""
    if sys.platform != "darwin":
        return

    resp = input("\n  Start VoiceFlow automatically on login? (y/N): ").strip().lower()
    if resp not in ("y", "yes"):
        return

    script_dir = Path(__file__).parent.resolve()
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_path = plist_dir / "com.voiceflow.app.plist"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.voiceflow.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{script_dir / 'voiceflow.py'}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{CONFIG_DIR / 'stdout.log'}</string>
    <key>StandardErrorPath</key>
    <string>{CONFIG_DIR / 'stderr.log'}</string>
</dict>
</plist>"""

    write_secure_text(plist_path, plist_content)
    print(f"  ✅  LaunchAgent created: {plist_path}")
    print("     VoiceFlow will start automatically on next login.")
    print(f"     To remove: launchctl unload {plist_path} && rm {plist_path}")


def main():
    print(BANNER)
    total_steps = 7

    # Step 1: Check Python
    print_step(1, total_steps, "Checking Python version")
    check_python()
    is_mac = check_macos()

    # Step 2: Install packages
    print_step(2, total_steps, "Installing dependencies")
    if is_mac:
        setup_portaudio()
    install_packages()

    # Step 3: API Key
    print_step(3, total_steps, "OpenAI API Key")
    api_key = configure_api_key()

    # Step 4: Hotkey
    print_step(4, total_steps, "Configure Hotkey")
    hotkey = configure_hotkey()

    # Step 5: Mode & cleanup
    print_step(5, total_steps, "Recording Settings")
    mode = configure_mode()
    cleanup = configure_cleanup()

    # Step 6: Save config
    print_step(6, total_steps, "Saving Configuration")
    config = {
        "hotkey": hotkey,
        "mode": mode,
        "whisper_model": "whisper-1",
        "language": "",
        "ai_cleanup": cleanup,
        "cleanup_model": "gpt-4o-mini",
        "auto_paste": True,
        "sound_feedback": True,
        "show_notification": True,
        "notification_preview": False,
        "save_recordings": False,
        "custom_prompt": "",
        "whisper_prompt": "",
        "max_recording_seconds": 300,
    }
    if api_key:
        ok, error = save_api_key(api_key)
        if not ok:
            print(f"  ❌  Could not save API key securely: {error}")
            print("     Set OPENAI_API_KEY and re-run setup, or try again after unlocking your secure store.")
            sys.exit(1)
    save_config(config)
    print(f"  ✅  Config saved to {CONFIG_FILE}")
    if api_key:
        print(f"  ✅  API key saved to {describe_api_key_storage()}")

    # Create dictionary file
    dict_file = CONFIG_DIR / "dictionary.txt"
    if not dict_file.exists():
        save_dictionary(
            "# VoiceFlow Custom Dictionary\n"
            "# Add words/names that Whisper should recognize, one per line.\n"
            "# Example:\n"
            "# Kubernetes\n"
            "# Anthropic\n"
            "# CalTrans\n"
        )
    print(f"  ✅  Dictionary file at {dict_file}")

    launch = create_launch_script()

    # Step 7: Permissions & auto-start
    print_step(7, total_steps, "Permissions & Launch")
    if is_mac:
        setup_accessibility()
        create_launchd_plist()

    # Done!
    print(f"""
{'═'*60}

  ✅  VoiceFlow setup complete!

  To start VoiceFlow:
    python3 voiceflow.py

  Or use the launch script:
    ./start.sh

  Configuration: {CONFIG_FILE}
  Custom Dictionary: {dict_file}
  Logs: {LOG_FILE}

  Quick Start:
    1. Run the app
    2. Hold {hotkey.capitalize()} and speak
    3. Release — your text appears at the cursor!

{'═'*60}
""")


if __name__ == "__main__":
    main()
