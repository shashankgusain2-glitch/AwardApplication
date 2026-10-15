"""
Who may work on which award. The one place that answers it: every staff
page, service and API view that touches an award, report, assignment,
evaluation or file filters through `awards_for(user)`.

    leader   every award (the overview of the whole event; creates awards)
    manager  the awards they manage (a leader picks one manager per award)
    staff    the awards they are allocated to (by a leader or the award's manager)
    others   none (applicants and judges reach reports through their own rules)
"""
from apps.accounts.models import User
from apps.core.services import BusinessRuleError

from .models import Award

# The roles that run awards day to day (the staff portal), and who may do staff work.
PORTAL_ROLES = (User.Role.STAFF, User.Role.MANAGER)
STAFF_WORK_ROLES = (User.Role.STAFF, User.Role.MANAGER, User.Role.LEADER)


def awards_for(user):
    """The awards this user may see and work on."""
    if not getattr(user, "is_authenticated", False):
        return Award.objects.none()
    if user.role == User.Role.LEADER:
        return Award.objects.all()
    if user.role == User.Role.MANAGER:
        return Award.objects.filter(manager=user)
    if user.role == User.Role.STAFF:
        return Award.objects.filter(staff=user)
    return Award.objects.none()


def sees_every_award(user):
    return getattr(user, "role", None) == User.Role.LEADER


def can_work_on(user, award):
    return award is not None and awards_for(user).filter(pk=award.pk).exists()


def check_can_work_on(user, award):
    if not can_work_on(user, award):
        raise BusinessRuleError(f"You aren't on the team for {award.name}. A leader or its award manager "
                                f"can add you.")


def team(award):
    """Everyone who runs this award: its manager and allocated staff (active accounts only)."""
    people = list(award.staff.filter(is_active=True))
    if award.manager and award.manager.is_active and award.manager not in people:
        people.append(award.manager)
    return people
