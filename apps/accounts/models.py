"""
People and login.

Roles:
- Leader: set on the user (sees all awards).
- Member / Working staff: per award, stored in awards.AwardStaff.
- Judge: has a judging.JudgeProfile.
- Applicant: any user who starts an application.

Planned: magic-link login (one-time email link instead of a password).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_leader = models.BooleanField(default=False)
