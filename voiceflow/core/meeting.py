"""Meeting transcription — dual-stream recording, chunked transcription, and session management."""

import os
import wave
import time
import shutil
import tempfile
import threading
from collections import deque
from pathlib import Path
from datetime import datetime

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None
    np = None

from .config import SAMPLE_RATE, CHANNELS, MEETING_DIR, ensure_private_dir, log, write_secure_text
from .transcriber import Transcriber, TranscriptionError

from voiceflow.platform import system_audio, notifications, sounds


# ---------------------------------------------------------------------------
# Meeting Recorder — dual-stream capture with time-based chunking
# ---------------------------------------------------------------------------

class MeetingRecorder:
    """Records mic + system audio simultaneously, flushing to WAV chunks on disk.

    Chunks are written every `chunk_seconds` with `overlap_seconds` of overlap
    to prevent words being cut at boundaries.
    """

    def __init__(self, config: dict):
        self.config = config
        self.chunk_seconds = config.get("meeting_chunk_seconds", 240)
        self.overlap_seconds = config.get("meeting_overlap_seconds", 10)
        self.mix_audio = config.get("meeting_mix_audio", False)
        self.sample_rate = SAMPLE_RATE
        self.channels = CHANNELS

        self._mic_frames: deque = deque()
        self._sys_frames: deque = deque()
        self._mic_stream = None
        self._recording = False
        self._lock = threading.Lock()
        self._chunk_timer = None
        self._chunk_dir = None
        self._chunk_index = 0
        self._chunks: list[dict] = []  # list of {mic: path, system: path, mixed: path, timestamp: float}
        self._start_time = 0.0
        self._final_duration = 0.0
        self._has_system_audio = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def elapsed_seconds(self) -> float:
        if not self._recording:
            return self._final_duration
        return time.monotonic() - self._start_time

    def start(self) -> bool:
        """Start dual-stream recording. Returns True if system audio is available."""
        with self._lock:
            if self._recording:
                return self._has_system_audio

            # Create temp directory for chunks
            self._chunk_dir = tempfile.mkdtemp(prefix="voiceflow_meeting_")
            self._chunk_index = 0
            self._chunks = []
            self._mic_frames = deque()
            self._sys_frames = deque()
            self._recording = True
            self._start_time = time.monotonic()

            # Start mic stream
            try:
                self._mic_stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16",
                    callback=self._mic_callback,
                    blocksize=1024,
                )
                self._mic_stream.start()
                log("Meeting: mic recording started")
            except sd.PortAudioError as e:
                log(f"Meeting: failed to start mic: {e}")
                self._recording = False
                raise

            # Start system audio stream (optional)
            self._has_system_audio = False
            if system_audio.is_available():
                try:
                    system_audio.start(
                        sample_rate=self.sample_rate,
                        channels=self.channels,
                        dtype="int16",
                        callback=self._sys_callback,
                    )
                    self._has_system_audio = True
                    log(f"Meeting: system audio started ({system_audio.get_source_name()})")
                except Exception as e:
                    log(f"Meeting: system audio unavailable, mic-only mode: {e}")

            # Start chunk timer
            self._schedule_chunk_flush()
            return self._has_system_audio

    def _mic_callback(self, indata, frames, time_info, status):
        if status:
            log(f"Meeting mic status: {status}")
        if self._recording:
            self._mic_frames.append(indata.copy())

    def _sys_callback(self, indata, frames, time_info, status):
        if status:
            log(f"Meeting system audio status: {status}")
        if self._recording:
            self._sys_frames.append(indata.copy())

    def _schedule_chunk_flush(self):
        """Schedule the next chunk flush."""
        if not self._recording:
            return
        self._chunk_timer = threading.Timer(self.chunk_seconds, self._flush_chunk)
        self._chunk_timer.daemon = True
        self._chunk_timer.start()

    def _flush_chunk(self):
        """Flush current audio buffers to WAV files and start next chunk."""
        if not self._recording:
            return

        with self._lock:
            self._chunk_index += 1
            chunk_info = {"timestamp": time.monotonic() - self._start_time}

            # Calculate overlap in frames.
            # Slicing with [-overlap_frames:] operates on axis=0 (frames),
            # which works regardless of channel count since arrays are shaped
            # (total_frames, channels) after np.concatenate(axis=0).
            overlap_frames = int(self.overlap_seconds * self.sample_rate)

            # Drain mic deque (thread-safe: callbacks only append).
            # Note: a callback could append one frame between list() and clear(),
            # causing ~64ms of audio loss per boundary. Acceptable for meeting use.
            mic_frames = list(self._mic_frames)
            self._mic_frames.clear()
            if mic_frames:
                mic_data = np.concatenate(mic_frames, axis=0)
                chunk_info["mic"] = self._write_wav(
                    mic_data, f"chunk_{self._chunk_index:03d}_mic.wav"
                )
                # Keep overlap for next chunk
                if len(mic_data) > overlap_frames:
                    self._mic_frames.append(mic_data[-overlap_frames:])
            else:
                chunk_info["mic"] = None

            # Drain system audio deque
            sys_frames = list(self._sys_frames)
            self._sys_frames.clear()
            if self._has_system_audio and sys_frames:
                sys_data = np.concatenate(sys_frames, axis=0)
                chunk_info["system"] = self._write_wav(
                    sys_data, f"chunk_{self._chunk_index:03d}_system.wav"
                )
                if len(sys_data) > overlap_frames:
                    self._sys_frames.append(sys_data[-overlap_frames:])
            else:
                chunk_info["system"] = None

            # Mixed mode: combine mic + system
            if self.mix_audio and chunk_info.get("mic") and chunk_info.get("system"):
                chunk_info["mixed"] = self._mix_and_write(
                    chunk_info["mic"], chunk_info["system"],
                    f"chunk_{self._chunk_index:03d}_mixed.wav"
                )
            else:
                chunk_info["mixed"] = None

            self._chunks.append(chunk_info)
            log(f"Meeting: flushed chunk {self._chunk_index} at {chunk_info['timestamp']:.0f}s")

        # Schedule next flush
        self._schedule_chunk_flush()

    def stop(self) -> list[dict]:
        """Stop recording and flush remaining audio. Returns list of chunk info dicts."""
        # Single lock section: stop recording flag, cancel timer, stop streams
        with self._lock:
            if not self._recording:
                return self._chunks
            self._final_duration = time.monotonic() - self._start_time
            self._recording = False

            # Cancel timer
            if self._chunk_timer:
                self._chunk_timer.cancel()
                self._chunk_timer = None

            # Stop streams (under lock so no new callbacks fire after this)
            if self._mic_stream:
                try:
                    self._mic_stream.stop()
                    self._mic_stream.close()
                except Exception as e:
                    log(f"Meeting: error stopping mic: {e}")
                self._mic_stream = None

            if self._has_system_audio:
                try:
                    system_audio.stop()
                except Exception as e:
                    log(f"Meeting: error stopping system audio: {e}")

        # Flush remaining audio as final chunk (safe: streams are stopped)
        self._chunk_index += 1
        chunk_info = {"timestamp": time.monotonic() - self._start_time}

        mic_frames = list(self._mic_frames)
        self._mic_frames.clear()
        if mic_frames:
            mic_data = np.concatenate(mic_frames, axis=0)
            if len(mic_data) / self.sample_rate >= 0.3:  # min duration
                chunk_info["mic"] = self._write_wav(
                    mic_data, f"chunk_{self._chunk_index:03d}_mic.wav"
                )
            else:
                chunk_info["mic"] = None
        else:
            chunk_info["mic"] = None

        sys_frames = list(self._sys_frames)
        self._sys_frames.clear()
        if self._has_system_audio and sys_frames:
            sys_data = np.concatenate(sys_frames, axis=0)
            if len(sys_data) / self.sample_rate >= 0.3:
                chunk_info["system"] = self._write_wav(
                    sys_data, f"chunk_{self._chunk_index:03d}_system.wav"
                )
            else:
                chunk_info["system"] = None
        else:
            chunk_info["system"] = None

        if self.mix_audio and chunk_info.get("mic") and chunk_info.get("system"):
            chunk_info["mixed"] = self._mix_and_write(
                chunk_info["mic"], chunk_info["system"],
                f"chunk_{self._chunk_index:03d}_mixed.wav"
            )
        else:
            chunk_info["mixed"] = None

        if chunk_info["mic"] or chunk_info["system"]:
            self._chunks.append(chunk_info)
            log(f"Meeting: flushed final chunk {self._chunk_index}")

        total_duration = time.monotonic() - self._start_time
        log(f"Meeting: recording stopped — {total_duration:.0f}s total, {len(self._chunks)} chunks")
        return self._chunks

    def _write_wav(self, audio_data, filename: str) -> str:
        """Write numpy audio data to a WAV file in the chunk directory."""
        path = os.path.join(self._chunk_dir, filename)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        return path

    def _mix_and_write(self, mic_path: str, sys_path: str, filename: str) -> str:
        """Mix mic and system audio into a single WAV file."""
        # Read both files
        with wave.open(mic_path, "rb") as wf:
            mic_bytes = wf.readframes(wf.getnframes())
        with wave.open(sys_path, "rb") as wf:
            sys_bytes = wf.readframes(wf.getnframes())

        mic_arr = np.frombuffer(mic_bytes, dtype=np.int16)
        sys_arr = np.frombuffer(sys_bytes, dtype=np.int16)

        # Pad shorter array to match longer
        max_len = max(len(mic_arr), len(sys_arr))
        if len(mic_arr) < max_len:
            mic_arr = np.pad(mic_arr, (0, max_len - len(mic_arr)))
        if len(sys_arr) < max_len:
            sys_arr = np.pad(sys_arr, (0, max_len - len(sys_arr)))

        # Mix with clipping protection
        mixed = np.clip(mic_arr.astype(np.int32) + sys_arr.astype(np.int32), -32768, 32767).astype(np.int16)

        path = os.path.join(self._chunk_dir, filename)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(mixed.tobytes())
        return path

    def cleanup_temp_files(self):
        """Remove temporary chunk directory and all files."""
        if self._chunk_dir and os.path.isdir(self._chunk_dir):
            shutil.rmtree(self._chunk_dir, ignore_errors=True)
            log(f"Meeting: cleaned up temp dir {self._chunk_dir}")


