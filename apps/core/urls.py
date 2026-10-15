from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("awards/", views.award_list, name="awards"),
    path("awards/<slug:slug>/", views.award_detail, name="award_detail"),
    path("requests/<str:type>/<int:pk>/decide/", views.decide_request, name="decide_request"),
    path("results/", views.results, name="results"),
]
