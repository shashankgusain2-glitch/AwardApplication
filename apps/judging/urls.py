from django.urls import path

from . import views

app_name = "judging"

urlpatterns = [
    path("", views.tab, name="tab"),
    path("login/<str:token>/", views.link_login, name="login"),
    path("reports/<int:pk>/", views.grade, name="grade"),
    path("reports/<int:pk>/respond/", views.respond, name="respond"),
]
