"""
/auth/  login, refresh, logout, register, me
/users/ leaders manage accounts (create, update, deactivate, activate); staff read;
        everyone reads/updates their own (/users/me/ or /auth/me/)
/profiles/ applicant organisation profiles; staff verify them
"""
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts import services
from apps.accounts.models import ApplicantProfile, User
from apps.audit.services import record
from apps.core.api.permissions import IsApplicant, IsLeader, IsStaffOrLeader
from apps.core.services import BusinessRuleError

from .serializers import (
    AccountCreateSerializer,
    ApplicantProfileSerializer,
    LogoutSerializer,
    MeSerializer,
    RegisterSerializer,
    RoleTokenObtainPairSerializer,
    UserSerializer,
    VerifySerializer,
    tokens_for,
)


class LoginView(TokenObtainPairView):
    """POST {email, password, role?} → {access, refresh, user}. Role (optional) must match the account."""
    serializer_class = RoleTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:   # only successful logins are recorded
            user = User.objects.get(email__iexact=request.data.get("email", "").strip())
            record(user, "login", user, request=request)
        return response


class RefreshView(TokenRefreshView):
    """POST {refresh} → new {access, refresh}. The old refresh token stops working."""


class LogoutView(GenericAPIView):
    """POST {refresh}: the refresh token is blacklisted, so it can't be used again."""
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": None, "message": "Logged out.", "errors": None})


class MeView(GenericAPIView):
    """GET: who am I (id, email, name, role). PATCH {name}: change my own name. Role and email can't change."""
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RegisterView(GenericAPIView):
    """Applicant self sign-up. Staff, judges and leaders are created by a leader (POST /users/)."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_applicant(**serializer.validated_data)
        return Response({"success": True, "data": {"user": UserSerializer(user).data, **tokens_for(user)},
                         "message": "Account created.", "errors": None}, status=status.HTTP_201_CREATED)


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    list / retrieve: staff and leaders. create / update: leaders only.
    /users/me/: any logged-in user reads or updates their own name.
    """
    queryset_model = User
    serializer_class = UserSerializer
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "name"]
    ordering_fields = ["email", "name", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        return User.objects.order_by("email")

    def get_permissions(self):
        if self.action == "me":
            return [permissions.IsAuthenticated()]
        if self.action in ("create", "update", "partial_update", "deactivate", "activate"):
            return [IsLeader()]
        return [IsStaffOrLeader()]

    def get_serializer_class(self):
        if self.action == "create":
            return AccountCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        judge_fields = {k: data.pop(k) for k in ("expertise", "priority", "max_open_assignments") if k in data}
        user = services.create_account(created_by=request.user, **data, **judge_fields)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        data = serializer.validated_data
        if serializer.instance.pk == self.request.user.pk and ("role" in data or "is_active" in data):
            raise BusinessRuleError("You can't change your own role or deactivate yourself.")
        if "is_active" in data:   # same rules as /deactivate/ and /activate/ (tokens blacklisted)
            services.set_active(serializer.instance, by=self.request.user, active=data.pop("is_active"))
        user = serializer.save()
        record(self.request.user, "update", user,
               changes={k: str(v) for k, v in serializer.validated_data.items()})

    @extend_schema(request=None, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """The account can't log in any more; its refresh tokens stop working. Nothing is deleted."""
        user = services.set_active(self.get_object(), by=request.user, active=False)
        return Response(UserSerializer(user).data)

    @extend_schema(request=None, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = services.set_active(self.get_object(), by=request.user, active=True)
        return Response(UserSerializer(user).data)

    @extend_schema(request=MeSerializer, responses=MeSerializer)
    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        if request.method == "PATCH":
            serializer = MeSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(MeSerializer(request.user).data)


class ApplicantProfileViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Applicants: their own profile (/profiles/mine/). Staff and leaders: all
    profiles, and verify them (/profiles/{id}/verify/).
    """
    serializer_class = ApplicantProfileSerializer
    queryset_model = ApplicantProfile
    filterset_fields = ["verification_status", "organisation_size", "state"]
    search_fields = ["organisation_name", "gstin", "user__email"]
    ordering_fields = ["organisation_name", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        qs = ApplicantProfile.objects.select_related("user")
        if self.request.user.role in (User.Role.STAFF, User.Role.LEADER):
            return qs
        return qs.filter(user=self.request.user)

    def get_permissions(self):
        if self.action == "mine":
            return [IsApplicant()]
        return [IsStaffOrLeader()]

    @extend_schema(request=ApplicantProfileSerializer, responses=ApplicantProfileSerializer)
    @action(detail=False, methods=["get", "put", "patch"])
    def mine(self, request):
        profile = ApplicantProfile.objects.filter(user=request.user).first()
        if request.method == "GET":
            if profile is None:
                return Response(None)
            return Response(self.get_serializer(profile).data)
        profile = services.save_profile(request.user, request.data, partial=request.method == "PATCH")
        return Response(self.get_serializer(profile).data)

    @extend_schema(request=VerifySerializer, responses=ApplicantProfileSerializer)
    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        profile = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.verify_organisation(profile, by=request.user, **serializer.validated_data)
        return Response(self.get_serializer(profile).data)