# ---------------------------------------------------------------------------
# Meeting Transcriber — chunked transcription with context passing
# ---------------------------------------------------------------------------

class MeetingTranscriber:
    """Transcribes meeting audio chunks sequentially with context continuity."""

    # Whisper-1 costs ~$0.006 per minute
    COST_PER_MINUTE = 0.006

    def __init__(self, config: dict):
        self.config = config
        self.transcriber = Transcriber(config)
        self.total_cost = 0.0

    def transcribe_chunks(self, chunks: list[dict], progress_callback=None) -> list[dict]:
        """Transcribe all chunks and return list of results.

        Each result: {timestamp, mic_text, system_text, mixed_text}

        Args:
            chunks: List of chunk info dicts from MeetingRecorder
            progress_callback: Optional fn(current, total, message) for progress updates
        """
        results = []
        total = len(chunks)
        mic_context = ""
        sys_context = ""

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(i + 1, total, f"Transcribing chunk {i + 1}/{total}")

            result = {
                "timestamp": chunk.get("timestamp", 0),
                "mic_text": "",
                "system_text": "",
            }

            # Transcribe mic audio
            if chunk.get("mic"):
                try:
                    text = self.transcriber.transcribe(
                        chunk["mic"],
                        context_prompt=f"Speaker: User. {mic_context}" if mic_context else "Speaker: User."
                    )
                    result["mic_text"] = text.strip() if text else ""
                    # Keep last ~200 chars as context for next chunk
                    if result["mic_text"]:
                        mic_context = result["mic_text"][-200:]
                    self._track_cost(chunk["mic"])
                except TranscriptionError as e:
                    log(f"Meeting: mic transcription error chunk {i + 1}: {e}")
                    result["mic_text"] = "[transcription error]"

            # Transcribe system audio (or mixed)
            audio_key = "mixed" if chunk.get("mixed") else "system"
            if chunk.get(audio_key):
                try:
                    text = self.transcriber.transcribe(
                        chunk[audio_key],
                        context_prompt=f"Speaker: Others. {sys_context}" if sys_context else "Speaker: Others."
                    )
                    result["system_text"] = text.strip() if text else ""
                    if result["system_text"]:
                        sys_context = result["system_text"][-200:]
                    self._track_cost(chunk[audio_key])
                except TranscriptionError as e:
                    log(f"Meeting: system transcription error chunk {i + 1}: {e}")
                    result["system_text"] = "[transcription error]"

            results.append(result)

        return results

    def _track_cost(self, audio_path: str):
        """Track estimated API cost for an audio file."""
        try:
            with wave.open(audio_path, "rb") as wf:
                duration_min = wf.getnframes() / wf.getframerate() / 60.0
                self.total_cost += duration_min * self.COST_PER_MINUTE
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Meeting Output — transcript formatting
# ---------------------------------------------------------------------------

