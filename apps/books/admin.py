from django.contrib import admin

from .models import BookDocument, BookSummary


@admin.register(BookDocument)
class BookDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "file_type", "word_count", "page_count", "created_at")
    list_filter = ("file_type",)
    search_fields = ("title", "user__username")


@admin.register(BookSummary)
class BookSummaryAdmin(admin.ModelAdmin):
    list_display = ("document", "created_at", "updated_at")
    search_fields = ("document__title",)
