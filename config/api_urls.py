"""All API routes, versioned under /api/v1/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import (
                                     ApplicantProfileViewSet,
                                     LoginView,
                                     LogoutView,
                                     MeView,
                                     RefreshView,
                                     RegisterView,
                                     UserViewSet,
)
from apps.applications.api.views import ApplicationViewSet
from apps.assignments.api.views import AssignmentViewSet, ConflictViewSet, MyAssignmentsView
from apps.awards.api.views import AwardViewSet
from apps.core.api.views import DashboardSummaryView, HealthView, LookupsView
from apps.evaluations.api.views import EvaluationViewSet, ScoreChangeRequestViewSet
from apps.notifications.api import NotificationViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("profiles", ApplicantProfileViewSet, basename="profile")
router.register("awards", AwardViewSet, basename="award")
router.register("applications", ApplicationViewSet, basename="application")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("conflicts", ConflictViewSet, basename="conflict")
router.register("evaluations", EvaluationViewSet, basename="evaluation")
router.register("score-change-requests", ScoreChangeRequestViewSet, basename="score-change-request")
router.register("notifications", NotificationViewSet, basename="notification")

auth_patterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
]

app_name = "api"
urlpatterns = [
    path("auth/", include(auth_patterns)),
    path("judge/my-assignments/", MyAssignmentsView.as_view(), name="my-assignments"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("lookups/", LookupsView.as_view(), name="lookups"),
    path("health/", HealthView.as_view(), name="health"),
    path("", include(router.urls)),
]
