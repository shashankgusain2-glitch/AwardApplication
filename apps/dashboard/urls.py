from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("review/", views.review, name="review"),
    path("results/", views.results, name="results"),
]
