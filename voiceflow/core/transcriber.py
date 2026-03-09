"""VoiceFlow transcription and AI cleanup module."""

import os

# Lazy import for optional dependency
try:
    from openai import OpenAI, OpenAIError, AuthenticationError, APIConnectionError, RateLimitError
except ImportError:
    OpenAI = None
    OpenAIError = None
    AuthenticationError = None
    APIConnectionError = None
    RateLimitError = None

from .config import log, load_dictionary

# Import platform services for error notifications
from voiceflow.platform import notifications, sounds


class TranscriptionError(Exception):
    """Raised when transcription fails with a user-friendly message.

    This exception is raised after error sound and notification have been sent,
    so callers should not duplicate the error feedback.
    """
    pass


class Transcriber:
    """Handles Whisper transcription and optional GPT text cleanup."""

    def __init__(self, config: dict):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("No OpenAI API key configured. Set it in ~/.voiceflow/config.json or OPENAI_API_KEY env var.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def transcribe(self, audio_path: str, context_prompt: str = None) -> str:
        """Send audio to Whisper and return raw transcript.

        Args:
            audio_path: Path to the WAV audio file
            context_prompt: Optional context to prepend to the Whisper prompt.
                           Used by meeting transcription for chunk-to-chunk continuity.

        Raises:
            TranscriptionError: On API errors (after showing notification)
        """
        log(f"Transcribing {audio_path} ...")
        kwargs = {
            "model": self.config.get("whisper_model", "whisper-1"),
            "file": open(audio_path, "rb"),
            "response_format": "text",
        }
        lang = self.config.get("language")
        if lang:
            kwargs["language"] = lang

        # Build prompt from dictionary + user prompt + optional context
        prompt_parts = []
        if context_prompt:
            prompt_parts.append(context_prompt)
        if self.config.get("whisper_prompt"):
            prompt_parts.append(self.config["whisper_prompt"])
        dictionary = load_dictionary()
        if dictionary:
            prompt_parts.append("Custom terms: " + ", ".join(dictionary))
        if prompt_parts:
            kwargs["prompt"] = " | ".join(prompt_parts)

        try:
            result = self.client.audio.transcriptions.create(**kwargs)
            text = result.strip() if isinstance(result, str) else str(result).strip()
            log(f"Raw transcript: {text[:120]}...")
            return text

        except AuthenticationError as e:
            error_msg = "Transcription failed: Invalid API key"
            log(f"Auth error: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except APIConnectionError as e:
            error_msg = "Transcription failed: Network error"
            log(f"Connection error: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except RateLimitError as e:
            error_msg = "Transcription failed: Rate limit exceeded"
            log(f"Rate limit: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except OpenAIError as e:
            # Catch-all for other OpenAI errors
            error_msg = f"Transcription failed: {type(e).__name__}"
            log(f"OpenAI error: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except Exception as e:
            # Non-OpenAI errors (shouldn't happen but be safe)
            error_msg = "Transcription failed: Unexpected error"
            log(f"Unexpected error during transcription: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

    def cleanup(self, raw_text: str) -> str:
        """Use GPT to clean up filler words, fix grammar, and format.

        Raises:
            TranscriptionError: On API errors (after showing notification)
        """
        if not self.config.get("ai_cleanup", True):
            return raw_text

        log("Cleaning up transcript with AI ...")
        system_prompt = (
            "You are a voice-to-text post-processor. The user dictated the following text. "
            "Clean it up by:\n"
            "1. Removing filler words (um, uh, like, you know, so, basically, etc.)\n"
            "2. Fixing obvious grammar and punctuation\n"
            "3. Preserving the speaker's intended meaning and tone exactly\n"
            "4. Keeping the same level of formality\n"
            "5. Adding proper paragraph breaks if the text is long\n"
            "6. NOT changing the content, rephrasing, or adding information\n"
            "7. If the text looks like code or a command, preserve it exactly\n"
            "Return ONLY the cleaned text, nothing else."
        )
        if self.config.get("custom_prompt"):
            system_prompt += f"\n\nAdditional instructions: {self.config['custom_prompt']}"

        try:
            response = self.client.chat.completions.create(
                model=self.config.get("cleanup_model", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            cleaned = response.choices[0].message.content.strip()
            log(f"Cleaned text: {cleaned[:120]}...")
            return cleaned

        except AuthenticationError as e:
            error_msg = "Cleanup failed: Invalid API key"
            log(f"Auth error during cleanup: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except APIConnectionError as e:
            error_msg = "Cleanup failed: Network error"
            log(f"Connection error during cleanup: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except RateLimitError as e:
            error_msg = "Cleanup failed: Rate limit exceeded"
            log(f"Rate limit during cleanup: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except OpenAIError as e:
            # Catch-all for other OpenAI errors
            error_msg = f"Cleanup failed: {type(e).__name__}"
            log(f"OpenAI error during cleanup: {e}")
            sounds.play("error")
            notifications.send("Transcription Error", error_msg)
            raise TranscriptionError(error_msg) from e

        except Exception as e:
            # Non-OpenAI errors - don't fail silently, but continue with raw text
            log(f"Unexpected error during cleanup: {e} - returning raw text")
            return raw_text

    def process(self, audio_path: str) -> str:
        """Full pipeline: transcribe -> cleanup -> return final text."""
        raw = self.transcribe(audio_path)
        if not raw:
            return ""
        final = self.cleanup(raw)
        return final
