"""
Who may work on which award. The one place that answers it: every staff
page, service and API view that touches an award, report, assignment,
evaluation or file filters through `awards_for(user)`.

    leader   every award (the overview of the whole event; creates awards)
    manager  the awards they manage (a leader picks one manager per award)
    staff    the awards they are allocated to (by a leader or the award's manager)
    others   none (applicants and judges reach reports through their own rules)

Strict split between the two portal roles (decision log, 16 Oct 2026):
    programme staff  do the work: verify organisations, accept or decline entries, duplicates,
                     assign judges, record conflicts, check requests first, draft the form
    award manager    decides: sets the award up, approves the form, confirms requests, decides
                     re-evaluations and results, answers staff escalations, allocates entries to staff
The manager never does staff work (and staff never decide), so every action has a doer and a
separate decider in the audit log.
"""
from apps.accounts.models import User
from apps.core.services import BusinessRuleError

from .models import Award

# The roles that use the staff portal, who may do staff work, and who may set an award up.
PORTAL_ROLES = (User.Role.STAFF, User.Role.MANAGER)
STAFF_WORK_ROLES = (User.Role.STAFF, User.Role.LEADER)    # leaders: through the API, as before
SETUP_ROLES = (User.Role.MANAGER, User.Role.LEADER)


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


def check_can_set_up(user, award):
    """Award set-up (details, rounds, criteria, judge panel, opening it): its manager, or a leader."""
    if user is None or user.role == User.Role.LEADER:        # None: a command or the date rules
        return
    if user.role == User.Role.MANAGER and award.manager_id == user.pk:
        return
    raise BusinessRuleError(f"The award manager sets up {award.name}; programme staff don't.")


def team(award):
    """Everyone who runs this award: its manager and allocated staff (active accounts only)."""
    people = list(award.staff.filter(is_active=True))
    if award.manager and award.manager.is_active and award.manager not in people:
        people.append(award.manager)
    return people
