"""
Leadership screens, on the real database. Leaders see everything and
approve results; they never change scores (that is the judges' job, with
staff permission: Rule 3).
"""
from datetime import date
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.accounts.permissions import role_required
from apps.applications import services as application_services
from apps.applications.models import Application
from apps.audit.models import AuditLog
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


@role_required("leader")
def results(request):
    """Scored reports waiting for a decision, best first, with every judge's total."""
    reports = _with_scores(application_services.visible_to(request.user)
                           .filter(status=Application.Status.SCORED)
                           .select_related("applicant__applicant_profile")).order_by("award__name", "-average")
    rows = []
    for report in reports:
        evaluations = Evaluation.objects.filter(assignment__report=report, status=Evaluation.Status.SUBMITTED) \
            .select_related("assignment__judge").order_by("assignment__round")
        rows.append({"report": report, "evaluations": evaluations,
                     "spread": (report.highest - report.lowest) if report.highest is not None else None})
    decided = application_services.visible_to(request.user).filter(
        status__in=[Application.Status.APPROVED, Application.Status.REJECTED]).order_by("-updated_at")[:20]
    return render(request, "dashboard/results.html", {"role": ROLE, "rows": rows, "decided": decided})


@role_required("leader")
@require_POST
def decide(request, pk):
    """Approve or reject a scored result. Goes through the same rule as the API (leaders approve)."""
    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    new_status = Application.Status.APPROVED if request.POST.get("decision") == "approve" \
        else Application.Status.REJECTED
    try:
        application_services.change_status(report, by=request.user, new_status=new_status,
                                           note=request.POST.get("note", ""))
        messages.success(request, f"{report.reference}: {report.get_status_display().lower()}.")
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


# --- Audit log viewer -----------------------------------------------------------------

@role_required("leader")
def audit(request):
    """Who did what, to which record, and when (read-only: entries can never change)."""
    entries = AuditLog.objects.select_related("user").order_by("-timestamp")
    filters = {k: request.GET.get(k, "").strip() for k in ("who", "action", "entity", "since")}
    if filters["who"]:
        entries = entries.filter(Q(user__email__icontains=filters["who"]) | Q(user__name__icontains=filters["who"]))
    if filters["action"] in AuditLog.Action.values:
        entries = entries.filter(action=filters["action"])
    if filters["entity"]:
        entries = entries.filter(entity=filters["entity"])
    if filters["since"]:
        try:
            entries = entries.filter(timestamp__date__gte=date.fromisoformat(filters["since"]))
        except ValueError:
            messages.error(request, "Use a date like 2026-10-14.")
    page = Paginator(entries, 50).get_page(request.GET.get("page"))
    return render(request, "dashboard/audit.html", {
        "role": ROLE, "page": page, "filters": filters, "actions": AuditLog.Action.choices,
        "entities": AuditLog.objects.order_by().values_list("entity", flat=True).distinct(),
        "querystring": urlencode({k: v for k, v in filters.items() if v}),
    })


@role_required("leader")
def requests_to_confirm(request):
    """Requests staff have checked, waiting for a leader's final confirmation (or refusal)."""
    from apps.core import approvals
    return render(request, "dashboard/requests.html", {
        "role": ROLE,
        "rows": approvals.for_leaders(approvals.waiting(approvals.T.WAITING_LEADER)),
        "with_staff": approvals.for_leaders(approvals.waiting(approvals.T.WAITING_STAFF)),
    })
