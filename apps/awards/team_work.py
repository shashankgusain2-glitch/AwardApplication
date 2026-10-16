"""
How programme staff and the award manager work together on one award (the strict split in
apps/awards/access.py: staff do the work, the manager decides).

    Form approval   staff save a draft of the next form version and send it; the manager
                    publishes it or sends it back with a note. An award with no active manager:
                    the staff member's save publishes it at once (nobody else could).
    Escalations     staff pass a hard case up with a question; the manager answers; staff act.
    Allocation      the manager gives entries to named staff on the award and sees each person's
                    workload. An entry nobody was given is for anyone on the award's staff.

Every step is audited and the other side is notified.
"""
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .access import check_can_work_on
from .models import Award, Escalation, FormVersion

# Entries still being worked on by staff or judges (allocation and workload count only these).
OPEN_WORK = ("submitted", "accepted", "assigned", "in_review")


def active_manager(award):
    manager = award.manager
    return manager if manager is not None and manager.is_active else None


def _check_staff_on(user, award, what):
    if user.role != User.Role.STAFF:
        raise BusinessRuleError(f"Programme staff {what}; the award manager decides.")
    check_can_work_on(user, award)


def _check_manager_of(user, award, what):
    if user.role != User.Role.MANAGER or award.manager_id != user.pk:
        manager = active_manager(award)
        raise BusinessRuleError(f"The award manager{f' ({manager.display_name})' if manager else ''} {what} "
                                f"for {award.name}.")


# --- Form approval: staff draft, the manager publishes -------------------------------------

def draft_of(award):
    """The award's unpublished form version (being edited, waiting, or sent back), or None."""
    return award.form_versions.filter(published_at__isnull=True).order_by("-version").first()


@transaction.atomic
def save_form_draft(award, questions, *, by):
    """
    Staff save the questions as the next version and send it to the award manager. Saving
    again replaces the draft (it isn't published, so nothing uses it yet). Returns the version;
    it is already published when the award has no active manager.
    """
    from .services import publish_form_version

    _check_staff_on(by, award, "build the application form")
    manager = active_manager(award)
    if manager is None:
        stale = draft_of(award)
        if stale is not None:            # a draft sent before the manager left: publish the new questions instead
            stale.delete()
        return publish_form_version(award, questions, by)
    if not questions:
        raise BusinessRuleError("A form needs at least one question.")
    keys = [q.get("key") for q in questions]
    if len(keys) != len(set(keys)) or not all(keys):
        raise BusinessRuleError("Every question needs a unique key.")
    draft = draft_of(award)
    if draft is None:
        latest = award.form_versions.order_by("-version").first()
        draft = FormVersion(award=award, version=latest.version + 1 if latest else 1)
    draft.questions = questions
    draft.submitted_by, draft.submitted_at = by, timezone.now()
    draft.reviewed_by, draft.review_note = None, ""
    draft.save()
    record(by, "update", draft, changes={"questions": len(questions), "sent_to": manager.email})
    notify(manager, f"{award.name}: {by.display_name} sent form version {draft.version} for you to approve.",
           kind=Notification.Kind.REQUEST, link=reverse("awards:form_builder", args=[award.slug]))
    return draft


@transaction.atomic
def review_form_draft(draft, *, by, approve, note=""):
    """The award manager publishes the waiting draft, or sends it back to staff with a note."""
    award = draft.award
    _check_manager_of(by, award, "approves the application form")
    if not draft.waiting_for_manager:
        raise BusinessRuleError("This form version isn't waiting for approval.")
    note = (note or "").strip()
    if not approve and not note:
        raise BusinessRuleError("Say what needs changing: staff see your note.")
    draft.reviewed_by, draft.review_note = by, note
    if approve:
        draft.published_at = timezone.now()
    else:
        draft.submitted_at = None        # back to staff: they change it and send it again
    draft.save()
    record(by, "update", draft, changes={"published" if approve else "sent_back": True, "note": note})
    if draft.submitted_by:
        message = (f"{award.name}: form version {draft.version} approved and published. New applications use it."
                   if approve else f"{award.name}: form version {draft.version} sent back by the award manager. "
                                   f"{note}")
        notify(draft.submitted_by, message, kind=Notification.Kind.STATUS_CHANGE,
               link=reverse("awards:form_builder", args=[award.slug]))
    return draft


