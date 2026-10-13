from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("verify/", include("apps.accounts.urls")),
    path("judge/", include("apps.judging.urls")),
    path("staff/", include("apps.staff.urls")),
    path("leadership/", include("apps.dashboard.urls")),
    path("", include("apps.entries.urls")),
    path("", include("apps.core.urls")),
]
