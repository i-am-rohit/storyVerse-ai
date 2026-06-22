from django.contrib import admin

from .models import Story


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "genre", "age_group", "language", "audio_converted", "created_at")
    list_filter = ("genre", "age_group", "language", "audio_converted")
    search_fields = ("title", "content", "user__username")
    readonly_fields = ("created_at", "updated_at")
