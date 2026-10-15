"""
Duplicate organisations: finding them, and staff deciding what they are.

The same company can register twice (two people, two logins, a GSTIN per
state, "Pvt Ltd" vs "Private Limited"). Then a judge's recorded conflict with
one record would miss the other.                                   [Rule 2]

  find   scan(): compare profiles and store pairs as DuplicateCandidate
           high      same PAN (GSTIN characters 3-12), or the same name once cleaned
           possible  similar name (SIMILAR or more)
  show   candidates_for(user): staff see a pair when either organisation has an
         entry in one of their awards (Duplicate review is a programme-staff page). On the review screen
         a pair is listed under an award only when both entered it (award_ids)
  decide merge(): the duplicate points at the main profile (merged_into). Both
         logins and entries stay; conflicts and verification follow the main
         profile. Blocked while both have an active entry in the same award:
         staff decline one first. keep_separate(). undo() reopens either.

The system never merges on its own. Only programme staff decide. Every decision is audited.
"""
import re
from difflib import SequenceMatcher

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services import record
from apps.core.services import BusinessRuleError

from .models import ApplicantProfile, DuplicateCandidate, User

SIMILAR = 0.80
LEGAL_WORDS = {"pvt", "private", "ltd", "limited", "llp", "inc", "co", "company", "corp", "corporation",
               "the", "india", "ms"}
C = DuplicateCandidate


# --- Comparing ---------------------------------------------------------------------

def clean_name(name):
    """'COASTAL MARINE FOODS PVT. LTD.' → 'coastal marine foods'."""
    words = re.sub(r"[^a-z0-9]+", " ", (name or "").lower().replace("&", " and ")).split()
    return " ".join(w for w in words if w not in LEGAL_WORDS)


def pan_of(profile):
    """The organisation's PAN: given directly, or characters 3-12 of the GSTIN."""
    return (profile.holder_pan or profile.gstin[2:12]).upper()


def compare(a, b):
    """(score, level, reason) if a and b look like the same organisation, else None."""
    reasons = []
    if pan_of(a) and pan_of(a) == pan_of(b):
        reasons.append("Same PAN in the GSTIN")
    name_a, name_b = clean_name(a.organisation_name), clean_name(b.organisation_name)
    if name_a and name_a == name_b:
        reasons.append("Same name once 'Pvt Ltd' and punctuation are removed")
    if reasons:
        return 1, C.Level.HIGH, "; ".join(reasons)
    score = round(SequenceMatcher(None, name_a, name_b).ratio(), 2) if name_a and name_b else 0
    if score >= SIMILAR:
        return score, C.Level.POSSIBLE, "Similar name, different PAN"
    return None


def scan(profile=None):
    """
    Store new pairs (one profile against all others, or every pair). Pairs staff
    already decided are left alone; open ones get a fresh score. Returns how many were new.
    """
    profiles = list(ApplicantProfile.objects.all())
    targets = [profile] if profile is not None else profiles
    new = 0
    for p in targets:
        for q in profiles:
            if q.pk == p.pk or (profile is None and q.pk < p.pk) or root(q).pk == root(p).pk:
                continue
            a, b = sorted([p, q], key=lambda x: x.pk)
            found = compare(a, b)
            existing = C.objects.filter(profile_a=a, profile_b=b).first()
            if found is None:
                if existing and existing.status == C.Status.OPEN:    # a name was corrected: no longer alike
                    existing.delete()
                continue
            score, level, reason = found
            if existing is None:
                C.objects.create(profile_a=a, profile_b=b, score=score, level=level, reason=reason)
                new += 1
            elif existing.status == C.Status.OPEN:
                existing.score, existing.level, existing.reason = score, level, reason
                existing.save(update_fields=["score", "level", "reason", "updated_at"])
    return new


# --- Merged groups -------------------------------------------------------------------

def root(profile):
    """The main profile this one was merged into (itself if it wasn't)."""
    seen = set()
    while profile.merged_into_id and profile.pk not in seen:
        seen.add(profile.pk)
        profile = profile.merged_into
    return profile


def group(profile):
    """Every profile of the same organisation: the main one and everything merged into it."""
    top = root(profile)
    members, frontier = [top], [top]
    while frontier:
        frontier = list(ApplicantProfile.objects.filter(merged_into__in=frontier))
        members += frontier
    return members


def group_ids(profile):
    return [p.pk for p in group(profile)]


def is_verified(profile):
    """Verification follows the main profile after a merge."""
    return bool(profile) and root(profile).verification_status == ApplicantProfile.Verification.VERIFIED


# --- Entries and visibility ------------------------------------------------------------

def entries_of(profiles):
    from apps.applications.models import Application
    return Application.objects.filter(applicant__applicant_profile__in=profiles).select_related("award")


def active_entries(profiles):
    """Entries still in play (not drafts, not declined)."""
    from apps.applications.models import Application
    return entries_of(profiles).exclude(status__in=[Application.Status.DRAFT, Application.Status.REJECTED])


def award_ids(candidate):
    """Awards BOTH organisations have an entry in (drafts included): where the pair really clashes."""
    # Each record's own entries, not its merged group's: after a merge both records are in one group.
    a = set(entries_of([candidate.profile_a]).values_list("award_id", flat=True))
    b = set(entries_of([candidate.profile_b]).values_list("award_id", flat=True))
    return a & b


