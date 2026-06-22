"""Audiobook narration service — ElevenLabs with demo fallback and background music."""

import logging
import re
from collections.abc import Callable

from django.core.files.base import ContentFile
from django.db import close_old_connections

from agents.music_agent import MusicAgent
from agents.narration_agent import NarrationAgent, NarrationError

from .models import Audiobook, generate_demo_wav
from .voices import INDIAN_VOICE_FALLBACK, get_music_style, resolve_story_music

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]


def _safe_filename(title: str, audiobook_id: int, ext: str, suffix: str = "") -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "", title.replace(" ", "_"))
    if not slug:
        slug = f"audiobook_{audiobook_id}"
    tag = f"_{suffix}" if suffix else ""
    return f"{slug}{tag}_{audiobook_id}.{ext}"


def _resolve_music_style(music_style: str, story_genre: str | None, language: str = "en") -> str:
    return resolve_story_music(story_genre, language, music_style)


def _friendly_narration_error(reason: str) -> str:
    err = reason.lower()
    if "quota" in err or "credits remaining" in err:
        return (
            "ElevenLabs credits are too low for this story length. "
            "Demo audio was saved — try a shorter story or add credits."
        )
    if "creator tier" in err or "free_users" in err or "paid plan" in err:
        return (
            "That voice requires an ElevenLabs paid plan. "
            "Demo audio was saved — try Jennie (free tier) or upgrade."
        )
    if "api key" in err:
        return "ElevenLabs is not configured. Demo audio was saved instead."
    return "ElevenLabs audio could not be generated. Demo audio was saved instead."


def _report(progress: ProgressCallback | None, percent: int, message: str) -> None:
    if progress:
        progress(percent, message)


def clear_audiobook_files(audiobook: Audiobook) -> None:
    if audiobook.audio_file:
        audiobook.audio_file.delete(save=False)
        audiobook.audio_file = None
    if audiobook.background_music_file:
        audiobook.background_music_file.delete(save=False)
        audiobook.background_music_file = None


def _save_background_music(
    audiobook: Audiobook,
    music_style: str,
    duration: float,
    progress: ProgressCallback | None = None,
) -> None:
    _report(progress, 82, "Composing free background music…")
    music = MusicAgent().compose(music_style, duration)
    filename = _safe_filename(audiobook.title, audiobook.pk, "wav", "music")
    audiobook.background_music_file.save(
        filename, ContentFile(music.audio_bytes), save=False
    )


