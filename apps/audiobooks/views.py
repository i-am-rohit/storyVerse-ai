import json
import re
import threading

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.stories.models import Story

from .models import Audiobook
from .services import clear_audiobook_files, run_audiobook_generation
from .voices import GENRE_MUSIC, MUSIC_STYLES, VOICES, get_music_style, get_voice, recommend_voices_for_story, resolve_story_music

GENRE_GRADIENTS = {
    "fantasy": ("#3b82f6", "#8b5cf6"),
    "adventure": ("#f59e0b", "#ef4444"),
    "mystery": ("#6366f1", "#312e81"),
    "sci_fi": ("#06b6d4", "#2563eb"),
    "fairy_tale": ("#ec4899", "#a855f7"),
    "historical": ("#78716c", "#292524"),
    "humor": ("#22c55e", "#ca8a04"),
    "horror": ("#991b1b", "#1c1917"),
}


def _parse_json(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def _estimate_duration(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    return max(10, int(words / 2.5))


def _story_payload(story: Story) -> dict:
    colors = GENRE_GRADIENTS.get(story.genre, ("#1db954", "#191414"))
    recommended_music = resolve_story_music(story.genre, story.language, "auto")
    music_info = get_music_style(recommended_music)
    return {
        "id": story.pk,
        "title": story.title,
        "content": story.content,
        "moral": story.moral,
        "genre": story.genre,
        "genre_label": story.get_genre_display(),
        "language": story.language,
        "language_label": story.get_language_display(),
        "duration_estimate": _estimate_duration(story.content),
        "cover": {"color_from": colors[0], "color_to": colors[1]},
        "word_count": len(story.content.split()),
        "recommended_music": recommended_music,
        "recommended_music_label": music_info["name"] if music_info else "",
        "recommended_voices": recommend_voices_for_story(story.language),
    }


def _audiobook_urls(request, audiobook: Audiobook) -> dict:
    urls = {
        "stream_url": request.build_absolute_uri(f"/audiobooks/stream/{audiobook.pk}/"),
        "download_url": request.build_absolute_uri(f"/audiobooks/download/{audiobook.pk}/"),
        "music_stream_url": None,
    }
    if audiobook.background_music_file:
        urls["music_stream_url"] = request.build_absolute_uri(
            f"/audiobooks/music/{audiobook.pk}/"
        )
    return urls


def _audiobook_payload(request, audiobook: Audiobook, include_story: bool = False) -> dict:
    music_info = get_music_style(audiobook.music_style)
    voice = get_voice(audiobook.voice_id) or {
        "id": audiobook.voice_id,
        "name": audiobook.voice_name,
        "gender": audiobook.voice_gender,
    }
    payload = {
        "audiobook_id": audiobook.pk,
        "title": audiobook.title,
        "voice_id": audiobook.voice_id,
        "voice": voice,
        "voice_name": audiobook.voice_name,
        "duration_seconds": audiobook.duration_seconds,
        "audio_source": audiobook.audio_source,
        "music_style": audiobook.music_style,
        "music_label": music_info["name"] if music_info else "No Music",
        "status": audiobook.status,
        "progress": audiobook.progress,
        "status_message": audiobook.status_message,
        "error_message": audiobook.error_message,
        "created_at": audiobook.created_at.isoformat(),
        "story_id": audiobook.story_id,
    }
    if audiobook.story:
        payload["genre_label"] = audiobook.story.get_genre_display()
        payload["language_label"] = audiobook.story.get_language_display()
        if include_story:
            payload.update(_story_payload(audiobook.story))
    if audiobook.status == Audiobook.GenerationStatus.READY and audiobook.audio_file:
        payload.update(_audiobook_urls(request, audiobook))
    return payload


def _start_generation_thread(
    audiobook: Audiobook,
    user_id: int,
    story: Story,
    voice_id: str,
    music_style: str,
) -> None:
    thread = threading.Thread(
        target=run_audiobook_generation,
        kwargs={
            "audiobook_id": audiobook.pk,
            "user_id": user_id,
            "story_text": story.content,
            "voice_id": voice_id,
            "language": story.language,
            "music_style": music_style,
            "story_genre": story.genre,
            "story_id": story.pk,
        },
        daemon=True,
    )
    thread.start()


def _sync_story_audio_flag(story_id: int | None, user_id: int) -> None:
    if not story_id:
        return
    has_audio = Audiobook.objects.filter(
        story_id=story_id,
        user_id=user_id,
        status=Audiobook.GenerationStatus.READY,
    ).exists()
    Story.objects.filter(pk=story_id, user_id=user_id).update(audio_converted=has_audio)


@login_required
def studio(request):
    story_id = request.GET.get("story")
    selected_story = None
    if story_id:
        selected_story = Story.objects.filter(pk=story_id, user=request.user).first()
    return render(request, "audiobooks/studio.html", {
        "voices": VOICES,
        "music_styles": MUSIC_STYLES,
        "genre_default_music": json.dumps(GENRE_MUSIC),
        "selected_story": selected_story,
    })


@login_required
def index(request):
    return studio(request)


@login_required
@require_GET
def list_stories(request):
    stories = Story.objects.filter(user=request.user).order_by("-created_at")[:20]
    return JsonResponse({
        "success": True,
        "stories": [_story_payload(s) for s in stories],
    })


@login_required
@require_GET
def list_audiobooks(request):
    audiobooks = (
        Audiobook.objects.filter(user=request.user)
        .select_related("story")
        .order_by("-created_at")
    )
    return JsonResponse({
        "success": True,
        "audiobooks": [_audiobook_payload(request, ab) for ab in audiobooks],
    })


@login_required
@require_GET
def generation_status(request, audiobook_id):
    try:
        audiobook = Audiobook.objects.select_related("story").get(
            pk=audiobook_id, user=request.user
        )
    except Audiobook.DoesNotExist:
        return _error("Audiobook not found.", status=404)

    payload = _audiobook_payload(request, audiobook, include_story=True)
    return JsonResponse({
        "success": True,
        "audiobook": payload,
        "done": audiobook.status in (
            Audiobook.GenerationStatus.READY,
            Audiobook.GenerationStatus.FAILED,
        ),
    })


@login_required
@require_GET
def list_voices(request):
    gender = request.GET.get("gender")
    region = request.GET.get("region")
    voices = VOICES
    if gender in ("male", "female"):
        voices = [v for v in voices if v["gender"] == gender]
    if region in ("western", "indian"):
        voices = [v for v in voices if v.get("region") == region]
    return JsonResponse({"success": True, "voices": voices})


@login_required
@require_GET
def list_music_styles(request):
    return JsonResponse({"success": True, "music_styles": MUSIC_STYLES})


@login_required
@require_POST
def generate_audiobook(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    story_id = data.get("story_id")
    voice_id = data.get("voice_id")
    music_style = data.get("music_style", "auto")
    audiobook_id = data.get("audiobook_id")

    if not story_id:
        return _error("Please select a story.")
    if not voice_id:
        return _error("Please select a voice.")

    try:
        story = Story.objects.get(pk=story_id, user=request.user)
    except Story.DoesNotExist:
        return _error("Story not found.", status=404)

    voice = get_voice(voice_id)
    if not voice:
        return _error("Invalid voice selection.")

    valid_music = {m["id"] for m in MUSIC_STYLES} | {"auto"}
    if music_style not in valid_music:
        return _error("Invalid background music selection.")

    duration = _estimate_duration(story.content)

    if audiobook_id:
        try:
            audiobook = Audiobook.objects.get(pk=audiobook_id, user=request.user)
        except Audiobook.DoesNotExist:
            return _error("Audiobook not found.", status=404)
        if audiobook.status == Audiobook.GenerationStatus.PROCESSING:
            return _error("This audiobook is already being generated.")

        clear_audiobook_files(audiobook)
        audiobook.story = story
        audiobook.title = story.title
        audiobook.voice_id = voice["id"]
        audiobook.voice_name = voice["name"]
        audiobook.voice_gender = voice["gender"]
        audiobook.duration_seconds = duration
        audiobook.status = Audiobook.GenerationStatus.PROCESSING
        audiobook.progress = 0
        audiobook.status_message = "Queued…"
        audiobook.error_message = ""
        audiobook.save()
    else:
        audiobook = Audiobook.objects.create(
            user=request.user,
            story=story,
            title=story.title,
            voice_id=voice["id"],
            voice_name=voice["name"],
            voice_gender=voice["gender"],
            duration_seconds=duration,
            status=Audiobook.GenerationStatus.PROCESSING,
            progress=0,
            status_message="Queued…",
        )

    _start_generation_thread(audiobook, request.user.pk, story, voice_id, music_style)

    return JsonResponse({
        "success": True,
        "audiobook_id": audiobook.pk,
        "status": audiobook.status,
        "message": "Audio conversion started.",
    })


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_audiobook(request, audiobook_id):
    try:
        audiobook = Audiobook.objects.get(pk=audiobook_id, user=request.user)
    except Audiobook.DoesNotExist:
        return _error("Audiobook not found.", status=404)

    if audiobook.status == Audiobook.GenerationStatus.PROCESSING:
        return _error("Cannot delete while conversion is in progress.")

    story_id = audiobook.story_id
    clear_audiobook_files(audiobook)
    audiobook.delete()
    _sync_story_audio_flag(story_id, request.user.pk)

    return JsonResponse({"success": True, "message": "Audiobook deleted."})


@login_required
@require_GET
def stream_audio(request, audiobook_id):
    """Stream audio inline for the player."""
    try:
        audiobook = Audiobook.objects.get(pk=audiobook_id, user=request.user)
    except Audiobook.DoesNotExist:
        return _error("Audiobook not found.", status=404)

    if not audiobook.audio_file:
        return _error("Audio file not found.", status=404)

    content_type = "audio/mpeg" if audiobook.audio_file.name.endswith(".mp3") else "audio/wav"
    audio_file = audiobook.audio_file.open("rb")
    response = FileResponse(audio_file, content_type=content_type)
    response["Content-Disposition"] = "inline"
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = audiobook.audio_file.size
    return response


@login_required
@require_GET
def stream_music(request, audiobook_id):
    """Stream background music track for layered playback."""
    try:
        audiobook = Audiobook.objects.get(pk=audiobook_id, user=request.user)
    except Audiobook.DoesNotExist:
        return _error("Audiobook not found.", status=404)

    if not audiobook.background_music_file:
        return _error("Background music not found.", status=404)

    audio_file = audiobook.background_music_file.open("rb")
    response = FileResponse(audio_file, content_type="audio/wav")
    response["Content-Disposition"] = "inline"
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = audiobook.background_music_file.size
    return response


@login_required
@require_GET
def download_audio(request, audiobook_id):
    """Download audio as attachment."""
    try:
        audiobook = Audiobook.objects.select_related("story").get(
            pk=audiobook_id, user=request.user
        )
    except Audiobook.DoesNotExist:
        return _error("Audiobook not found.", status=404)

    if not audiobook.audio_file:
        return _error("Audio file not found.", status=404)

    ext = "mp3" if audiobook.audio_file.name.endswith(".mp3") else "wav"
    filename = re.sub(r"[^\w\s-]", "", audiobook.title).strip().replace(" ", "_") or "audiobook"
    content_type = "audio/mpeg" if ext == "mp3" else "audio/wav"

    response = FileResponse(audiobook.audio_file.open("rb"), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}.{ext}"'
    return response
