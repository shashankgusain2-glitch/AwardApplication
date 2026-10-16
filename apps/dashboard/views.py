"""
Leadership screens, on the real database. Leaders see everything and
approve results; they never change scores (that is the judges' job, with
staff permission: Rule 3).
"""

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.accounts.permissions import role_required
from apps.applications.models import Application
from apps.awards.models import Award
from apps.core import overview as summaries
from apps.core.services import BusinessRuleError
from apps.evaluations.models import Evaluation

ROLE = "leader"
SUBMITTED = Q(assignments__evaluation__status=Evaluation.Status.SUBMITTED) & ~Q(assignments__status="superseded")


def _with_scores(reports):
    """Average, lowest and highest submitted total per report, and how many judges have submitted."""
    return reports.annotate(
        average=Avg("assignments__evaluation__total_score", filter=SUBMITTED),
        lowest=Min("assignments__evaluation__total_score", filter=SUBMITTED),
        highest=Max("assignments__evaluation__total_score", filter=SUBMITTED),
        judged=Count("assignments__evaluation", filter=SUBMITTED, distinct=True),
    )


@role_required("leader")
def overview(request):
    """Home page: the whole event at a glance, from the database."""
    return render(request, "dashboard/overview.html", {"role": ROLE, **summaries.leader_overview()})


@role_required("leader")
def awards(request):
    """Every award with who runs it (manager and staff). Leaders create awards here and choose their teams."""
    rows = (Award.objects.select_related("manager").prefetch_related("staff", "judge_panel")
            .annotate(entries=Count("applications", filter=Q(applications__is_deleted=False)
                                    & ~Q(applications__status=Application.Status.DRAFT), distinct=True))
            .order_by("name"))
    return render(request, "dashboard/awards.html", {
        "role": ROLE, "awards": rows,
        "without_manager": sum(1 for a in rows if a.manager is None or not a.manager.is_active),
    })


def _ranking(award, published=None):
    """The award's decided entries, best first, with the judges' average (what the leader approves)."""
    reports = Application.objects.filter(award=award, status__in=[Application.Status.APPROVED,
                                                                 Application.Status.REJECTED])
    if published is not None:
        reports = reports.filter(result_published=published)
    reports = _with_scores(reports.select_related("applicant__applicant_profile")).filter(judged__gt=0)
    return sorted(reports, key=lambda r: (r.status != Application.Status.APPROVED, -(r.average or 0), r.reference))


@role_required("leader")
def results(request):
    """
    Approve each award's result as a whole. The award manager decides every entry and sends the
    award's result; a leader approves it (published: the results board, applicants told) or sends
    it back with a note. Leaders don't decide single applications.
    """
    from apps.awards import results as award_results

    waiting = []
    for award in Award.objects.filter(results_status=Award.Results.SUBMITTED).select_related(
            "manager", "results_submitted_by").order_by("results_submitted_at"):
        rows = _ranking(award, published=False)
        waiting.append({"award": award, "rows": rows,
                        "successful": sum(r.status == Application.Status.APPROVED for r in rows),
                        "already_published": Application.objects.filter(award=award, result_published=True).count()})
    others = Award.objects.exclude(results_status=Award.Results.SUBMITTED).select_related("manager",
                                                                              "results_decided_by")
    progress = [{"award": a, "state": award_results.state(a)} for a in others.order_by("name")]
    return render(request, "dashboard/results.html", {"role": ROLE, "waiting": waiting, "progress": progress,
                                                      "focus": request.GET.get("award", "")})


@role_required("leader")
@require_POST
def decide_award(request, slug):
    """Approve an award's result, or send it back to the award manager with a note."""
    from apps.awards import results as award_results

    award = get_object_or_404(Award, slug=slug)
    note = request.POST.get("note", "")
    try:
        if request.POST.get("decision") == "approve":
            award_results.approve(award, by=request.user, note=note)
            messages.success(request, f"{award.name}: result approved. It is on the results board and every "
                                      f"applicant has been told.")
        else:
            award_results.send_back(award, by=request.user, note=note)
            messages.success(request, f"{award.name}: sent back to {award_results.preparer_label(award)}.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return redirect("dashboard:results")


# --- People: leaders create and manage staff, judge and leader accounts -------------

STAFF_ROLES = [(r, label) for r, label in User.Role.choices if r != User.Role.APPLICANT]   # applicants sign up


def _number(raw, default):
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() else default


def _show_link(request, person, link):
    """While email isn't set up (SHOW_INVITE_LINKS), show the leader the link to pass on by hand."""
    if settings.SHOW_INVITE_LINKS:
        messages.info(request, f"Email may not be set up yet: send {person.email} this one-time link yourself: {link}")


@role_required("leader")
@require_http_methods(["GET", "POST"])
def people(request):
    """Everyone with an account; leaders add staff, judges and leaders (they get an invite email)."""
    if request.method == "POST":
        role = request.POST.get("role", "")
        if role not in dict(STAFF_ROLES):
            messages.error(request, "Choose staff, award manager, judge or leader. Applicants sign up themselves.")
            return redirect("dashboard:people")
        email = request.POST.get("email", "").strip().lower()
        name = request.POST.get("name", "").strip()
        judge_fields = {}
        if role == User.Role.JUDGE:
            judge_fields = {"expertise": request.POST.get("expertise", "").strip(),
                            "priority": min(max(_number(request.POST.get("priority"), 5), 1), 99),
                            "max_open_assignments": max(_number(request.POST.get("max_open_assignments"), 10), 1)}
        try:
            if not name:
                raise BusinessRuleError("Give the person's name.")
            validate_email(email)
            with transaction.atomic():
                user = account_services.create_account(created_by=request.user, email=email, name=name,
                                                       role=role, **judge_fields)
                link = account_services.invite(user, by=request.user)
        except ValidationError:
            messages.error(request, "Enter a valid email address.")
        except BusinessRuleError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"{user.display_name} ({user.get_role_display()}) added. "
                                      f"An email with a set-your-password link was sent to {user.email}.")
            _show_link(request, user, link)
        return redirect("dashboard:people")

    users = User.objects.prefetch_related("managed_awards", "staff_awards").order_by("role", "name", "email")
    role, query = request.GET.get("role", ""), request.GET.get("q", "").strip()
    if role in User.Role.values:
        users = users.filter(role=role)
    if query:
        users = users.filter(Q(email__icontains=query) | Q(name__icontains=query))
    return render(request, "dashboard/people.html", {
        "role": ROLE, "people": users[:300], "roles": User.Role.choices, "new_roles": STAFF_ROLES,
        "filters": {"role": role, "q": query},
    })


@role_required("leader")
@require_POST
def person_action(request, pk):
    person = get_object_or_404(User, pk=pk)
    action = request.POST.get("action")
    try:
        if action == "deactivate":
            account_services.set_active(person, by=request.user, active=False)
            messages.success(request, f"{person.display_name} can no longer log in. Their history is kept.")
        elif action == "activate":
            account_services.set_active(person, by=request.user, active=True)
            messages.success(request, f"{person.display_name} can log in again.")
        elif action == "invite":
            if person.role == User.Role.APPLICANT:
                raise BusinessRuleError("Applicants reset their own password from the login page.")
            link = account_services.invite(person, by=request.user)
            messages.success(request, f"A new set-your-password link was sent to {person.email}.")
            _show_link(request, person, link)
        else:
            raise BusinessRuleError("Unknown action.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return redirect("dashboard:people")