def forms_waiting(user):
    """Form drafts waiting for this award manager."""
    return (FormVersion.objects.filter(award__manager=user, published_at__isnull=True, submitted_at__isnull=False)
            .select_related("award", "submitted_by").order_by("submitted_at"))


# --- Escalations: staff ask, the manager answers ------------------------------------------

@transaction.atomic
def escalate(award, *, by, question, application=None):
    _check_staff_on(by, award, "pass cases to the award manager")
    if application is not None and application.award_id != award.pk:
        raise BusinessRuleError("That entry isn't in this award.")
    question = (question or "").strip()
    if not question:
        raise BusinessRuleError("Say what you need the award manager to decide.")
    manager = active_manager(award)
    if manager is None:
        raise BusinessRuleError(f"{award.name} has no award manager to ask. A leader can choose one.")
    escalation = Escalation.objects.create(award=award, application=application, raised_by=by, question=question)
    record(by, "create", escalation, changes={"application": getattr(application, "reference", None)})
    about = f" about {application.reference}" if application else ""
    notify(manager, f"{award.name}: {by.display_name} needs your decision{about}. {question}"[:500],
           kind=Notification.Kind.REQUEST, link=reverse("awards:escalations"))
    return escalation


@transaction.atomic
def answer_escalation(escalation, *, by, answer):
    _check_manager_of(by, escalation.award, "answers escalations")
    if escalation.status != Escalation.Status.OPEN:
        raise BusinessRuleError("This case has already been answered.")
    answer = (answer or "").strip()
    if not answer:
        raise BusinessRuleError("Write your decision: staff act on it.")
    escalation.status, escalation.answer = Escalation.Status.ANSWERED, answer
    escalation.answered_by, escalation.answered_at = by, timezone.now()
    escalation.save()
    record(by, "update", escalation, changes={"status": escalation.status})
    about = f" about {escalation.application.reference}" if escalation.application else ""
    notify(escalation.raised_by, f"{escalation.award.name}: the award manager answered{about}. {answer}"[:500],
           kind=Notification.Kind.STATUS_CHANGE, link=reverse("awards:escalations"))
    return escalation


def escalations_for(user):
    """Cases on this person's awards (staff: every case on their awards; the manager: their awards)."""
    from .access import awards_for
    return (Escalation.objects.filter(award__in=awards_for(user))
            .select_related("award", "application", "raised_by", "answered_by"))


# --- Allocation: the manager gives entries to named staff ----------------------------------

@transaction.atomic
def allocate(application, *, by, staff_member):
    """The award manager gives an entry to one of the award's staff (None: back to anyone on the staff)."""
    award = application.award
    _check_manager_of(by, award, "decides who handles each entry")
    if staff_member is not None and not award.staff.filter(pk=staff_member.pk, is_active=True).exists():
        raise BusinessRuleError(f"{staff_member.display_name} isn't on the {award.name} staff.")
    before = application.handled_by
    if before == staff_member:
        return application
    application.handled_by = staff_member
    application.save(update_fields=["handled_by", "updated_at"])
    record(by, "update", application, changes={"handled_by": {"from": getattr(before, "email", None),
                                                              "to": getattr(staff_member, "email", None)}})
    if staff_member is not None:
        notify(staff_member, f"{application.reference} ({award.name}): the award manager gave this entry to you.",
               kind=Notification.Kind.ASSIGNMENT, link=reverse("awards:entries") + "?mine=1")
    return application


def workload(award):
    """Each active staff member on the award with how many open entries they hold, plus the unallocated ones."""
    from apps.applications.models import Application

    open_entries = Application.objects.filter(award=award, status__in=OPEN_WORK)
    counts = dict(open_entries.exclude(handled_by=None).values_list("handled_by")
                  .annotate(n=Count("id")).values_list("handled_by", "n"))
    rows = [{"user": s, "open": counts.get(s.pk, 0)} for s in award.staff.filter(is_active=True).order_by("name")]
    return {"rows": rows, "unallocated": open_entries.filter(Q(handled_by=None) | Q(handled_by__is_active=False)
                                                             | ~Q(handled_by__in=award.staff.all())).count()}


def team_workload(user):
    """The manager's home page: workload for each award they manage."""
    return [{"award": a, **workload(a)} for a in Award.objects.filter(manager=user).order_by("name")]
