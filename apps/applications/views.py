"""Downloading an uploaded file (any logged-in role that may see it; everyone else gets 404)."""
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from . import files


@login_required
def download(request, pk):
    attachment = get_object_or_404(files.visible_to(request.user), pk=pk)
    return FileResponse(attachment.file.open("rb"), as_attachment=True,
                        filename=files.download_name(attachment, request.user),
                        content_type=attachment.content_type)
