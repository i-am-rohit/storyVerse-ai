import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.common.sse import format_event, sse_error

from .forms import StoryGeneratorForm
from .models import Story
from .services import StoryGeneratorService
from .streaming import stream_story_continue, stream_story_generation


@login_required
def generator(request):
    form = StoryGeneratorForm()
    return render(request, "stories/generator.html", {"form": form})


def _source_meta(story: Story) -> dict:
    if story.prompt and "summary of uploaded book:" in story.prompt.lower():
        return {"label": "Uploaded Book Summary", "slug": "uploaded", "icon": "bi-cloud-upload"}
    if story.prompt:
        return {"label": "Generated", "slug": "generated", "icon": "bi-stars"}
    return {"label": "Manual", "slug": "manual", "icon": "bi-pencil-square"}


def _story_row(story: Story) -> dict:
    source = _source_meta(story)
    words = story.content.split()
    preview = story.content.strip()
    if len(preview) > 220:
        preview = preview[:220].rsplit(" ", 1)[0] + "…"

    return {
        "id": story.pk,
        "title": story.title,
        "genre": story.get_genre_display(),
        "genre_slug": story.genre,
        "language": story.get_language_display(),
        "language_slug": story.language,
        "age_group": story.get_age_group_display(),
        "story_length": story.get_story_length_display(),
        "story_length_slug": story.story_length,
        "source": source["label"],
        "source_slug": source["slug"],
        "source_icon": source["icon"],
        "audio_converted": story.audio_converted,
        "preview": preview,
        "word_count": len(words),
        "has_moral": bool(story.moral.strip()),
        "created_at": story.created_at,
        "updated_at": story.updated_at,
    }


@login_required
def index(request):
    stories_qs = Story.objects.filter(user=request.user).order_by("-created_at")
    story_rows = [_story_row(story) for story in stories_qs]

    context = {
        "stories": story_rows,
        "counts": {
            "total": len(story_rows),
            "generated": sum(1 for s in story_rows if s["source_slug"] == "generated"),
            "uploaded": sum(1 for s in story_rows if s["source_slug"] == "uploaded"),
            "converted": sum(1 for s in story_rows if s["audio_converted"]),
        },
    }
    return render(request, "stories/index.html", context)


@login_required
def get_story(request, story_id):
    try:
        story = Story.objects.get(pk=story_id, user=request.user)
    except Story.DoesNotExist:
        return _error("Story not found.", status=404)

    source = _source_meta(story)
    return JsonResponse({
        "success": True,
        "story": {
            "id": story.pk,
            "title": story.title,
            "content": story.content,
            "moral": story.moral,
            "genre": story.get_genre_display(),
            "language": story.get_language_display(),
            "age_group": story.get_age_group_display(),
            "story_length": story.get_story_length_display(),
            "source": source["label"],
            "audio_converted": story.audio_converted,
            "word_count": len(story.content.split()),
            "created_at": story.created_at.isoformat(),
            "updated_at": story.updated_at.isoformat(),
        },
    })


@login_required
@require_POST
def delete_story(request, story_id):
    try:
        story = Story.objects.get(pk=story_id, user=request.user)
    except Story.DoesNotExist:
        return _error("Story not found.", status=404)

    title = story.title
    story.delete()
    return JsonResponse({"success": True, "message": f'"{title}" deleted.'})


