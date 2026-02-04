"""macOS platform backend implementation."""

from .clipboard import MacOSClipboard
from .notifications import MacOSNotifications
from .sounds import MacOSSounds
from .tray import MacOSTray
from .autostart import MacOSAutostart


class MacOSBackend:
    """Composite backend holding all macOS platform services."""

    def __init__(self):
        self.clipboard = MacOSClipboard()
        self.notifications = MacOSNotifications()
        self.sounds = MacOSSounds()
        self.tray = MacOSTray()
        self.autostart = MacOSAutostart()
