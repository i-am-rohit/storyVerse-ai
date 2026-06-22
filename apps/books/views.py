import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.common.sse import format_event, sse_error

from .models import BookDocument, BookSummary
from .services.document_parser import DocumentParseError, extract_text, validate_upload
from .services.summary_service import SummaryService
from .services.summary_stream import stream_summary_generation

VALID_SUMMARY_TYPES = {
    "all",
    "short",
    "detailed",
    "full_book",
    "chapters",
    "chapters_short",
    "main_points",
    "short_stories",
    "reading_guide",
}


def _error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def _parse_json(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _document_payload(doc: BookDocument) -> dict:
    has_summary = False
    summary_id = None
    summary_types = []
    try:
        summary = doc.summary
        has_summary = True
        summary_id = summary.pk
        if summary.short_summary:
            summary_types.append("short")
        if summary.detailed_summary:
            summary_types.append("detailed")
            summary_types.append("full_book")
        if summary.chapter_summaries:
            summary_types.append("chapters")
        if summary.chapter_short_summaries:
            summary_types.append("chapters_short")
        if summary.main_points:
            summary_types.append("main_points")
        if summary.short_stories:
            summary_types.append("short_stories")
        if summary.reading_guide:
            summary_types.append("reading_guide")
    except ObjectDoesNotExist:
        pass

    return {
        "id": doc.pk,
        "title": doc.title,
        "file_type": doc.file_type,
        "word_count": doc.word_count,
        "page_count": doc.page_count,
        "created_at": doc.created_at.isoformat(),
        "has_summary": has_summary,
        "summary_id": summary_id,
        "summary_types": summary_types,
    }


def _summary_payload(summary: BookSummary) -> dict:
    return {
        "short_summary": summary.short_summary,
        "detailed_summary": summary.detailed_summary,
        "chapter_summaries": summary.chapter_summaries,
        "chapter_short_summaries": summary.chapter_short_summaries,
        "main_points": summary.main_points,
        "short_stories": summary.short_stories,
        "reading_guide": summary.reading_guide,
        "summary_id": summary.pk,
        "document_id": summary.document_id,
    }


@login_required
def summarizer(request):
    return render(request, "books/summarizer.html")


@login_required
def index(request):
    return summarizer(request)


@login_required
@require_GET
def list_documents(request):
    documents = BookDocument.objects.filter(user=request.user).order_by("-created_at")
    return JsonResponse({
        "success": True,
        "documents": [_document_payload(doc) for doc in documents],
    })


@login_required
@require_GET
def get_document(request, document_id):
    try:
        document = BookDocument.objects.get(pk=document_id, user=request.user)
    except BookDocument.DoesNotExist:
        return _error("Document not found.", status=404)

    payload = {"document": _document_payload(document)}
    try:
        payload["summary"] = _summary_payload(document.summary)
    except ObjectDoesNotExist:
        payload["summary"] = None

    return JsonResponse({"success": True, **payload})


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_document(request, document_id):
    try:
        document = BookDocument.objects.get(pk=document_id, user=request.user)
    except BookDocument.DoesNotExist:
        return _error("Document not found.", status=404)

    if document.file:
        document.file.delete(save=False)
    document.delete()
    return JsonResponse({"success": True, "message": "Book deleted."})


@login_required
@require_POST
def upload_document(request):
    upload = request.FILES.get("file")
    if not upload:
        return _error("No file provided.")

    try:
        file_type = validate_upload(upload)
        text, page_count = extract_text(upload, file_type)
    except DocumentParseError as exc:
        return _error(str(exc))

    if len(text.split()) < 50:
        return _error("Document is too short. Please upload a file with at least 50 words.")

    title = upload.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    upload.seek(0)

    document = BookDocument.objects.create(
        user=request.user,
        title=title,
        file=upload,
        file_type=file_type,
        extracted_text=text,
        word_count=len(text.split()),
        page_count=page_count,
    )

    return JsonResponse({
        "success": True,
        "document": _document_payload(document),
    })


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
def generate_summary_stream(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    document_id = data.get("document_id")
    summary_type = data.get("type", "all")

    if not document_id:
        return _error("No document selected.")
    if summary_type not in VALID_SUMMARY_TYPES:
        return _error("Invalid summary type.")

    try:
        document = BookDocument.objects.get(pk=document_id, user=request.user)
    except BookDocument.DoesNotExist:
        return _error("Document not found.", status=404)

    def run_and_save():
        generated = {}
        for event in stream_summary_generation(
            summary_type,
            document.extracted_text,
            document.title,
            document.page_count,
        ):
            if event.get("event") == "complete":
                generated = event.get("generated", {})
            yield event

        if generated:
            summary, _ = BookSummary.objects.get_or_create(document=document)
            for key, value in generated.items():
                setattr(summary, key, value)
            summary.save()

            yield {
                "event": "saved",
                "summary": _summary_payload(summary),
                "document": _document_payload(document),
                "generated_type": summary_type,
            }

    return _sse_response(run_and_save())


@login_required
@require_POST
def generate_summary(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    document_id = data.get("document_id")
    summary_type = data.get("type", "all")

    if not document_id:
        return _error("No document selected.")
    if summary_type not in VALID_SUMMARY_TYPES:
        return _error("Invalid summary type.")

    try:
        document = BookDocument.objects.get(pk=document_id, user=request.user)
    except BookDocument.DoesNotExist:
        return _error("Document not found.", status=404)

    generated = SummaryService.generate_by_type(
        summary_type,
        document.extracted_text,
        document.title,
        document.page_count,
    )

    summary, _ = BookSummary.objects.get_or_create(document=document)
    for key, value in generated.items():
        setattr(summary, key, value)
    summary.save()

    return JsonResponse({
        "success": True,
        "summary": _summary_payload(summary),
        "document": _document_payload(document),
        "generated_type": summary_type,
    })


@login_required
@require_GET
def download_summary(request, summary_id):
    try:
        summary = BookSummary.objects.select_related("document").get(
            pk=summary_id,
            document__user=request.user,
        )
    except BookSummary.DoesNotExist:
        return _error("Summary not found.", status=404)

    doc = summary.document
    lines = [
        f"# {doc.title} — Summary Report",
        "Generated by StoryVerse AI",
        f"Words in source: {doc.word_count:,}",
        "",
    ]

    if summary.short_summary:
        lines.extend(["## Short Summary", summary.short_summary, ""])
    if summary.detailed_summary:
        lines.extend(["## Full Book Summary", summary.detailed_summary, ""])
    if summary.reading_guide:
        lines.extend(["## Best Way to Read This Book", summary.reading_guide, ""])
    if summary.main_points:
        lines.append("## Main Points")
        for item in summary.main_points:
            category = item.get("category", "Point")
            lines.append(f"- [{category}] {item.get('point', '')}")
        lines.append("")
    if summary.chapter_short_summaries:
        lines.append("## Chapter Wise (Short)")
        for chapter in summary.chapter_short_summaries:
            pct = chapter.get("percent_of_book")
            pct_label = f" ({pct}% of book)" if pct is not None else ""
            lines.append(f"\n### {chapter['title']}{pct_label}")
            lines.append(chapter["summary"])
        lines.append("")
    if summary.short_stories:
        lines.append("## Short Stories from Book")
        for story in summary.short_stories:
            lines.append(f"\n### {story['title']}")
            if story.get("source_chapter"):
                lines.append(f"Based on: {story['source_chapter']}")
            lines.append(story["content"])
            if story.get("moral"):
                lines.append(f"Moral: {story['moral']}")
        lines.append("")
    if summary.chapter_summaries:
        lines.append("## Chapter Summaries")
        for chapter in summary.chapter_summaries:
            lines.append(f"\n### {chapter['title']}")
            lines.append(chapter["summary"])

    content = "\n".join(lines)
    filename = doc.title.replace(" ", "_") + "_summary.txt"

    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def narrate_summary(request):
    data = _parse_json(request)
    if data is None:
        return _error("Invalid JSON payload.")

    summary_id = data.get("summary_id")
    summary_type = data.get("type", "short")
    story_index = data.get("story_index")

    try:
        summary = BookSummary.objects.select_related("document").get(
            pk=summary_id,
            document__user=request.user,
        )
    except BookSummary.DoesNotExist:
        return _error("Summary not found.", status=404)

    if summary_type == "short_stories" and story_index is not None:
        try:
            story_item = summary.short_stories[int(story_index)]
        except (IndexError, TypeError, ValueError):
            return _error("That short story was not found.")
        narration_text = story_item.get("content", "")
        story_title = story_item.get("title", f"{summary.document.title} — Story")
        story_moral = story_item.get("moral", "Knowledge shared is knowledge multiplied.")
    else:
        text_map = {
            "short": summary.short_summary,
            "detailed": summary.detailed_summary,
            "full_book": summary.detailed_summary,
            "chapters": "\n\n".join(
                f"{c['title']}: {c['summary']}" for c in summary.chapter_summaries
            ),
            "chapters_short": "\n\n".join(
                f"{c['title']} ({c.get('percent_of_book', 0)}%): {c['summary']}"
                for c in summary.chapter_short_summaries
            ),
            "main_points": "\n".join(
                f"• {p.get('point', '')}" for p in summary.main_points
            ),
            "short_stories": "\n\n".join(
                f"{s['title']}\n{s['content']}" for s in summary.short_stories
            ),
            "reading_guide": summary.reading_guide,
        }
        narration_text = text_map.get(summary_type) or summary.short_summary
        story_title = f"{summary.document.title} — Summary"
        story_moral = "Knowledge shared is knowledge multiplied."

    if not narration_text:
        return _error("That summary type has not been generated yet.")

    from apps.stories.models import Story

    story = Story.objects.create(
        user=request.user,
        title=story_title,
        content=narration_text,
        moral=story_moral,
        genre=Story.Genre.HISTORICAL,
        age_group=Story.AgeGroup.ADULT,
        prompt=f"Summary of uploaded book: {summary.document.title}",
    )

    return JsonResponse({
        "success": True,
        "story_id": story.pk,
        "redirect_url": f"/audiobooks/?story={story.pk}",
    })
