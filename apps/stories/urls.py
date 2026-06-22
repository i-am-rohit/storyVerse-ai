from django.urls import path

from . import views

app_name = "stories"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.generator, name="create"),
    path("api/<int:story_id>/", views.get_story, name="get"),
    path("api/<int:story_id>/delete/", views.delete_story, name="delete"),
    path("generate/", views.generate_story, name="generate"),
    path("generate/stream/", views.generate_story_stream, name="generate_stream"),
    path("continue/", views.continue_story, name="continue"),
    path("continue/stream/", views.continue_story_stream, name="continue_stream"),
    path("save/", views.save_story, name="save"),
    path("convert-audio/", views.convert_to_audio, name="convert_audio"),
]
