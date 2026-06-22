from django.conf import settings
from django.db import models


class BookDocument(models.Model):
    class FileType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"
        TXT = "txt", "TXT"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="book_documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/books/")
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    extracted_text = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BookSummary(models.Model):
    document = models.OneToOneField(
        BookDocument,
        on_delete=models.CASCADE,
        related_name="summary",
    )
    short_summary = models.TextField(blank=True)
    detailed_summary = models.TextField(blank=True)
    chapter_summaries = models.JSONField(default=list)
    chapter_short_summaries = models.JSONField(default=list)
    main_points = models.JSONField(default=list)
    short_stories = models.JSONField(default=list)
    reading_guide = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "book summaries"

    def __str__(self):
        return f"Summary: {self.document.title}"
