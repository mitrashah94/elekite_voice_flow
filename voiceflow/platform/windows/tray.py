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


# Icon generation utilities

def _create_icon(color: str, size: int = 64):
    """Create a circular icon with the specified color.

    Args:
        color: Color name (e.g., 'gray', 'red', 'orange')
        size: Icon size in pixels (default 64 for high-DPI support)

    Returns:
        PIL.Image object or None if pystray/Pillow not available
    """
    if not PYSTRAY_AVAILABLE:
        return None

    # Create RGBA image with transparent background
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw filled circle with 4-pixel padding from edges
    padding = 4
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=color
    )

    return image


def create_idle_icon():
    """Create gray circle icon for idle state."""
    return _create_icon('gray')


def create_recording_icon():
    """Create red circle icon for recording state."""
    return _create_icon('red')


def create_processing_icon():
    """Create orange circle icon for processing state."""
    return _create_icon('orange')
