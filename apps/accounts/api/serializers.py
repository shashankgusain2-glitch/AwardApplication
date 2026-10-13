from django.contrib.auth import password_validation
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ApplicantProfile, JudgeProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class MeSerializer(serializers.ModelSerializer):
    """What users may change about themselves: only their name."""
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "created_at"]
        read_only_fields = ["id", "email", "role", "created_at"]


class AccountCreateSerializer(serializers.Serializer):
    """Leaders create staff, judge and leader accounts."""
    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=User.Role.choices)
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    expertise = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(required=False, min_value=1, max_value=99)
    max_open_assignments = serializers.IntegerField(required=False, min_value=1)


def tokens_for(user):
    refresh = RoleTokenObtainPairSerializer.get_token(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Email + password → JWT access + refresh. The role, email and name are in
    the token claims. `role` is optional (the web login is one form); if it
    is sent and doesn't match the account, login is refused on the server.
    """
    role = serializers.ChoiceField(choices=User.Role.choices, required=False, write_only=True)

    default_error_messages = {"no_active_account": "Incorrect email or password."}

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        token["name"] = user.name
        return token

    def validate(self, attrs):
        role = attrs.pop("role", None)
        data = super().validate(attrs)
        if role and self.user.role != role:
            raise AuthenticationFailed("Incorrect email or password for this role.", code="role_mismatch")
        data["user"] = UserSerializer(self.user).data
        return data


class RegisterSerializer(serializers.Serializer):
    """Applicant self sign-up. Always creates an applicant; a sent `role` is ignored."""
    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    organisation_name = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate(self, attrs):
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": ["An account with this email already exists."]})
        password_validation.validate_password(attrs["password"], User(email=attrs["email"], name=attrs["name"]))
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        RefreshToken(self.validated_data["refresh"]).blacklist()


class ApplicantProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ApplicantProfile
        fields = ["id", "user", "organisation_name", "gstin", "holder_pan", "sector", "organisation_size",
                  "annual_turnover_band", "established_year", "website", "address", "city", "state", "pincode",
                  "contact_name", "contact_designation", "contact_phone", "verification_status",
                  "verified_at", "verification_note", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "verification_status", "verified_at", "verification_note",
                            "created_at", "updated_at"]

    def validate_gstin(self, value):
        from apps.core.validators import validate_gstin
        return validate_gstin(value) if value else value

    def validate_holder_pan(self, value):
        from apps.core.validators import validate_pan
        return validate_pan(value) if value else value


class VerifySerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class JudgeProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = JudgeProfile
        fields = ["id", "user", "expertise", "priority", "max_open_assignments", "awards"]
