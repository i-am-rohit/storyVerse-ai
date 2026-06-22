"""
URL configuration for StoryVerse AI.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from apps.dashboard import views as dashboard_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard_views.home, name="home"),
    path("welcome/", dashboard_views.landing, name="landing"),
    path("help/", dashboard_views.user_guide, name="user_guide"),
    path("dashboard/", include("apps.dashboard.urls")),
    path("stories/", include("apps.stories.urls")),
    path("audiobooks/", include("apps.audiobooks.urls")),
    path("books/", include("apps.books.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("oauth/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
