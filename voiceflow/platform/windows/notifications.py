"""Windows notification stub - implemented in Phase 4."""

from ..interfaces import NotificationService


class WindowsNotifications(NotificationService):
    """Windows notification stub - real implementation in Phase 4."""

    def send(self, title: str, message: str) -> None:
        """Log notification instead of displaying (stub)."""
        from voiceflow.core.config import log

        log(f"[Notification stub] {title}: {message}")
