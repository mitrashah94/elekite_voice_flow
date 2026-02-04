"""Windows system tray support using pystray."""

import os

from ..interfaces import TrayService

# Conditional import for optional dependency
try:
    import pystray
    from pystray import Menu, MenuItem
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    pystray = None
    Menu = None
    MenuItem = None
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


class WindowsTrayApp:
    """Windows system tray application for VoiceFlow."""

    def __init__(self, config: dict, on_start_recording, on_stop_recording, is_fallback_hotkey: bool = False):
        """Initialize the Windows tray application.

        Args:
            config: Application configuration dictionary
            on_start_recording: Callback for starting recording
            on_stop_recording: Callback for stopping recording
            is_fallback_hotkey: Whether using fallback hotkey (for display)
        """
        self.config = config
        self._on_start_recording = on_start_recording
        self._on_stop_recording = on_stop_recording
        self._is_fallback_hotkey = is_fallback_hotkey
        self._state = "idle"
        self._icon = None

        # Pre-generate icons for each state
        self._icons = {
            "idle": create_idle_icon(),
            "recording": create_recording_icon(),
            "processing": create_processing_icon(),
        }

    def _get_status_text(self) -> str:
        """Get human-readable status text for current state."""
        states = {
            "idle": "Ready",
            "recording": "Recording...",
            "processing": "Transcribing...",
        }
        return states.get(self._state, "Ready")

    def _show_status(self, icon, item):
        """Left-click handler - show current status via notification balloon."""
        icon.notify(self._get_status_text(), "VoiceFlow")

    def _open_settings(self, icon, item):
        """Open settings/config file in default editor."""
        from voiceflow.core.config import CONFIG_FILE, CONFIG_DIR

        # Ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        config_path = str(CONFIG_FILE)
        if os.path.exists(config_path):
            os.startfile(config_path)
        else:
            # Create a default config file first
            from voiceflow.core.config import save_config
            save_config(self.config)
            os.startfile(config_path)

    def _view_log(self, icon, item):
        """Open log file in default viewer."""
        from voiceflow.core.config import LOG_FILE

        log_path = str(LOG_FILE)
        if os.path.exists(log_path):
            os.startfile(log_path)

    def _quit(self, icon, item):
        """Quit the application."""
        icon.stop()

    def _create_menu(self):
        """Create the right-click context menu.

        Menu structure:
        - (hidden default) Status -> left-click shows notification
        - Status: [current state] (disabled, for display)
        - ---
        - Settings...
        - View Log
        - ---
        - Quit VoiceFlow
        """
        if not PYSTRAY_AVAILABLE:
            return None

        return Menu(
            # Hidden default item for left-click status display
            MenuItem("Status", self._show_status, default=True, visible=False),
            # Visible status line (disabled, for display only)
            MenuItem(
                lambda text: f"Status: {self._get_status_text()}",
                None,
                enabled=False
            ),
            Menu.SEPARATOR,
            MenuItem("Settings...", self._open_settings),
            MenuItem("View Log", self._view_log),
            Menu.SEPARATOR,
            MenuItem("Quit VoiceFlow", self._quit),
        )
