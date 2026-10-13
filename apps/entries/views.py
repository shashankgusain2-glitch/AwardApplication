"""
Applicant workflow (12 Oct meeting):

  register organisation → events → form (save midway) → submit
  → staff check → status → request edit → staff confirm → edit and resubmit
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.awards.models import Award
from apps.core.models import log

from .forms import EditRequestForm, OrganisationForm, application_form
from .models import Application


def organisation_required(view):
    """Logged in AND has registered an organisation; otherwise send them to the right step."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "organisation"):
            return redirect("entries:register")
        return view(request, *args, **kwargs)
    return wrapper


@login_required
@require_http_methods(["GET", "POST"])
def register(request):
    if hasattr(request.user, "organisation"):
        return redirect("entries:events")
    form = OrganisationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        organisation = form.save(commit=False)
        organisation.owner = request.user
        organisation.save()
        messages.success(request, f"{organisation.name} is registered. Choose an event to apply.")
        return redirect("entries:events")
    return render(request, "entries/register.html", {"form": form})


@organisation_required
def events(request):
    mine = {a.award_id: a for a in request.user.organisation.applications.all()}
    awards = [{"award": award, "application": mine.get(award.id)} for award in Award.objects.filter(is_open=True)]
    return render(request, "entries/events.html", {"events": awards})


@organisation_required
@require_POST
def start(request, slug):
    award = get_object_or_404(Award, slug=slug, is_open=True)
    application, created = Application.objects.get_or_create(
        organisation=request.user.organisation,
        award=award,
        defaults={"form_version": award.current_form},
    )
    return redirect("entries:application", pk=application.pk)


@organisation_required
@require_http_methods(["GET", "POST"])
def application(request, pk):
    app = get_object_or_404(Application, pk=pk, organisation=request.user.organisation)
    questions = app.form_version.questions

    if request.method == "POST" and app.can_edit:
        submitting = request.POST.get("action") == "submit"
        form = application_form(questions, data=request.POST, require_all=submitting)
        if form.is_valid():
            app.answers = {k: v for k, v in form.cleaned_data.items() if v not in (None, "")}
            if submitting:
                first_time = app.status == Application.Status.DRAFT
                if first_time:
                    # Staff check it before it joins the report pool.
                    app.status = Application.Status.SUBMITTED
                    app.submitted_at = timezone.now()
                app.edit_request = Application.EditRequest.NONE
                app.edit_reason = ""
                log(request.user, "Submitted the report" if first_time else "Resubmitted after an approved edit", app)
                messages.success(request, "Submitted. Staff will check it, then it joins the report pool."
                                 if first_time else "Changes submitted. Your report is locked again.")
            else:
                messages.success(request, "Saved. You can come back and finish later.")
            app.save()
            return redirect("entries:application", pk=app.pk)
    else:
        form = application_form(questions, initial=app.answers, disabled=not app.can_edit)

    return render(request, "entries/application.html", {
        "app": app,
        "form": form,
        "edit_form": EditRequestForm(),
    })


@organisation_required
@require_POST
def request_edit(request, pk):
    app = get_object_or_404(Application, pk=pk, organisation=request.user.organisation)
    form = EditRequestForm(request.POST)
    if app.can_request_edit and form.is_valid():
        app.edit_request = Application.EditRequest.REQUESTED
        app.edit_reason = form.cleaned_data["reason"]
        app.save()
        log(request.user, f"Asked staff to allow changes: {app.edit_reason}", app)
        messages.success(request, "Request sent. Staff will confirm before you can make changes.")
    return redirect("entries:application", pk=app.pk)


