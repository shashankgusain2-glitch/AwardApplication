"""Leadership: one dashboard of the whole event (read-only)."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.awards.models import Award
from apps.core.models import ActivityLog
from apps.entries.models import Application
from apps.judging.models import JudgeProfile, ScoreChangeRequest

S = Application.Status


def leader_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_leader or request.user.is_superuser):
            messages.error(request, "That page is for leadership.")
            return redirect("core:home")
        return view(request, *args, **kwargs)
    return wrapper


@leader_required
def overview(request):
    events = []
    for award in Award.objects.all():
        apps = award.applications.exclude(status=S.DRAFT).select_related("organisation")
        count = lambda *statuses: apps.filter(status__in=statuses).count()  # noqa: E731
        ranked = [a for a in apps if a.status in (S.JUDGED, S.SHORTLISTED, S.ROUND2_DONE)]
        ranked.sort(key=lambda a: (a.round2_average or 0, a.round1_average or 0), reverse=True)
        events.append({
            "award": award,
            "drafts": award.applications.filter(status=S.DRAFT).count(),
            "submitted": count(S.SUBMITTED),
            "pool": count(S.POOL),
            "evaluating": count(S.ASSIGNED, S.JUDGING),
            "judged": count(S.JUDGED),
            "round2": count(S.SHORTLISTED, S.ROUND2_DONE),
            "rejected": count(S.REJECTED),
            "ranking": ranked[:10],
        })
    return render(request, "dashboard/overview.html", {
        "events": events,
        "judges": JudgeProfile.objects.all(),
        "edit_requests": Application.objects.filter(edit_request=Application.EditRequest.REQUESTED).count(),
        "score_requests": ScoreChangeRequest.objects.filter(status="requested").count(),
        "activity": ActivityLog.objects.select_related("actor", "application__organisation")[:15],
    })
