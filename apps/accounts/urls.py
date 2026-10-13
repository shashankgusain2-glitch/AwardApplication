from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.verify_email, name="verify_email"),
    path("code/", views.verify_code, name="verify_code"),
    path("logout/", views.logout_view, name="logout"),
]
