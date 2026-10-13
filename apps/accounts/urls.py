from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset, name="password_reset"),
    path("password-reset/sent/", views.password_reset_done, name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("password-reset/done/", views.password_reset_complete, name="password_reset_complete"),
]
