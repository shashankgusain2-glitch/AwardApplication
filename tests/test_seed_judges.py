"""`python manage.py seed_judges`: spare demo judges on every award's panel, so new awards have free judges."""
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.awards.models import Award

from .factories import AwardFactory, JudgeFactory


@pytest.mark.django_db
def test_pool_joins_every_panel_without_removing_anyone():
    award, other = AwardFactory(), AwardFactory()
    existing = JudgeFactory(awards=[award])

    call_command("seed_judges", stdout=StringIO())

    pool = User.objects.filter(email__endswith="@judges.example", role=User.Role.JUDGE)
    assert pool.count() == 12
    assert award.judge_panel.count() == 13 and award.judge_panel.filter(user=existing).exists()
    assert other.judge_panel.count() == 12


@pytest.mark.django_db
def test_rerun_adds_the_pool_to_a_new_award_without_duplicates():
    AwardFactory()
    call_command("seed_judges", stdout=StringIO())
    new_award = AwardFactory()
    call_command("seed_judges", stdout=StringIO())

    assert User.objects.filter(email__endswith="@judges.example").count() == 12
    assert all(a.judge_panel.count() == 12 for a in Award.objects.all())
    assert new_award.judge_panel.count() == 12


@pytest.mark.django_db
def test_one_award_only():
    award, other = AwardFactory(), AwardFactory()
    call_command("seed_judges", "--award", award.slug, stdout=StringIO())
    assert award.judge_panel.count() == 12 and other.judge_panel.count() == 0
    with pytest.raises(CommandError):
        call_command("seed_judges", "--award", "no-such-award", stdout=StringIO())
