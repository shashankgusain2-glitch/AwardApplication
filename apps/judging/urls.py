from django.urls import path

from . import views

app_name = "judging"

urlpatterns = [
    path("", views.assignments, name="assignments"),
    path("assignments/<int:pk>/respond/", views.respond, name="respond"),
    path("score/", views.score, name="score"),
    path("score/<int:pk>/", views.score, name="score"),
]
