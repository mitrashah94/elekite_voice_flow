"""Platform abstraction layer - auto-selects correct backend.

Note on hotkeys: Hotkey handling is NOT part of this abstraction.
HotkeyManager in voiceflow/core/app.py uses pynput directly, which
provides cross-platform hotkey support out of the box. No need to
reinvent this wheel.
"""

import sys

from .interfaces import (
    ClipboardService,
    NotificationService,
    SoundService,
    TrayService,
    AutostartService,
)

# Platform detection at import time
if sys.platform == "darwin":
    from .macos import MacOSBackend
    _backend_class = MacOSBackend
elif sys.platform == "win32":
    from .windows import WindowsBackend
    _backend_class = WindowsBackend
else:
    raise ImportError(f"Unsupported platform: {sys.platform}")

# Instantiate singleton at import time
# This triggers ABC validation immediately - missing methods = TypeError HERE
backend = _backend_class()

# Export the singleton and its services for convenient access
clipboard: ClipboardService = backend.clipboard
notifications: NotificationService = backend.notifications
sounds: SoundService = backend.sounds
tray: TrayService = backend.tray
autostart: AutostartService = backend.autostart

__all__ = [
    "backend",
    "clipboard",
    "notifications",
    "sounds",
    "tray",
    "autostart",
    # Re-export interfaces for type hints
    "ClipboardService",
    "NotificationService",
    "SoundService",
    "TrayService",
    "AutostartService",
]
