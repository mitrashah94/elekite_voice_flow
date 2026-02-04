"""Windows tray stub - implemented in Phase 3."""

from ..interfaces import TrayService


class WindowsTray(TrayService):
    """Windows tray stub - real implementation in Phase 3."""

    def is_available(self) -> bool:
        """Return False as tray is not yet implemented."""
        return False

    def set_title(self, title: str) -> None:
        """No-op until Phase 3."""
        pass

    def get_app_class(self):
        """Return None as tray app is not yet implemented."""
        return None
