"""Windows system tray support using pystray."""

import os
import subprocess
import sys

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

    def __init__(self, config: dict, on_start_recording, on_stop_recording,
                 on_toggle_meeting=None, is_fallback_hotkey: bool = False):
        """Initialize the Windows tray application.

        Args:
            config: Application configuration dictionary
            on_start_recording: Callback for starting recording
            on_stop_recording: Callback for stopping recording
            on_toggle_meeting: Callback for toggling meeting mode
            is_fallback_hotkey: Whether using fallback hotkey (for display)
        """
        self.config = config
        self._on_start_recording = on_start_recording
        self._on_stop_recording = on_stop_recording
        self._on_toggle_meeting = on_toggle_meeting
        self._is_fallback_hotkey = is_fallback_hotkey
        self._state = "idle"
        self._meeting_state = "idle"  # idle, active, processing
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
        """Open the settings GUI."""
        # Find settings_gui.py - it's at project root
        # This file is at voiceflow/platform/windows/tray.py
        # Go up 3 levels to reach project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        settings_script = os.path.join(project_root, "settings_gui.py")

        if os.path.exists(settings_script):
            # Use pythonw on Windows to avoid console window
            python_exe = sys.executable
            if sys.platform == "win32":
                pythonw = python_exe.replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw):
                    python_exe = pythonw
            subprocess.Popen([python_exe, settings_script])
        else:
            # Fallback: open config file directly
            from voiceflow.core.config import CONFIG_FILE
            os.startfile(str(CONFIG_FILE))

    def _view_log(self, icon, item):
        """Open log file in default viewer."""
        from voiceflow.core.config import LOG_FILE

        log_path = str(LOG_FILE)
        if os.path.exists(log_path):
            os.startfile(log_path)

    def _toggle_meeting(self, icon, item):
        """Toggle meeting transcription mode."""
        if self._on_toggle_meeting:
            self._on_toggle_meeting()

    def _get_meeting_text(self) -> str:
        """Get dynamic meeting menu item text."""
        if self._meeting_state == "active":
            return "Stop Meeting"
        elif self._meeting_state == "processing":
            return "Processing meeting..."
        return "Start Meeting..."

    def set_meeting_state(self, state: str, has_system_audio: bool = False):
        """Update meeting state and refresh menu.

        Args:
            state: One of "idle", "active", "processing"
            has_system_audio: Whether system audio is being captured
        """
        self._meeting_state = state
        if self._icon is not None:
            self._icon.update_menu()

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
            MenuItem(
                lambda text: self._get_meeting_text(),
                self._toggle_meeting,
                enabled=lambda item: self._meeting_state != "processing",
            ),
            Menu.SEPARATOR,
            MenuItem("Settings...", self._open_settings),
            MenuItem("View Log", self._view_log),
            Menu.SEPARATOR,
            MenuItem("Quit VoiceFlow", self._quit),
        )

    def set_state(self, state: str) -> None:
        """Update application state and icon.

        Args:
            state: One of "idle", "recording", or "processing"
        """
        self._state = state

        if self._icon is not None:
            # Update icon image
            self._icon.icon = self._icons.get(state, self._icons["idle"])

            # Update tooltip title
            title_states = {
                "idle": "VoiceFlow - Ready",
                "recording": "VoiceFlow - Recording...",
                "processing": "VoiceFlow - Transcribing...",
            }
            self._icon.title = title_states.get(state, "VoiceFlow - Ready")

            # Refresh menu to update dynamic status text
            self._icon.update_menu()

    def _setup(self, icon):
        """Setup callback for pystray - called after icon is ready.

        This runs in a separate thread managed by pystray.
        """
        icon.visible = True

    def run(self):
        """Start the tray application.

        Note: This method is blocking on Windows.
        """
        if not PYSTRAY_AVAILABLE:
            return

        self._icon = pystray.Icon(
            name="VoiceFlow",
            icon=self._icons["idle"],
            title="VoiceFlow - Ready",
            menu=self._create_menu()
        )
        self._icon.run(setup=self._setup)

    def stop(self):
        """Stop the tray application."""
        if self._icon is not None:
            self._icon.stop()
            self._icon = None
