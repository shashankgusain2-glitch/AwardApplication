from django.urls import path

from . import views

app_name = "awards"

urlpatterns = [
    path("", views.staff_home, name="staff_home"),
    path("settings/", views.settings, name="settings"),
    path("awards/", views.award_list, name="award_list"),
    path("awards/new/", views.award_new, name="award_new"),
    path("awards/<slug:slug>/", views.award_edit, name="award_edit"),
    path("awards/<slug:slug>/status/", views.award_status, name="award_status"),
    path("awards/<slug:slug>/criteria/", views.award_criteria, name="award_criteria"),
    path("awards/<slug:slug>/panel/", views.award_panel, name="award_panel"),
    path("form-builder/", views.form_builder, name="form_builder"),
    path("form-builder/<slug:slug>/", views.form_builder, name="form_builder"),
    path("form-builder/<slug:slug>/new-version/", views.form_edit, name="form_edit"),
    path("entries/", views.entries, name="entries"),
    path("duplicates/", views.duplicates, name="duplicates"),
    path("assign/", views.assign, name="assign"),
    path("assign/<int:pk>/", views.assign, name="assign"),
    path("organisations/<int:pk>/verify/", views.verify_organisation, name="verify_organisation"),
    path("entries/<int:pk>/reject/", views.reject_report, name="reject_report"),
]
