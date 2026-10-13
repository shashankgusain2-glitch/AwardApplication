"""
People and their profiles.

Every user has exactly one role and logs in with their email. Applicants
sign up themselves; staff, judge and leader accounts are created by a
leader or admin (or the seed command).
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)   # stored hashed, or unusable if None
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        # Superusers manage the platform, so they get the leader role.
        extra.setdefault("role", User.Role.LEADER)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    class Role(models.TextChoices):
        APPLICANT = "applicant", "Applicant"
        STAFF = "staff", "Staff"
        JUDGE = "judge", "Judge"
        LEADER = "leader", "Leader"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True, default="")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [models.Index(fields=["role", "is_active"], name="user_role_active_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(role__in=["applicant", "staff", "judge", "leader"]),
                                   name="user_role_valid"),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.name or self.email

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split(" ")[0] if self.name else self.email


class ApplicantProfile(TimeStampedModel):
    """The applicant's organisation. Staff verify it before its reports go to judges."""

    class Size(models.TextChoices):
        MICRO = "micro", "Micro"
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        LARGE = "large", "Large"

    class Turnover(models.TextChoices):
        UNDER_100CR = "lt_100cr", "Under ₹100 crore"
        FROM_100_TO_500CR = "100_500cr", "₹100–500 crore"
        OVER_500CR = "gt_500cr", "Over ₹500 crore"

    class Verification(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="applicant_profile")
    organisation_name = models.CharField(max_length=200)
    gstin = models.CharField("GSTIN", max_length=15, blank=True, default="")
    holder_pan = models.CharField("PAN of organisation holder", max_length=10, blank=True, default="")
    sector = models.CharField(max_length=100, blank=True, default="")
    organisation_size = models.CharField(max_length=20, choices=Size.choices, blank=True, default="")
    annual_turnover_band = models.CharField(max_length=20, choices=Turnover.choices, blank=True, default="")
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)
    website = models.URLField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    pincode = models.CharField(max_length=6, blank=True, default="")
    contact_name = models.CharField(max_length=150, blank=True, default="")
    contact_designation = models.CharField(max_length=100, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")

    verification_status = models.CharField(max_length=20, choices=Verification.choices,
                                           default=Verification.PENDING, db_index=True)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_note = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["gstin"], condition=~Q(gstin=""), name="profile_gstin_unique"),
            models.CheckConstraint(
                condition=Q(established_year__isnull=True) | Q(established_year__gte=1800, established_year__lte=2100),
                name="profile_established_year_range"),
        ]

    def __str__(self):
        return self.organisation_name


class JudgeProfile(TimeStampedModel):
    """A judge's expertise, place on the priority list, and workload limit."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="judge_profile")
    expertise = models.CharField(max_length=200, blank=True, default="")
    priority = models.PositiveSmallIntegerField(default=5, help_text="1 = first choice")
    max_open_assignments = models.PositiveSmallIntegerField(default=10)
    awards = models.ManyToManyField("awards.Award", blank=True, related_name="judge_panel")

    class Meta:
        ordering = ["priority"]
        constraints = [
            models.CheckConstraint(condition=Q(priority__gte=1, priority__lte=99), name="judge_priority_range"),
            models.CheckConstraint(condition=Q(max_open_assignments__gte=1), name="judge_max_open_at_least_1"),
        ]

    def __str__(self):
        return f"Judge profile: {self.user}"
