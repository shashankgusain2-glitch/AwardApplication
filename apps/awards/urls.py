from django.urls import path

from . import views

app_name = "awards"

urlpatterns = [
    path("", views.staff_home, name="staff_home"),
    path("settings/", views.settings, name="settings"),
    path("form-builder/", views.form_builder, name="form_builder"),
    path("form-builder/<slug:slug>/", views.form_builder, name="form_builder"),
    path("entries/", views.entries, name="entries"),
    path("duplicates/", views.duplicates, name="duplicates"),
    path("assign/", views.assign, name="assign"),
    path("assign/<int:pk>/", views.assign, name="assign"),
    path("organisations/<int:pk>/verify/", views.verify_organisation, name="verify_organisation"),
    path("entries/<int:pk>/edit-request/", views.decide_edit, name="decide_edit"),
    path("entries/<int:pk>/reject/", views.reject_report, name="reject_report"),
    path("score-changes/<int:pk>/", views.decide_score_change, name="decide_score_change"),
]
