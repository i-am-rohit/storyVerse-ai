from calendar import month_abbr
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.audiobooks.models import Audiobook
from apps.books.models import BookDocument, BookSummary
from apps.stories.models import Story


class DashboardService:
    """Aggregates user analytics for the dashboard."""

    @classmethod
    def get_stats(cls, user) -> dict:
        total_stories = Story.objects.filter(user=user).count()
        total_audiobooks = Audiobook.objects.filter(user=user).count()
        total_summaries = BookSummary.objects.filter(document__user=user).count()

        listening_seconds = (
            Audiobook.objects.filter(user=user).aggregate(total=Sum("duration_seconds"))["total"] or 0
        )
        listening_hours = round(listening_seconds / 3600, 1)

        return {
            "total_stories": total_stories,
            "total_audiobooks": total_audiobooks,
            "total_summaries": total_summaries,
            "listening_hours": listening_hours,
        }

    @classmethod
    def get_genre_distribution(cls, user) -> dict:
        qs = (
            Story.objects.filter(user=user)
            .values("genre")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        genre_map = dict(Story.Genre.choices)
        labels = []
        data = []
        colors = [
            "#3b82f6", "#8b5cf6", "#06b6d4", "#ec4899",
            "#f59e0b", "#10b981", "#ef4444", "#6366f1",
        ]
        for i, entry in enumerate(qs):
            labels.append(genre_map.get(entry["genre"], entry["genre"]))
            data.append(entry["count"])

        if not labels:
            labels = ["No data yet"]
            data = [1]

        return {
            "labels": labels,
            "data": data,
            "colors": colors[: len(labels)],
        }

    @classmethod
    def get_monthly_stories(cls, user, months: int = 6) -> dict:
        cutoff = timezone.now() - timedelta(days=months * 31)
        qs = (
            Story.objects.filter(user=user, created_at__gte=cutoff)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        month_counts = {}
        for entry in qs:
            if entry["month"]:
                key = entry["month"].strftime("%Y-%m")
                month_counts[key] = entry["count"]

        labels = []
        data = []
        now = timezone.now()
        for i in range(months - 1, -1, -1):
            dt = now - timedelta(days=i * 30)
            key = dt.strftime("%Y-%m")
            labels.append(f"{month_abbr[dt.month]} {dt.year}")
            data.append(month_counts.get(key, 0))

        return {"labels": labels, "data": data}

    @classmethod
    def get_language_usage(cls, user) -> dict:
        qs = (
            Story.objects.filter(user=user)
            .values("language")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        lang_map = dict(Story.Language.choices)
        labels = []
        data = []
        for entry in qs:
            labels.append(lang_map.get(entry["language"], entry["language"]))
            data.append(entry["count"])

        if not labels:
            labels = ["English"]
            data = [0]

        return {"labels": labels, "data": data}

    @classmethod
    def get_activity_timeline(cls, user, limit: int = 10) -> list[dict]:
        activities = []

        for story in Story.objects.filter(user=user).order_by("-created_at")[:limit]:
            activities.append({
                "type": "story",
                "title": story.title,
                "description": f"Story created · {story.get_genre_display()}",
                "timestamp": story.created_at,
                "icon": "bi-journal-text",
                "color": "#3b82f6",
                "url": "/stories/",
            })

        for book in Audiobook.objects.filter(user=user).order_by("-created_at")[:limit]:
            activities.append({
                "type": "audiobook",
                "title": book.title,
                "description": f"Audiobook generated · Voice: {book.voice_name}",
                "timestamp": book.created_at,
                "icon": "bi-headphones",
                "color": "#1db954",
                "url": "/audiobooks/",
            })

        for summary in (
            BookSummary.objects.filter(document__user=user)
            .select_related("document")
            .order_by("-created_at")[:limit]
        ):
            activities.append({
                "type": "summary",
                "title": summary.document.title,
                "description": "Book summary generated",
                "timestamp": summary.created_at,
                "icon": "bi-file-earmark-text",
                "color": "#a855f7",
                "url": "/books/",
            })

        for doc in BookDocument.objects.filter(user=user).order_by("-created_at")[:limit]:
            activities.append({
                "type": "upload",
                "title": doc.title,
                "description": f"Document uploaded · {doc.get_file_type_display()}",
                "timestamp": doc.created_at,
                "icon": "bi-cloud-upload",
                "color": "#06b6d4",
                "url": "/books/",
            })

        activities.sort(key=lambda a: a["timestamp"], reverse=True)
        return activities[:limit]

    @classmethod
    def get_dashboard_context(cls, user) -> dict:
        return {
            "stats": cls.get_stats(user),
            "genre_chart": cls.get_genre_distribution(user),
            "monthly_chart": cls.get_monthly_stories(user),
            "language_chart": cls.get_language_usage(user),
            "activities": cls.get_activity_timeline(user),
        }
