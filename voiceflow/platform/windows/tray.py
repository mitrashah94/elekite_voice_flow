"""Windows system tray support using pystray."""

from ..interfaces import TrayService

# Conditional import for optional dependency
try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None
    PYSTRAY_AVAILABLE = False


class WindowsTray(TrayService):
    """Windows implementation of system tray functionality."""

    def is_available(self) -> bool:
        """Check if pystray is available for tray functionality."""
        return PYSTRAY_AVAILABLE

    def set_title(self, title: str) -> None:
        """Set tray icon title.

        Note: This is a placeholder - actual title setting happens
        on the pystray.Icon instance, not through this service.
        The tray service provides access to pystray, not direct control.
        """
        pass

    def get_app_class(self):
        """Return the pystray.Icon class for instantiation, or None if unavailable."""
        if not PYSTRAY_AVAILABLE:
            return None
        return pystray.Icon
