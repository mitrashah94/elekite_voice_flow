"""Windows clipboard operations using pyperclip and pynput."""

import time

import pyperclip
from pynput.keyboard import Controller, Key

from ..interfaces import ClipboardService


class WindowsClipboard(ClipboardService):
    """Windows implementation of clipboard operations."""

    def __init__(self):
        self._keyboard = Controller()

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard using pyperclip."""
        pyperclip.copy(text)

    def paste(self) -> None:
        """Simulate Ctrl+V keystroke using pynput."""
        # Small delay so clipboard is ready
        time.sleep(0.05)

        # Use context manager for clean press/release
        with self._keyboard.pressed(Key.ctrl):
            self._keyboard.press('v')
            self._keyboard.release('v')
