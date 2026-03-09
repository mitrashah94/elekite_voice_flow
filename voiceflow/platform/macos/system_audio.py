"""macOS system audio capture using BlackHole virtual audio device."""

import threading

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ..interfaces import SystemAudioService
from voiceflow.core.config import log


class MacOSSystemAudio(SystemAudioService):
    """Capture system audio on macOS via BlackHole virtual audio device.

    Requires BlackHole (https://existential.audio/blackhole/) to be installed.
    Returns unavailable if BlackHole is not detected.
    """

    def __init__(self):
        self._stream = None
        self._lock = threading.Lock()
        self._source_name = ""
        self._blackhole_device_index = None
        self._detect_method()

    def _detect_method(self):
        """Detect if BlackHole virtual audio device is available."""
        blackhole_device = self._find_blackhole_device()
        if blackhole_device is not None:
            self._source_name = f"BlackHole ({blackhole_device['name']})"
            self._blackhole_device_index = blackhole_device["index"]

    def _find_blackhole_device(self) -> dict | None:
        """Find a BlackHole virtual audio device."""
        if sd is None:
            return None
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                name = dev.get("name", "").lower()
                if "blackhole" in name and dev.get("max_input_channels", 0) > 0:
                    return {"index": i, "name": dev["name"]}
        except Exception as e:
            log(f"Error querying audio devices: {e}")
        return None

    def is_available(self) -> bool:
        return self._blackhole_device_index is not None

    def start(self, sample_rate: int, channels: int, dtype: str, callback) -> None:
        with self._lock:
            if self._stream is not None:
                return

            if self._blackhole_device_index is None:
                raise RuntimeError("System audio capture not available on this system")

            if sd is None:
                raise RuntimeError("sounddevice not available")

            try:
                self._stream = sd.InputStream(
                    device=self._blackhole_device_index,
                    samplerate=sample_rate,
                    channels=channels,
                    dtype=dtype,
                    callback=callback,
                    blocksize=1024,
                )
                self._stream.start()
                log(f"System audio capture started via BlackHole (device {self._blackhole_device_index})")
            except sd.PortAudioError as e:
                self._stream = None
                raise RuntimeError(f"Failed to open BlackHole device: {e}")

    def stop(self) -> None:
        with self._lock:
            if self._stream is None:
                return
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                log(f"Error stopping BlackHole stream: {e}")
            self._stream = None
            log("System audio capture stopped")

    def get_source_name(self) -> str:
        return self._source_name
