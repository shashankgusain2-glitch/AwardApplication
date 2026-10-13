from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # REST API (versioned) and its docs
    path("api/v1/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    # Server-rendered portal pages
    path("applicant/", include("apps.entries.urls")),
    path("judge/", include("apps.judging.urls")),
    path("staff/", include("apps.awards.urls")),
    path("leadership/", include("apps.dashboard.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.core.urls")),
]
