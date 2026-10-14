"""The notifications page: every logged-in user sees only their own."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification
from .services import mark_all_read, mark_read


@login_required
def inbox(request):
    notes = Notification.objects.filter(user=request.user)[:100]
    return render(request, "notifications/inbox.html", {"role": request.user.role, "notes": notes})


@login_required
@require_POST
def open_note(request, pk):
    """Mark one as read, then go to the page it points at (only links inside this site)."""
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    mark_read(note)
    safe = url_has_allowed_host_and_scheme(note.link, allowed_hosts={request.get_host()})
    return redirect(note.link if note.link and safe else "notifications:inbox")


@login_required
@require_POST
def read_all(request):
    mark_all_read(request.user)
    return redirect("notifications:inbox")