def format_transcript(results: list[dict], start_time: datetime,
                      total_duration: float, total_cost: float,
                      output_format: str = "markdown") -> str:
    """Format transcription results into a readable transcript."""
    if output_format == "text":
        return _format_text(results, start_time, total_duration, total_cost)
    return _format_markdown(results, start_time, total_duration, total_cost)


def _format_markdown(results, start_time, total_duration, total_cost) -> str:
    lines = [
        "# Meeting Transcript",
        f"**Date:** {start_time.strftime('%Y-%m-%d %H:%M')} | "
        f"**Duration:** {int(total_duration // 60)} min | "
        f"**Est. cost:** ~${total_cost:.2f}",
        "",
        "---",
        "",
    ]

    for result in results:
        ts = result["timestamp"]
        minutes = int(ts // 60)
        seconds = int(ts % 60)
        timestamp_str = f"{minutes:02d}:{seconds:02d}"

        if result.get("mic_text") and result["mic_text"] != "[transcription error]":
            lines.append(f"**[{timestamp_str}]** [You] {result['mic_text']}")
            lines.append("")

        if result.get("system_text") and result["system_text"] != "[transcription error]":
            lines.append(f"**[{timestamp_str}]** [Others] {result['system_text']}")
            lines.append("")

        if result.get("mic_text") == "[transcription error]" or result.get("system_text") == "[transcription error]":
            lines.append(f"**[{timestamp_str}]** *[transcription error]*")
            lines.append("")

        if not result.get("mic_text") and not result.get("system_text"):
            lines.append(f"**[{timestamp_str}]** *[silence]*")
            lines.append("")

    return "\n".join(lines)


def _format_text(results, start_time, total_duration, total_cost) -> str:
    lines = [
        "MEETING TRANSCRIPT",
        f"Date: {start_time.strftime('%Y-%m-%d %H:%M')}",
        f"Duration: {int(total_duration // 60)} min",
        f"Est. cost: ~${total_cost:.2f}",
        "",
        "-" * 40,
        "",
    ]

    for result in results:
        ts = result["timestamp"]
        minutes = int(ts // 60)
        seconds = int(ts % 60)
        timestamp_str = f"[{minutes:02d}:{seconds:02d}]"

        if result.get("mic_text"):
            lines.append(f"{timestamp_str} [You] {result['mic_text']}")
        if result.get("system_text"):
            lines.append(f"{timestamp_str} [Others] {result['system_text']}")
        if not result.get("mic_text") and not result.get("system_text"):
            lines.append(f"{timestamp_str} [silence]")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Meeting Session — orchestrates the full lifecycle
# ---------------------------------------------------------------------------

class MeetingSession:
    """Orchestrates meeting recording, transcription, and output."""

    def __init__(self, config: dict):
        self.config = config
        self.recorder = MeetingRecorder(config)
        self._start_time = None
        self._is_active = False
        self._processing = False
        self._on_complete = None  # callback(transcript_path)
        self._on_progress = None  # callback(current, total, message)

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def is_processing(self) -> bool:
        return self._processing

    @property
    def elapsed_seconds(self) -> float:
        return self.recorder.elapsed_seconds

    def start(self, on_complete=None, on_progress=None) -> bool:
        """Start a meeting recording session.

        Args:
            on_complete: Callback with (transcript_path: str) when done
            on_progress: Callback with (current: int, total: int, message: str)

        Returns:
            True if system audio is available, False if mic-only
        """
        if self._is_active:
            return False

        self._on_complete = on_complete
        self._on_progress = on_progress
        self._start_time = datetime.now()
        self._is_active = True

        has_system = self.recorder.start()

        if has_system:
            log("Meeting session started (mic + system audio)")
        else:
            log("Meeting session started (mic only — system audio unavailable)")
            notifications.send(
                "Meeting Mode",
                "System audio not available — recording mic only. "
                "Install BlackHole for full meeting capture."
            )

        return has_system

    def stop(self):
        """Stop recording and begin transcription in background."""
        if not self._is_active:
            return
        self._is_active = False

        # Stop recording
        chunks = self.recorder.stop()

        if not chunks:
            log("Meeting: no audio chunks to transcribe")
            notifications.send("Meeting Mode", "No audio was captured.")
            self.recorder.cleanup_temp_files()
            return

        # Transcribe in background
        self._processing = True
        thread = threading.Thread(
            target=self._process_meeting,
            args=(chunks,),
            daemon=True,
        )
        thread.start()

    def _process_meeting(self, chunks: list[dict]):
        """Background thread: transcribe chunks and save output."""
        try:
            transcriber = MeetingTranscriber(self.config)

            # Transcribe all chunks
            results = transcriber.transcribe_chunks(
                chunks,
                progress_callback=self._on_progress,
            )

            # Calculate total duration
            total_duration = self.recorder.elapsed_seconds
            if chunks:
                total_duration = max(total_duration, chunks[-1].get("timestamp", 0))

            # Format transcript
            output_format = self.config.get("meeting_output_format", "markdown")
            transcript = format_transcript(
                results,
                self._start_time,
                total_duration,
                transcriber.total_cost,
                output_format,
            )

            # Save to file
            output_dir = self.config.get("meeting_output_dir")
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = MEETING_DIR
                ensure_private_dir(output_path)

            ext = "md" if output_format == "markdown" else "txt"
            ts = self._start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{ts}.{ext}"
            filepath = output_path / filename

            write_secure_text(filepath, transcript, private_parent=not bool(output_dir))
            log(f"Meeting transcript saved to {filepath}")

            notifications.send(
                "Meeting Transcript Ready",
                f"Saved to {filepath.name} (~${transcriber.total_cost:.2f})"
            )

            if self._on_complete:
                self._on_complete(str(filepath))

        except Exception as e:
            log(f"Meeting transcription error: {e}")
            notifications.send("Meeting Error", f"Transcription failed: {str(e)[:80]}")
        finally:
            self._processing = False
            self.recorder.cleanup_temp_files()
