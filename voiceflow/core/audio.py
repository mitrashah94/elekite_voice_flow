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

from .config import SAMPLE_RATE, CHANNELS, ensure_private_permissions, log


class AudioRecorder:
    """Records audio from the default input device using sounddevice."""

    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list = []
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()
        self._stop_due_to_error = False  # Track mid-recording device errors

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        """Start recording. Handle device errors gracefully."""
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stop_due_to_error = False  # Reset error flag
            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16",
                    callback=self._callback,
                    blocksize=1024,
                )
                self._stream.start()
                log("Recording started")
            except sd.PortAudioError as e:
                log(f"Failed to start recording: {e}")
                self._recording = False
                self._stream = None
                raise  # Let caller handle the error

    def _callback(self, indata, frames, time_info, status):
        """Callback for audio stream. Handle mid-recording disconnect."""
        if status:
            log(f"Audio stream status: {status}")
            # Check for device errors that indicate disconnect
            # status flags: input_overflow, input_underflow, output_overflow,
            # output_underflow, priming_output - these are warnings
            # But if we detect a device error, we should stop gracefully
            status_str = str(status).lower()
            if "error" in status_str or "device" in status_str:
                log(f"Audio device error mid-recording: {status}")
                self._stop_due_to_error = True
                return  # Stop accepting new data

        # Normal recording continues
        if not self._stop_due_to_error:
            self._frames.append(indata.copy())

    def stop(self) -> str | None:
        """Stop recording and return the path to a WAV file, or None."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False

            # Handle mid-recording device disconnect gracefully
            if self._stop_due_to_error:
                log("Recording stopped due to device error - processing captured audio")

            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except sd.PortAudioError as e:
                    # Device disconnected - continue to process whatever we have
                    log(f"Audio device error during stop: {e}")
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
        ensure_private_permissions(tmp.name)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        log(f"Saved recording to {tmp.name}")
        return tmp.name
