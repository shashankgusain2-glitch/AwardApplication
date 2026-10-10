from django.urls import path

from . import views

app_name = "awards"

urlpatterns = [
    path("", views.staff_home, name="staff_home"),
    path("settings/", views.settings, name="settings"),
    path("form-builder/", views.form_builder, name="form_builder"),
    path("entries/", views.entries, name="entries"),
    path("duplicates/", views.duplicates, name="duplicates"),
    path("assign/", views.assign, name="assign"),
]
