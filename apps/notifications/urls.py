from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/open/", views.open_note, name="open"),
    path("read-all/", views.read_all, name="read_all"),
]
