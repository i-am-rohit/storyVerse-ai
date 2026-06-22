from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("", views.index, name="index"),
    path("summarizer/", views.summarizer, name="summarizer"),
    path("api/documents/", views.list_documents, name="list_documents"),
    path("api/documents/<int:document_id>/", views.get_document, name="get_document"),
    path("api/documents/<int:document_id>/delete/", views.delete_document, name="delete_document"),
    path("upload/", views.upload_document, name="upload"),
    path("generate/", views.generate_summary, name="generate"),
    path("generate/stream/", views.generate_summary_stream, name="generate_stream"),
    path("download/<int:summary_id>/", views.download_summary, name="download"),
    path("narrate/", views.narrate_summary, name="narrate"),
]
