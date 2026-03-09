"""Windows system audio capture using WASAPI loopback."""

import threading

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ..interfaces import SystemAudioService
from voiceflow.core.config import log


class WindowsSystemAudio(SystemAudioService):
    """Capture system audio on Windows using WASAPI loopback.

    WASAPI loopback is built into Windows (Vista+) and captures whatever
    the default output device plays — no virtual audio devices needed.
    """

    def __init__(self):
        self._stream = None
        self._lock = threading.Lock()
        self._loopback_device = None
        self._source_name = ""
        self._detect_loopback()

    def _detect_loopback(self):
        """Find the default output device's loopback interface."""
        if sd is None:
            return
        try:
            # Get the default output device
            default_output = sd.query_devices(kind="output")
            if default_output:
                self._loopback_device = default_output
                self._source_name = f"WASAPI Loopback ({default_output['name']})"
        except Exception as e:
            log(f"Error detecting WASAPI loopback device: {e}")

    def is_available(self) -> bool:
        if sd is None or self._loopback_device is None:
            return False
        # Verify WASAPI loopback actually works by checking for WasapiSettings
        try:
            sd.WasapiSettings  # noqa: B018
            return True
        except AttributeError:
            return False

    def start(self, sample_rate: int, channels: int, dtype: str, callback) -> None:
        with self._lock:
            if self._stream is not None:
                return

            if not self.is_available():
                raise RuntimeError("WASAPI loopback not available")

            try:
                # Use the default output device as a loopback input
                default_output_idx = sd.default.device[1]  # output device index
                self._stream = sd.InputStream(
                    device=default_output_idx,
                    samplerate=sample_rate,
                    channels=channels,
                    dtype=dtype,
                    callback=callback,
                    blocksize=1024,
                    extra_settings=sd.WasapiSettings(exclusive=False),
                )
                self._stream.start()
                log(f"System audio capture started via WASAPI loopback")
            except sd.PortAudioError as e:
                self._stream = None
                raise RuntimeError(f"Failed to start WASAPI loopback: {e}")

    def stop(self) -> None:
        with self._lock:
            if self._stream is None:
                return
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                log(f"Error stopping WASAPI loopback: {e}")
            self._stream = None
            log("System audio capture stopped")

    def get_source_name(self) -> str:
        return self._source_name
