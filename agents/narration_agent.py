"""Narration agent — ElevenLabs text-to-speech integration."""

import json
import logging
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .audio_mixer import pcm_to_wav, wav_duration_seconds
from .voice_map import (
    DEFAULT_MODEL,
    ELEVENLABS_LANGUAGE_MAP,
    ELEVENLABS_VOICE_MAP,
    MAX_CHUNK_CHARS,
)

DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"

logger = logging.getLogger(__name__)


def _ssl_context() -> ssl.SSLContext:
    """Use certifi CA bundle when available (fixes macOS Python SSL errors)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class NarrationError(Exception):
    """Raised when narration cannot be generated."""


@dataclass
class NarrationResult:
    audio_bytes: bytes
    duration_seconds: float
    voice: str
    source: str = "elevenlabs"
    audio_format: str = "mp3"
    audio_path: Path | None = None


class NarrationAgent:
    """Generates narrated audio from story text via ElevenLabs TTS."""

    def __init__(self, api_key: str | None = None, model_id: str | None = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.model_id = model_id or getattr(settings, "ELEVENLABS_MODEL", DEFAULT_MODEL)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def resolve_voice_id(self, voice: str) -> str:
        if voice in ELEVENLABS_VOICE_MAP:
            return ELEVENLABS_VOICE_MAP[voice]
        if settings.ELEVENLABS_VOICE_ID:
            return settings.ELEVENLABS_VOICE_ID
        return ELEVENLABS_VOICE_MAP["aria"]

    def narrate(
        self,
        text: str,
        voice: str = "aria",
        language: str = "en",
        output_dir: Path | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        on_progress=None,
    ) -> NarrationResult:
        if not self.is_configured():
            raise NarrationError(
                "ElevenLabs API key is not configured. Set ELEVENLABS_API_KEY in your .env file."
            )

        text = text.strip()
        if not text:
            raise NarrationError("No text provided for narration.")

        voice_id = self.resolve_voice_id(voice)
        chunks = self._chunk_text(text)
        audio_parts: list[bytes] = []
        total_chunks = len(chunks)

        for index, chunk in enumerate(chunks):
            if on_progress:
                pct = int(((index + 1) / total_chunks) * 100)
                on_progress(pct, f"Narrating section {index + 1} of {total_chunks}")
            audio_parts.append(self._synthesize_chunk(chunk, voice_id, language, output_format))

        if output_format.startswith("pcm") or output_format.startswith("wav"):
            pcm = b"".join(audio_parts) if output_format.startswith("pcm") else None
            if output_format.startswith("wav"):
                audio_bytes = b"".join(audio_parts)
                duration_seconds = wav_duration_seconds(audio_bytes)
                file_ext = "wav"
            else:
                audio_bytes = pcm_to_wav(pcm)
                duration_seconds = wav_duration_seconds(audio_bytes)
                file_ext = "wav"
        else:
            audio_bytes = b"".join(audio_parts)
            word_count = len(re.findall(r"\w+", text))
            duration_seconds = max(5.0, word_count / 2.5)
            file_ext = "mp3" if "mp3" in output_format else "audio"

        audio_path = None
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            audio_path = output_dir / f"narration_{voice_id[:8]}.{file_ext}"
            audio_path.write_bytes(audio_bytes)

        return NarrationResult(
            audio_bytes=audio_bytes,
            duration_seconds=duration_seconds,
            voice=voice_id,
            source="elevenlabs",
            audio_format=file_ext,
            audio_path=audio_path,
        )

    def _chunk_text(self, text: str) -> list[str]:
        if len(text) <= MAX_CHUNK_CHARS:
            return [text]

        sentences = re.split(r"(?<=[.!?।])\s+", text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    chunks.append(current)
                if len(sentence) <= MAX_CHUNK_CHARS:
                    current = sentence
                else:
                    for i in range(0, len(sentence), MAX_CHUNK_CHARS):
                        chunks.append(sentence[i:i + MAX_CHUNK_CHARS])
                    current = ""

        if current:
            chunks.append(current)

        return chunks or [text[:MAX_CHUNK_CHARS]]

    def _synthesize_chunk(
        self,
        text: str,
        voice_id: str,
        language: str = "en",
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> bytes:
        query = urllib.parse.urlencode({"output_format": output_format})
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{query}"
        lang_code = ELEVENLABS_LANGUAGE_MAP.get(language, "en")
        payload_data = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }
        if lang_code:
            payload_data["language_code"] = lang_code
        payload = json.dumps(payload_data).encode("utf-8")

        accept = "audio/pcm" if output_format.startswith("pcm") else "audio/mpeg"

        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Accept": accept,
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=120, context=_ssl_context()
            ) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in (400, 401, 402, 403):
                logger.warning("ElevenLabs API error %s: %s", exc.code, body)
            else:
                logger.error("ElevenLabs API error %s: %s", exc.code, body)
            raise NarrationError(self._parse_api_error(exc.code, body)) from exc
        except urllib.error.URLError as exc:
            logger.error("ElevenLabs connection error: %s", exc.reason)
            raise NarrationError(f"Could not reach ElevenLabs API: {exc.reason}") from exc

    @staticmethod
    def _parse_api_error(code: int, body: str) -> str:
        try:
            detail = json.loads(body).get("detail", {})
            if isinstance(detail, dict):
                return detail.get("message", body)
            if isinstance(detail, list) and detail:
                return detail[0].get("msg", body)
        except json.JSONDecodeError:
            pass
        return f"ElevenLabs API returned HTTP {code}. Check your API key and quota."
