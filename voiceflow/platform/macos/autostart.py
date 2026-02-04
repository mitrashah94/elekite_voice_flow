"""macOS autostart support using LaunchAgents."""

import subprocess
from pathlib import Path

from ..interfaces import AutostartService


class MacOSAutostart(AutostartService):
    """macOS implementation of launch-on-login using LaunchAgents."""

    PLIST_NAME = "com.voiceflow.app.plist"
    LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"

    def _get_plist_path(self) -> Path:
        """Get the path to the LaunchAgent plist file."""
        return self.LAUNCH_AGENTS_DIR / self.PLIST_NAME

    def is_enabled(self) -> bool:
        """Check if the LaunchAgent plist exists."""
        return self._get_plist_path().exists()

    def enable(self) -> None:
        """Enable launch on login.

        Note: Full implementation deferred - current setup.py
        handles this during the setup wizard.
        """
        pass

    def disable(self) -> None:
        """Disable launch on login by unloading and removing the plist."""
        plist_path = self._get_plist_path()
        if plist_path.exists():
            # Unload first
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                capture_output=True
            )
            plist_path.unlink()
