"""macOS sound playback using afplay."""

import os
import subprocess

from ..interfaces import SoundService


class MacOSSounds(SoundService):
    """macOS implementation of sound playback."""

    SOUNDS = {
        "start": "/System/Library/Sounds/Pop.aiff",
        "stop": "/System/Library/Sounds/Purr.aiff",
        "error": "/System/Library/Sounds/Basso.aiff",
    }

    def play(self, sound_name: str) -> None:
        """Play a named system sound using afplay."""
        path = self.SOUNDS.get(sound_name)
        if path and os.path.exists(path):
            subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
