from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("verify/", include("apps.accounts.urls")),
    path("", include("apps.entries.urls")),
    path("", include("apps.core.urls")),
]
