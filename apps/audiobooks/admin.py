from django.contrib import admin

from .models import Audiobook


@admin.register(Audiobook)
class AudiobookAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "voice_name", "voice_gender", "audio_source", "duration_seconds", "created_at")
    list_filter = ("voice_gender", "audio_source")
    search_fields = ("title", "user__username", "voice_name")
