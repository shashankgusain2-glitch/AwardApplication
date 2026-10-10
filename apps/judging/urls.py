from django.urls import path

from . import views

app_name = "judging"

urlpatterns = [
    path("", views.assignments, name="assignments"),
    path("score/", views.score, name="score"),
]
