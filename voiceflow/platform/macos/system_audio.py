"""macOS system audio capture using ScreenCaptureKit or BlackHole fallback."""

import threading

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ..interfaces import SystemAudioService
from voiceflow.core.config import log


class MacOSSystemAudio(SystemAudioService):
    """Capture system audio on macOS.

    Strategy:
    1. Try ScreenCaptureKit (macOS 12.3+) for native system audio capture
    2. Fall back to BlackHole virtual audio device if installed
    3. Return unavailable if neither option works
    """

    def __init__(self):
        self._stream = None
        self._lock = threading.Lock()
        self._source_name = ""
        self._method = None  # 'screencapturekit' or 'blackhole'
        self._detect_method()

    def _detect_method(self):
        """Detect the best available system audio capture method."""
        # Try ScreenCaptureKit first
        if self._check_screencapturekit():
            self._method = "screencapturekit"
            self._source_name = "ScreenCaptureKit"
            return

        # Fall back to BlackHole virtual audio device
        blackhole_device = self._find_blackhole_device()
        if blackhole_device is not None:
            self._method = "blackhole"
            self._source_name = f"BlackHole ({blackhole_device['name']})"
            self._blackhole_device_index = blackhole_device["index"]
            return

        self._method = None
        self._source_name = ""

    def _check_screencapturekit(self) -> bool:
        """Check if ScreenCaptureKit is available."""
        try:
            import ScreenCaptureKit  # noqa: F401
            return True
        except ImportError:
            return False

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
        return self._method is not None

    def start(self, sample_rate: int, channels: int, dtype: str, callback) -> None:
        with self._lock:
            if self._stream is not None:
                return

            if self._method == "screencapturekit":
                self._start_screencapturekit(sample_rate, channels, dtype, callback)
            elif self._method == "blackhole":
                self._start_blackhole(sample_rate, channels, dtype, callback)
            else:
                raise RuntimeError("System audio capture not available on this system")

    def _start_screencapturekit(self, sample_rate, channels, dtype, callback):
        """Start capture using ScreenCaptureKit via a sounddevice-compatible wrapper."""
        try:
            import ScreenCaptureKit as SCK
            import CoreMedia
            import numpy as np

            # Get shareable content to find audio sources
            content = SCK.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
                True, False, None
            )

            # Configure audio-only capture
            config = SCK.SCStreamConfiguration.alloc().init()
            config.setCapturesAudio_(True)
            config.setExcludesCurrentProcessAudio_(True)
            config.setSampleRate_(sample_rate)
            config.setChannelCount_(channels)

            # Create a filter for all audio
            filter_ = SCK.SCContentFilter.alloc().initWithDisplay_excludingApplications_exceptingWindows_(
                None, [], []
            )

            # Delegate that converts SCK audio to sounddevice callback format
            class AudioDelegate:
                def __init__(self, cb, sr, ch):
                    self._callback = cb
                    self._sample_rate = sr
                    self._channels = ch

                def stream_didOutputSampleBuffer_ofType_(self, stream, sample_buffer, output_type):
                    if output_type != SCK.SCStreamOutputType.audio:
                        return
                    try:
                        # Extract audio data from CMSampleBuffer
                        block_buffer = CoreMedia.CMSampleBufferGetDataBuffer(sample_buffer)
                        if block_buffer is None:
                            return
                        data_length = CoreMedia.CMBlockBufferGetDataLength(block_buffer)
                        data = CoreMedia.CMBlockBufferCopyDataBytes(block_buffer, 0, data_length, None)
                        audio_array = np.frombuffer(data, dtype=np.int16).reshape(-1, self._channels)
                        self._callback(audio_array, len(audio_array), None, None)
                    except Exception as e:
                        log(f"ScreenCaptureKit audio callback error: {e}")

            self._delegate = AudioDelegate(callback, sample_rate, channels)
            self._sck_stream = SCK.SCStream.alloc().initWithFilter_configuration_delegate_(
                filter_, config, self._delegate
            )
            self._sck_stream.startCaptureWithCompletionHandler_(None)
            self._stream = self._sck_stream
            log("System audio capture started via ScreenCaptureKit")

        except Exception as e:
            log(f"ScreenCaptureKit failed, trying BlackHole fallback: {e}")
            # Try BlackHole fallback
            blackhole = self._find_blackhole_device()
            if blackhole:
                self._method = "blackhole"
                self._blackhole_device_index = blackhole["index"]
                self._source_name = f"BlackHole ({blackhole['name']})"
                self._start_blackhole(sample_rate, channels, dtype, callback)
            else:
                raise RuntimeError(f"System audio capture failed: {e}")

    def _start_blackhole(self, sample_rate, channels, dtype, callback):
        """Start capture using BlackHole virtual audio device."""
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

            if self._method == "screencapturekit":
                try:
                    self._stream.stopCaptureWithCompletionHandler_(None)
                except Exception as e:
                    log(f"Error stopping ScreenCaptureKit: {e}")
            else:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    log(f"Error stopping BlackHole stream: {e}")

            self._stream = None
            log("System audio capture stopped")

    def get_source_name(self) -> str:
        return self._source_name
