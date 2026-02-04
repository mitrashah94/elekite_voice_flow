"""macOS notification support using osascript."""

import subprocess

from ..interfaces import NotificationService


class MacOSNotifications(NotificationService):
    """macOS implementation of system notifications."""

    def send(self, title: str, message: str) -> None:
        """Send a macOS notification using osascript."""
        # Escape quotes in message to prevent osascript injection
        safe_title = title.replace('"', '\\"')
        safe_message = message.replace('"', '\\"')
        subprocess.run([
            "osascript", "-e",
            f'display notification "{safe_message}" with title "{safe_title}"'
        ], capture_output=True)
