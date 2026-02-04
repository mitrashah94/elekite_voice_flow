"""Platform abstraction layer - auto-selects correct backend."""

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
    # Windows backend will be added in Phase 2
    raise ImportError("Windows backend not yet implemented")
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
