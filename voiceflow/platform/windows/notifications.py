"""Windows notification implementation using winotify."""

from ..interfaces import NotificationService

try:
    from winotify import Notification
    WINOTIFY_AVAILABLE = True
except ImportError:
    Notification = None
    WINOTIFY_AVAILABLE = False


class WindowsNotifications(NotificationService):
    """Windows implementation of notifications using winotify."""

    # App ID shown in Windows action center
    APP_ID = "VoiceFlow"

    def send(self, title: str, message: str) -> None:
        """Display a Windows toast notification.

        Args:
            title: Notification title (e.g., "VoiceFlow")
            message: Notification body (e.g., transcription preview)
        """
        if not WINOTIFY_AVAILABLE:
            # Fallback to logging if winotify not installed
            from voiceflow.core.config import log
            log(f"Notification displayed: {title}")
            return

        try:
            toast = Notification(
                app_id=self.APP_ID,
                title=title,
                msg=message,
                icon=""  # Skip icon - notifications work without it
            )
            toast.show()
        except Exception as e:
            # Don't crash the app if notification fails
            from voiceflow.core.config import log
            log(f"Notification error: {e}")
