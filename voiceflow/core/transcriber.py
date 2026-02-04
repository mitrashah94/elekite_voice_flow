"""VoiceFlow transcription and AI cleanup module."""

import os

# Lazy import for optional dependency
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .config import log, load_dictionary


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

    def transcribe(self, audio_path: str) -> str:
        """Send audio to Whisper and return raw transcript."""
        log(f"Transcribing {audio_path} ...")
        kwargs = {
            "model": self.config.get("whisper_model", "whisper-1"),
            "file": open(audio_path, "rb"),
            "response_format": "text",
        }
        lang = self.config.get("language")
        if lang:
            kwargs["language"] = lang

        # Build prompt from dictionary + user prompt
        prompt_parts = []
        if self.config.get("whisper_prompt"):
            prompt_parts.append(self.config["whisper_prompt"])
        dictionary = load_dictionary()
        if dictionary:
            prompt_parts.append("Custom terms: " + ", ".join(dictionary))
        if prompt_parts:
            kwargs["prompt"] = " | ".join(prompt_parts)

        result = self.client.audio.transcriptions.create(**kwargs)
        text = result.strip() if isinstance(result, str) else str(result).strip()
        log(f"Raw transcript: {text[:120]}...")
        return text

    def cleanup(self, raw_text: str) -> str:
        """Use GPT to clean up filler words, fix grammar, and format."""
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

    def process(self, audio_path: str) -> str:
        """Full pipeline: transcribe -> cleanup -> return final text."""
        raw = self.transcribe(audio_path)
        if not raw:
            return ""
        final = self.cleanup(raw)
        return final