def _parse_json(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def _sse_response(generator):
    def event_stream():
        try:
            for event in generator:
                yield format_event(event)
        except Exception as exc:
            yield sse_error(str(exc))

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_POST
def generate_story_stream(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return _error("Please enter a story prompt.")

    language = data.get("language", Story.Language.ENGLISH)
    genre = data.get("genre", Story.Genre.FANTASY)
    age_group = data.get("age_group", Story.AgeGroup.CHILD)
    story_length = data.get("story_length", Story.StoryLength.MEDIUM)

    if language not in dict(Story.Language.choices):
        return _error("Invalid language.")
    if genre not in dict(Story.Genre.choices):
        return _error("Invalid genre.")
    if age_group not in dict(Story.AgeGroup.choices):
        return _error("Invalid age group.")
    if story_length not in dict(Story.StoryLength.choices):
        return _error("Invalid story size.")

    return _sse_response(stream_story_generation(
        prompt=prompt,
        language=language,
        genre=genre,
        age_group=age_group,
        story_length=story_length,
    ))


@login_required
@require_POST
def continue_story_stream(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    genre = data.get("genre", Story.Genre.FANTASY)
    age_group = data.get("age_group", Story.AgeGroup.CHILD)

    if not content:
        return _error("No story content to continue.")

    return _sse_response(stream_story_continue(
        title=title or "Untitled Story",
        content=content,
        genre=genre,
        age_group=age_group,
        language=data.get("language", Story.Language.ENGLISH),
        story_length=data.get("story_length", Story.StoryLength.MEDIUM),
    ))


@login_required
@require_POST
def generate_story(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return _error("Please enter a story prompt.")

    language = data.get("language", Story.Language.ENGLISH)
    genre = data.get("genre", Story.Genre.FANTASY)
    age_group = data.get("age_group", Story.AgeGroup.CHILD)
    story_length = data.get("story_length", Story.StoryLength.MEDIUM)

    if language not in dict(Story.Language.choices):
        return _error("Invalid language.")
    if genre not in dict(Story.Genre.choices):
        return _error("Invalid genre.")
    if age_group not in dict(Story.AgeGroup.choices):
        return _error("Invalid age group.")
    if story_length not in dict(Story.StoryLength.choices):
        return _error("Invalid story size.")

    story = StoryGeneratorService.generate(
        prompt=prompt,
        language=language,
        genre=genre,
        age_group=age_group,
        story_length=story_length,
    )
    return JsonResponse({"success": True, "story": story})


@login_required
@require_POST
def continue_story(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    genre = data.get("genre", Story.Genre.FANTASY)
    age_group = data.get("age_group", Story.AgeGroup.CHILD)

    if not content:
        return _error("No story content to continue.")

    extended = StoryGeneratorService.continue_story(
        title=title or "Untitled Story",
        content=content,
        genre=genre,
        age_group=age_group,
        language=data.get("language", Story.Language.ENGLISH),
        story_length=data.get("story_length", Story.StoryLength.MEDIUM),
    )
    return JsonResponse({"success": True, "content": extended})


@login_required
@require_POST
def save_story(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        return _error("Title and content are required to save.")

    story_id = data.get("story_id")
    if story_id:
        try:
            story = Story.objects.get(pk=story_id, user=request.user)
            story.title = title
            story.content = content
            story.moral = data.get("moral", "")
            story.language = data.get("language", Story.Language.ENGLISH)
            story.genre = data.get("genre", Story.Genre.FANTASY)
            story.age_group = data.get("age_group", Story.AgeGroup.CHILD)
            story.story_length = data.get("story_length", Story.StoryLength.MEDIUM)
            story.prompt = data.get("prompt", "")
            story.save()
        except Story.DoesNotExist:
            return _error("Story not found.", status=404)
    else:
        story = Story.objects.create(
            user=request.user,
            title=title,
            content=content,
            moral=data.get("moral", ""),
            language=data.get("language", Story.Language.ENGLISH),
            genre=data.get("genre", Story.Genre.FANTASY),
            age_group=data.get("age_group", Story.AgeGroup.CHILD),
            story_length=data.get("story_length", Story.StoryLength.MEDIUM),
            prompt=data.get("prompt", ""),
        )

    return JsonResponse({
        "success": True,
        "story_id": story.pk,
        "message": "Story saved successfully.",
    })


@login_required
@require_POST
def convert_to_audio(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    story_id = data.get("story_id")
    if not story_id:
        return _error("Please save the story before converting to audio.")

    try:
        story = Story.objects.get(pk=story_id, user=request.user)
    except Story.DoesNotExist:
        return _error("Story not found.", status=404)

    story.audio_converted = True
    story.save(update_fields=["audio_converted", "updated_at"])

    return JsonResponse({
        "success": True,
        "message": "Story queued for audio conversion.",
        "redirect_url": f"/audiobooks/?story={story.pk}",
    })
