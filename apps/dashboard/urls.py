from django.urls import path

from apps.awards import views as award_views

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("awards/", views.awards, name="awards"),
    path("awards/new/", award_views.award_new, name="award_new"),   # only leaders create awards
    path("results/", views.results, name="results"),
    path("results/<int:pk>/decide/", views.decide, name="decide"),
    path("people/", views.people, name="people"),
    path("people/<int:pk>/", views.person_action, name="person_action"),
    path("audit/", views.audit, name="audit"),
    path("requests/", views.requests_to_confirm, name="requests"),
    path("requests/<str:type>/<int:pk>/", views.request_detail, name="request_detail"),
]
