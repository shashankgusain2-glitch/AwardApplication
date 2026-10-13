"""
People and login.

Every user has exactly one role. Applicants sign up themselves; staff,
judge and leader accounts are created by an admin (or the seed command).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        APPLICANT = "applicant", "Applicant"
        STAFF = "staff", "Staff"
        JUDGE = "judge", "Judge"
        LEADER = "leader", "Leader"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT)

    @property
    def display_name(self):
        return self.get_full_name() or self.email
