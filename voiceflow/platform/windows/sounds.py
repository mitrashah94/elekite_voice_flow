"""Windows sound playback using winsound and bundled WAV files."""

import sys
from pathlib import Path

from ..interfaces import SoundService

# winsound is Windows-only stdlib module
if sys.platform == "win32":
    import winsound
else:
    winsound = None  # Module won't work on non-Windows


class WindowsSounds(SoundService):
    """Windows implementation of sound playback using winsound."""

    def __init__(self):
        # Sound files bundled with the app
        self._sound_dir = Path(__file__).parent.parent.parent / "sounds"
        self._sounds = {
            "start": self._sound_dir / "start.wav",
            "stop": self._sound_dir / "stop.wav",
            "error": self._sound_dir / "error.wav",
        }

    def play(self, sound_name: str) -> None:
        """Play a named sound asynchronously."""
        if winsound is None:
            # Not on Windows, silently ignore
            return

        sound_file = self._sounds.get(sound_name)
        if sound_file and sound_file.exists():
            winsound.PlaySound(
                str(sound_file),
                winsound.SND_FILENAME | winsound.SND_ASYNC
            )
