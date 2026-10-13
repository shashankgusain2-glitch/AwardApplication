from django.urls import path

from . import views

app_name = "staff"

urlpatterns = [
    path("", views.home, name="home"),
    path("reports/", views.reports, name="reports"),
    path("reports/<int:pk>/", views.report, name="report"),
    path("reports/<int:pk>/action/", views.report_action, name="report_action"),
    path("judges/", views.judges, name="judges"),
    path("judges/<int:pk>/link/", views.judge_link, name="judge_link"),
    path("requests/", views.requests, name="requests"),
    path("requests/score/<int:pk>/", views.score_request_action, name="score_request_action"),
    path("events/", views.events, name="events"),
    path("events/<slug:slug>/form/", views.form_editor, name="form_editor"),
    path("activity/", views.activity, name="activity"),
]
