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


class SystemAudioService(ABC):
    """Abstract interface for capturing system/loopback audio.

    Used by meeting transcription to capture what plays through
    speakers/headphones (e.g., other participants in a Zoom call).
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if system audio capture is supported on this platform."""
        pass

    @abstractmethod
    def start(self, sample_rate: int, channels: int, dtype: str, callback) -> None:
        """Start capturing system audio.

        Args:
            sample_rate: Audio sample rate in Hz (e.g., 16000)
            channels: Number of audio channels (e.g., 1 for mono)
            dtype: Audio data type (e.g., 'int16')
            callback: Function called with (indata, frames, time_info, status)
                      Same signature as sounddevice.InputStream callback.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing system audio."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return a human-readable name of the audio source being captured."""
        pass