def candidates_for(user, *, status=None):
    """The pairs this person may see: leaders all; staff and managers those touching their awards."""
    from apps.applications.models import Application
    from apps.awards.access import awards_for, sees_every_award

    qs = C.objects.select_related("profile_a__user", "profile_b__user", "decided_by")
    if status:
        qs = qs.filter(status=status)
    if sees_every_award(user):
        return qs
    users = Application.objects.filter(award__in=awards_for(user)).values("applicant")
    return qs.filter(Q(profile_a__user__in=users) | Q(profile_b__user__in=users))


def merge_blockers(candidate):
    """[(award, entries of A, entries of B)] where both organisations have an active entry."""
    side_a, side_b = active_entries(group(candidate.profile_a)), active_entries(group(candidate.profile_b))
    shared = set(side_a.values_list("award_id", flat=True)) & set(side_b.values_list("award_id", flat=True))
    rows = []
    for award_id in sorted(shared):
        a = [e for e in side_a if e.award_id == award_id]
        b = [e for e in side_b if e.award_id == award_id]
        rows.append((a[0].award, a, b))
    return rows


def open_duplicate_in_award(profile, award):
    """
    An undecided HIGH match for this organisation whose other side also entered this award.
    Possible matches (only a similar name, e.g. "Plant 1" and "Plant 2") are flagged, not blocking.
    """
    from apps.applications.models import Application
    ids = group_ids(profile)
    for candidate in C.objects.filter(Q(profile_a_id__in=ids) | Q(profile_b_id__in=ids), status=C.Status.OPEN,
                                      level=C.Level.HIGH):
        other = candidate.profile_b if candidate.profile_a_id in ids else candidate.profile_a
        if (Application.objects.filter(award=award, applicant__applicant_profile__in=group(other))
                .exclude(status=Application.Status.REJECTED).exists()):
            return candidate
    return None


# --- Decisions -----------------------------------------------------------------------

def _check_can_decide(candidate, by):
    if by.role != User.Role.STAFF:
        raise BusinessRuleError("Programme staff decide duplicates (on Duplicate review).")
    if not candidates_for(by).filter(pk=candidate.pk).exists():
        raise BusinessRuleError("Neither organisation has an entry in an award you work on.")


def _decided(candidate, by, status, note, merged=None):
    candidate.status, candidate.decided_by, candidate.decided_at = status, by, timezone.now()
    candidate.note, candidate.merged_profile = note, merged
    candidate.save()


@transaction.atomic
def merge(candidate, *, by, keep, note=""):
    """Merge the other profile into `keep` (the record to keep as the main one)."""
    _check_can_decide(candidate, by)
    if candidate.status != C.Status.OPEN:
        raise BusinessRuleError("This pair has already been decided. Undo that first.")
    if keep.pk not in (candidate.profile_a_id, candidate.profile_b_id):
        raise BusinessRuleError("Choose one of the two organisations to keep.")
    blockers = merge_blockers(candidate)
    if blockers:
        award, a, b = blockers[0]
        raise BusinessRuleError(
            f"Both organisations have an entry in {award.name} ({a[0].reference} and {b[0].reference}). "
            f"One organisation can only enter once: decline one of the entries first, then merge.")
    other = candidate.profile_b if keep.pk == candidate.profile_a_id else candidate.profile_a
    main, moving = root(keep), root(other)
    if main.pk == moving.pk:
        raise BusinessRuleError("These are already the same organisation.")
    moving.merged_into = main
    moving.save(update_fields=["merged_into", "updated_at"])
    _decided(candidate, by, C.Status.MERGED, note, merged=moving)
    record(by, "update", moving, changes={"merged_into": main.pk, "organisation": main.organisation_name,
                                          "note": note})
    record(by, "update", candidate, changes={"status": C.Status.MERGED, "kept": main.organisation_name})
    return candidate


@transaction.atomic
def keep_separate(candidate, *, by, note=""):
    _check_can_decide(candidate, by)
    if candidate.status != C.Status.OPEN:
        raise BusinessRuleError("This pair has already been decided. Undo that first.")
    _decided(candidate, by, C.Status.SEPARATE, note)
    record(by, "update", candidate, changes={"status": C.Status.SEPARATE, "note": note})
    return candidate


@transaction.atomic
def undo(candidate, *, by):
    """Reopen a decided pair. Undoing a merge makes the two organisations separate records again."""
    _check_can_decide(candidate, by)
    if candidate.status == C.Status.OPEN:
        raise BusinessRuleError("This pair hasn't been decided yet.")
    before = candidate.status
    if before == C.Status.MERGED and candidate.merged_profile_id:
        moved = candidate.merged_profile
        moved.merged_into = None
        moved.save(update_fields=["merged_into", "updated_at"])
        record(by, "update", moved, changes={"merged_into": None, "why": "merge undone"})
    _decided(candidate, by, C.Status.OPEN, "")
    candidate.decided_by = candidate.decided_at = None
    candidate.save(update_fields=["decided_by", "decided_at", "updated_at"])
    record(by, "update", candidate, changes={"status": {"from": before, "to": C.Status.OPEN}})
    return candidate
