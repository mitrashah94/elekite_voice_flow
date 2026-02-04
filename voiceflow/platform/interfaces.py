"""Abstract base classes defining platform-specific service interfaces."""

from abc import ABC, abstractmethod


class ClipboardService(ABC):
    """Abstract interface for clipboard operations."""

    @abstractmethod
    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        pass

    @abstractmethod
    def paste(self) -> None:
        """Simulate paste keystroke (Cmd+V / Ctrl+V)."""
        pass


class NotificationService(ABC):
    """Abstract interface for system notifications."""

    @abstractmethod
    def send(self, title: str, message: str) -> None:
        """Send a system notification."""
        pass


class SoundService(ABC):
    """Abstract interface for playing system sounds."""

    @abstractmethod
    def play(self, sound_name: str) -> None:
        """Play a named sound (start, stop, error)."""
        pass


class TrayService(ABC):
    """Abstract interface for system tray/menu bar functionality."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if tray functionality is available."""
        pass

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Set tray icon title/text."""
        pass

    @abstractmethod
    def get_app_class(self):
        """Return the tray app base class for subclassing."""
        pass


class AutostartService(ABC):
    """Abstract interface for launch-on-login functionality."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if autostart is currently enabled."""
        pass

    @abstractmethod
    def enable(self) -> None:
        """Enable launch on login."""
        pass

    @abstractmethod
    def disable(self) -> None:
        """Disable launch on login."""
        pass
