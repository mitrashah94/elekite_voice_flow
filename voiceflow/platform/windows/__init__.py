"""Windows platform backend implementation."""

from .clipboard import WindowsClipboard
from .notifications import WindowsNotifications
from .sounds import WindowsSounds
from .tray import WindowsTray
from .autostart import WindowsAutostart
from .system_audio import WindowsSystemAudio


class WindowsBackend:
    """Composite backend holding all Windows platform services.

    Note: Hotkey functionality is NOT included here. Hotkeys are handled
    by pynput in voiceflow/core/app.py, which is already cross-platform.
    pynput abstracts Windows/macOS/Linux hotkey differences internally,
    so no platform-specific HotkeyService is needed.
    """

    def __init__(self):
        self.clipboard = WindowsClipboard()
        self.notifications = WindowsNotifications()
        self.sounds = WindowsSounds()
        self.tray = WindowsTray()
        self.autostart = WindowsAutostart()
        self.system_audio = WindowsSystemAudio()


__all__ = ["WindowsBackend"]