def generate_audiobook_audio(
    audiobook: Audiobook,
    story_text: str,
    voice_id: str,
    language: str = "en",
    music_style: str = "none",
    story_genre: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """
    Generate narration audio; optionally attach a separate background music track.
    Voice and music are mixed in the browser during playback (works on free ElevenLabs tier).
    """
    resolved_music = _resolve_music_style(music_style, story_genre, language)
    use_music = resolved_music != "none"
    agent = NarrationAgent()

    _report(progress_callback, 8, "Preparing narration…")

    if agent.is_configured():
        try:
            def narration_progress(chunk_pct: int, message: str) -> None:
                overall = 10 + int(chunk_pct * 0.65)
                _report(progress_callback, overall, message)

            result = _narrate_with_fallback(
                agent, story_text, voice_id, language, on_progress=narration_progress
            )
            _report(progress_callback, 78, "Saving narrated audio…")
            filename = _safe_filename(audiobook.title, audiobook.pk, "mp3")
            audiobook.audio_file.save(filename, ContentFile(result.audio_bytes), save=False)
            audiobook.audio_source = Audiobook.AudioSource.ELEVENLABS
            audiobook.music_style = resolved_music
            audiobook.duration_seconds = int(result.duration_seconds)

            if use_music:
                _save_background_music(
                    audiobook, resolved_music, result.duration_seconds, progress_callback
                )

            _report(progress_callback, 95, "Finalizing audiobook…")
            audiobook.save()

            music_label = get_music_style(resolved_music)
            music_note = f" + {music_label['name']}" if music_label and use_music else ""
            lang_note = " (Hindi)" if language == "hi" else ""
            return {
                "source": "elevenlabs",
                "duration_seconds": audiobook.duration_seconds,
                "music_style": resolved_music,
                "has_background_music": use_music,
                "message": f"Audiobook narrated with ElevenLabs{lang_note}{music_note}.",
            }
        except NarrationError as exc:
            return _save_demo_fallback(
                audiobook, _friendly_narration_error(str(exc)), resolved_music, progress_callback
            )

    return _save_demo_fallback(
        audiobook,
        "ElevenLabs API key not configured — demo audio saved. Add ELEVENLABS_API_KEY to .env.",
        resolved_music,
        progress_callback,
    )


def _narrate_with_fallback(
    agent: NarrationAgent,
    text: str,
    voice_id: str,
    language: str,
    on_progress=None,
):
    if voice_id == INDIAN_VOICE_FALLBACK:
        return agent.narrate(text, voice=voice_id, language=language, on_progress=on_progress)
    try:
        return agent.narrate(text, voice=voice_id, language=language, on_progress=on_progress)
    except NarrationError as exc:
        err = str(exc).lower()
        if any(token in err for token in ("creator tier", "free_users", "paid plan", "library")):
            logger.info("Voice %s unavailable on current plan; using %s", voice_id, INDIAN_VOICE_FALLBACK)
        else:
            logger.warning("Voice %s failed (%s); retrying with %s", voice_id, exc, INDIAN_VOICE_FALLBACK)
        return agent.narrate(
            text, voice=INDIAN_VOICE_FALLBACK, language=language, on_progress=on_progress
        )


def _save_demo_fallback(
    audiobook: Audiobook,
    reason: str,
    music_style: str = "none",
    progress_callback: ProgressCallback | None = None,
) -> dict:
    _report(progress_callback, 40, "Generating demo audio…")
    duration = min(audiobook.duration_seconds, 30) or 10
    voice_wav = generate_demo_wav(duration_seconds=duration)
    filename = _safe_filename(audiobook.title, audiobook.pk, "wav")
    audiobook.audio_file.save(filename, ContentFile(voice_wav), save=False)
    audiobook.audio_source = Audiobook.AudioSource.DEMO
    audiobook.music_style = music_style
    audiobook.duration_seconds = duration

    use_music = music_style != "none"
    if use_music:
        _save_background_music(audiobook, music_style, duration, progress_callback)

    _report(progress_callback, 95, "Finalizing audiobook…")
    audiobook.save()
    return {
        "source": "demo",
        "duration_seconds": audiobook.duration_seconds,
        "music_style": music_style,
        "has_background_music": use_music,
        "message": reason,
    }


def run_audiobook_generation(
    audiobook_id: int,
    user_id: int,
    story_text: str,
    voice_id: str,
    language: str,
    music_style: str,
    story_genre: str | None,
    story_id: int | None,
) -> None:
    """Background worker — updates progress on the Audiobook row."""
    close_old_connections()
    try:
        audiobook = Audiobook.objects.get(pk=audiobook_id, user_id=user_id)
        audiobook.status = Audiobook.GenerationStatus.PROCESSING
        audiobook.progress = 0
        audiobook.status_message = "Starting…"
        audiobook.error_message = ""
        audiobook.save(update_fields=["status", "progress", "status_message", "error_message", "updated_at"])

        def progress(percent: int, message: str) -> None:
            Audiobook.objects.filter(pk=audiobook_id).update(
                progress=min(100, max(0, percent)),
                status_message=message[:255],
            )

        meta = generate_audiobook_audio(
            audiobook,
            story_text,
            voice_id,
            language=language,
            music_style=music_style,
            story_genre=story_genre,
            progress_callback=progress,
        )

        audiobook.refresh_from_db()
        audiobook.status = Audiobook.GenerationStatus.READY
        audiobook.progress = 100
        audiobook.status_message = meta.get("message", "Complete")[:255]
        audiobook.save(update_fields=["status", "progress", "status_message", "updated_at"])

        if story_id:
            from apps.stories.models import Story

            Story.objects.filter(pk=story_id, user_id=user_id).update(audio_converted=True)
    except Exception as exc:
        logger.exception("Audiobook generation failed for id=%s", audiobook_id)
        Audiobook.objects.filter(pk=audiobook_id).update(
            status=Audiobook.GenerationStatus.FAILED,
            error_message=str(exc)[:2000],
            status_message="Generation failed",
        )
    finally:
        close_old_connections()
