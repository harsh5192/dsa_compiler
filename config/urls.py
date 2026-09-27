"""
URL configuration for the offline-first DSA platform.

Everything the browser needs is served from this process: pages, JSON endpoints
for the code runner, static assets and the PWA manifest.  No external host is
contacted at runtime.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Local Django auth (login/logout/register/settings) under accounts:.
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("problems/", include("apps.problems.urls")),
    path("sheets/", include("apps.sheets.urls")),
    path("submissions/", include("apps.submissions.urls")),
    path("progress/", include("apps.progress.urls")),
    path("api/", include("apps.execution.urls")),
    # Installable app shell.
    path("manifest.webmanifest", TemplateView.as_view(
        template_name="manifest.webmanifest", content_type="application/manifest+json"
    ), name="manifest"),
    path("sw.js", TemplateView.as_view(
        template_name="sw.js", content_type="application/javascript"
    ), name="service-worker"),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    path("favicon.ico", RedirectView.as_view(url="/static/icons/favicon.svg")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
