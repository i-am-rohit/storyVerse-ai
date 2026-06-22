from django.urls import path

from . import views

app_name = "audiobooks"

urlpatterns = [
    path("", views.index, name="index"),
    path("studio/", views.studio, name="studio"),
    path("api/stories/", views.list_stories, name="list_stories"),
    path("api/audiobooks/", views.list_audiobooks, name="list_audiobooks"),
    path("api/audiobooks/<int:audiobook_id>/status/", views.generation_status, name="generation_status"),
    path("api/audiobooks/<int:audiobook_id>/delete/", views.delete_audiobook, name="delete_audiobook"),
    path("api/voices/", views.list_voices, name="list_voices"),
    path("api/music/", views.list_music_styles, name="list_music"),
    path("api/generate/", views.generate_audiobook, name="generate"),
    path("stream/<int:audiobook_id>/", views.stream_audio, name="stream"),
    path("music/<int:audiobook_id>/", views.stream_music, name="stream_music"),
    path("download/<int:audiobook_id>/", views.download_audio, name="download"),
]
