"""VoiceFlow audio recording module."""

import wave
import tempfile
import threading

# Lazy imports for optional dependencies
try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None
    np = None

from .config import SAMPLE_RATE, CHANNELS, log


class AudioRecorder:
    """Records audio from the default input device using sounddevice."""

    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list = []
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._callback,
                blocksize=1024,
            )
            self._stream.start()
            log("Recording started")

    def _callback(self, indata, frames, time_info, status):
        if status:
            log(f"Audio status: {status}")
        self._frames.append(indata.copy())

    def stop(self) -> str | None:
        """Stop recording and return the path to a WAV file, or None."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        if not self._frames:
            log("No audio frames captured")
            return None

        audio_data = np.concatenate(self._frames, axis=0)
        duration = len(audio_data) / self.sample_rate
        log(f"Recording stopped — {duration:.1f}s of audio")

        if duration < 0.3:
            log("Recording too short, discarding")
            return None

        # Write to a temp WAV file
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        log(f"Saved recording to {tmp.name}")
        return tmp.name
