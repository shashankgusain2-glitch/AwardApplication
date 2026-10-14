"""
Uploaded files (evidence) on an application's file questions.

Rules:
- Only the applicant uploads, only to their own application, only while it
  can be edited, and only on a question of type "file".
- PDF, JPG or PNG up to 10 MB. The file's first bytes must really be that
  type: a renamed .exe doesn't get in.
- One file per question: uploading again replaces the old file.
- Who may download: the applicant who owns it, staff and leaders, and judges
  with a live (not declined) assignment on that report. On a blind round the
  judge gets a neutral file name, because file names often name the company.  [Rule 1]
"""
import os

from django.db import transaction

from apps.accounts.models import User
from apps.assignments.models import JudgeAssignment
from apps.audit.services import record
from apps.core.services import BusinessRuleError

from .models import MAX_ATTACHMENT_BYTES, Attachment
from .services import can_edit

# extension → (content type, the bytes a real file of that type starts with)
FILE_TYPES = {
    ".pdf": ("application/pdf", (b"%PDF",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
}


def _file_question(application, key):
    question = next((q for q in application.form_version.questions if q["key"] == key), None)
    if question is None or question.get("type") != "file":
        raise BusinessRuleError("That question doesn't take a file.")
    return question


def _check(upload):
    name = os.path.basename(upload.name or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in FILE_TYPES:
        raise BusinessRuleError("Upload a PDF, JPG or PNG file.")
    if upload.size > MAX_ATTACHMENT_BYTES:
        raise BusinessRuleError("The file is bigger than 10 MB.")
    if upload.size == 0:
        raise BusinessRuleError("The file is empty.")
    content_type, signatures = FILE_TYPES[ext]
    head = upload.read(16)
    upload.seek(0)
    if not any(head.startswith(sig) for sig in signatures):
        raise BusinessRuleError(f"{name} isn't really a {ext[1:].upper()} file.")
    return name[:255], content_type


@transaction.atomic
def attach(application, *, by, question_key, upload):
    """Save the applicant's file for one file question (replacing an earlier one)."""
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only add files to your own application.")
    if not can_edit(application):
        raise BusinessRuleError("This application is submitted. Ask staff to allow changes first.")
    _file_question(application, question_key)
    name, content_type = _check(upload)
    for old in application.attachments.filter(question_key=question_key):
        old.file.delete(save=False)
        old.delete()
    attachment = Attachment.objects.create(application=application, question_key=question_key, file=upload,
                                           original_name=name, size_bytes=upload.size,
                                           content_type=content_type, uploaded_by=by)
    application.content = {**application.content, question_key: name}
    application.save(update_fields=["content", "updated_at"])
    record(by, "update", application, changes={"file": question_key, "name": name, "bytes": upload.size})
    return attachment


def visible_to(user):
    """Attachments this user may download."""
    qs = Attachment.objects.select_related("application__award", "application__form_version")
    if user.role == User.Role.APPLICANT:
        return qs.filter(application__applicant=user, application__is_deleted=False)
    if user.role in (User.Role.STAFF, User.Role.LEADER):
        return qs
    if user.role == User.Role.JUDGE:
        live = JudgeAssignment.objects.filter(judge=user).exclude(status=JudgeAssignment.Status.DECLINED)
        return qs.filter(application__in=live.values("report"))
    return qs.none()


def download_name(attachment, user):
    """The file name this user sees. Judges on a blind round get a neutral name."""
    if user.role == User.Role.JUDGE:
        from apps.assignments.services import report_for_judge
        assignment = (JudgeAssignment.objects.filter(judge=user, report=attachment.application)
                      .exclude(status=JudgeAssignment.Status.DECLINED).order_by("round").first())
        if assignment and report_for_judge(assignment)["blind"]:
            ext = os.path.splitext(attachment.original_name)[1]
            return f"{attachment.application.reference}-{attachment.question_key}{ext}"
    return attachment.original_name
