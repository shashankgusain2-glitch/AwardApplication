"""`python manage.py seed_managers`: spare award managers for awards created later."""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.awards.access import awards_for

from .factories import AwardFactory


@pytest.mark.django_db
def test_spare_managers_are_created_once_and_manage_nothing_yet():
    AwardFactory()
    call_command("seed_managers", stdout=StringIO())
    call_command("seed_managers", stdout=StringIO())
    managers = User.objects.filter(email__startswith="manager.", role=User.Role.MANAGER)
    assert managers.count() == 5
    assert all(not awards_for(m).exists() for m in managers)
