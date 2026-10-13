from django.urls import path

from . import views

app_name = "entries"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("events/", views.events, name="events"),
    path("events/<slug:slug>/apply/", views.start, name="start"),
    path("applications/<int:pk>/", views.application, name="application"),
    path("applications/<int:pk>/request-edit/", views.request_edit, name="request_edit"),
    path("staff/", views.staff, name="staff"),
    path("staff/<int:pk>/", views.staff_action, name="staff_action"),
]
