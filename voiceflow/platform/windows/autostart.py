"""Windows autostart stub - implemented in Phase 4."""

from ..interfaces import AutostartService


class WindowsAutostart(AutostartService):
    """Windows autostart stub - real implementation in Phase 4."""

    def is_enabled(self) -> bool:
        """Return False as autostart is not yet implemented."""
        return False

    def enable(self) -> None:
        """No-op until Phase 4."""
        pass

    def disable(self) -> None:
        """No-op until Phase 4."""
        pass
