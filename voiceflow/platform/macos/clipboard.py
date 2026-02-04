"""macOS clipboard operations using pbcopy and osascript."""

import subprocess
import time

from ..interfaces import ClipboardService


class MacOSClipboard(ClipboardService):
    """macOS implementation of clipboard operations."""

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard using pbcopy."""
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))

    def paste(self) -> None:
        """Simulate Cmd+V keystroke using osascript."""
        # Small delay so clipboard is ready
        time.sleep(0.05)
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "v" using command down'
        ], capture_output=True)
