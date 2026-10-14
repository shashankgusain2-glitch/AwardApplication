from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("review/", views.review, name="review"),
    path("results/", views.results, name="results"),
    path("results/<int:pk>/decide/", views.decide, name="decide"),
    path("people/", views.people, name="people"),
    path("people/<int:pk>/", views.person_action, name="person_action"),
    path("audit/", views.audit, name="audit"),
    path("requests/", views.requests_to_confirm, name="requests"),
]
