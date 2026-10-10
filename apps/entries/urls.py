from django.urls import path

from . import views

app_name = "entries"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("organisation/", views.organisation, name="organisation"),
    path("application/", views.application_form, name="form"),
    path("status/", views.application_status, name="status"),
]
