from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("applicant/", include("apps.entries.urls")),
    path("judge/", include("apps.judging.urls")),
    path("staff/", include("apps.awards.urls")),
    path("leadership/", include("apps.dashboard.urls")),
    path("", include("apps.core.urls")),
]
