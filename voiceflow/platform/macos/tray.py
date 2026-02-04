"""macOS menu bar tray support using rumps."""

from ..interfaces import TrayService

# Preserve lazy import pattern for optional dependency
try:
    import rumps
    RUMPS_AVAILABLE = True
except ImportError:
    rumps = None
    RUMPS_AVAILABLE = False


class MacOSTray(TrayService):
    """macOS implementation of system tray (menu bar) functionality."""

    def is_available(self) -> bool:
        """Check if rumps is available for menu bar functionality."""
        return RUMPS_AVAILABLE

    def set_title(self, title: str) -> None:
        """Set tray icon title.

        Note: This is a placeholder - actual title setting happens
        on the rumps.App instance, not through this service.
        The tray service provides access to rumps, not direct control.
        """
        pass

    def get_app_class(self):
        """Return the rumps.App class for subclassing, or None if unavailable."""
        if not RUMPS_AVAILABLE:
            return None
        return rumps.App
