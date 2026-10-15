"""
Duplicate organisations (apps/accounts/duplicates.py and Duplicate review, /staff/duplicates/):
found automatically, listed per award, merged or kept separate by staff, and undoable.
"""
import re

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts import duplicates
from apps.accounts.models import ApplicantProfile, DuplicateCandidate
from apps.accounts.services import register_applicant
from apps.applications import services as applications
from apps.applications.models import Application
from apps.core.overview import organisations_to_verify
from apps.core.services import BusinessRuleError

from .conftest import login as web_login
from .factories import PASSWORD, ApplicantProfileFactory, ApplicationFactory, AwardFactory, LeaderFactory, StaffFactory

C = DuplicateCandidate


def profile(name, gstin, verified=True):
    return ApplicantProfileFactory(organisation_name=name, gstin=gstin, holder_pan="",
                                   verification_status="verified" if verified else "pending")


@pytest.mark.parametrize("a,b,level", [
    (("Shri Ganesh Polymers Ltd", "24ABCDE1234F1Z3"), ("Totally Other Name", "27ABCDE1234F1Z9"), "high"),  # same PAN
    (("Coastal Marine Foods", "32AAAAA0003A1Z1"), ("COASTAL MARINE FOODS PVT. LTD.", "32BBBBB0003B1Z5"), "high"),
    (("Vertex Pharma Labs", "36AAAAA0004A1Z9"), ("Vertex Pharma Laboratories", "36CCCCC0004C1Z3"), "possible"),
    (("Acme Precision Components", "27AAAAA0001A1Z5"), ("Northstar Auto Components", "29AAAAA0005A1Z7"), None),
])
@pytest.mark.django_db
def test_detection(a, b, level):
    first, second = profile(*a), profile(*b)
    found = duplicates.compare(first, second)
    assert (found[1] if found else None) == level


def test_clean_name_drops_legal_words_and_punctuation():
    assert duplicates.clean_name("COASTAL MARINE FOODS PVT. LTD.") == "coastal marine foods"
    assert duplicates.clean_name("Smith & Sons (India) Private Limited") == "smith and sons"


@pytest.mark.django_db
def test_signing_up_with_a_known_company_name_flags_it():
    profile("Coastal Marine Foods", "32AAAAA0003A1Z1")
    register_applicant(email="joseph@coastal.example", password=PASSWORD, name="Joseph",
                       organisation_name="Coastal Marine Foods Pvt Ltd")
    pair = C.objects.get()
    assert pair.level == C.Level.HIGH and pair.status == C.Status.OPEN


@pytest.fixture
def world(db):
    """Two awards; Shri Ganesh registered twice. Both records entered Award A; only the first entered Award B."""
    award_a, award_b, award_c = AwardFactory(name="Award A"), AwardFactory(name="Award B"), AwardFactory(name="Award C")
    staff = StaffFactory()
    main = profile("Shri Ganesh Polymers Ltd", "24AAAAA0002A1Z3")
    second = profile("Shree Ganesh Polymers Limited", "27AAAAA0002A1Z1", verified=False)
    main_a = ApplicationFactory(applicant=main.user, award=award_a)
    second_a = ApplicationFactory(applicant=second.user, award=award_a, status=Application.Status.SUBMITTED)
    main_b = ApplicationFactory(applicant=main.user, award=award_b)
    duplicates.scan()
    return {"a": award_a, "b": award_b, "c": award_c, "staff": staff, "main": main, "second": second,
            "main_a": main_a, "second_a": second_a, "main_b": main_b, "pair": C.objects.get()}


def staff_client(user):
    client = Client()
    assert web_login(client, user.email).status_code == 302, "test login failed"
    return client


TAB = re.compile(r'class="chip[^"]*" href="\?award=[^"]+">([^<]+?) \((\d+)\)')


def tab_counts(page):
    """{tab label: count} from the duplicate review page."""
    return {name: int(n) for name, n in TAB.findall(page)}


def test_pair_is_listed_only_under_the_award_both_entered(world):
    page = staff_client(world["staff"]).get(reverse("awards:duplicates")).content.decode()
    assert tab_counts(page) == {"Award A": 1, "Award B": 0, "Award C": 0, "Not in the same award": 0}
    assert "Shree Ganesh Polymers Limited" in page

    page_b = staff_client(world["staff"]).get(reverse("awards:duplicates") + "?award=" + world["b"].slug)
    assert "Shree Ganesh Polymers Limited" not in page_b.content.decode()


def test_pairs_that_did_not_both_enter_one_award_have_their_own_tab(world):
    world["second_a"].delete()
    page = staff_client(world["staff"]).get(reverse("awards:duplicates")).content.decode()
    assert tab_counts(page)["Award A"] == 0 and tab_counts(page)["Not in the same award"] == 1


def test_staff_only_see_pairs_touching_their_awards(world):
    outsider = StaffFactory(awards=[world["c"]])
    assert not duplicates.candidates_for(outsider).exists()
    response = staff_client(outsider).post(reverse("awards:duplicate_decide", args=[world["pair"].pk]),
                                           {"action": "separate"})
    assert response.status_code == 404
    assert duplicates.candidates_for(LeaderFactory()).count() == 1


def test_merge_is_blocked_until_one_entry_in_the_shared_award_is_declined(world):
    with pytest.raises(BusinessRuleError, match="Both organisations have an entry in Award A"):
        duplicates.merge(world["pair"], by=world["staff"], keep=world["main"])

    applications.decline_entry(world["second_a"], by=world["staff"], note="Duplicate entry")
    duplicates.merge(world["pair"], by=world["staff"], keep=world["main"], note="Same PAN")

    world["second"].refresh_from_db()
    assert world["second"].merged_into == world["main"]
    assert world["pair"].status == C.Status.MERGED and world["pair"].decided_by == world["staff"]


def test_after_a_merge_verification_follows_the_main_record(world):
    applications.decline_entry(world["second_a"], by=world["staff"], note="Duplicate entry")
    assert world["second"] in organisations_to_verify(world["staff"])
    assert not duplicates.is_verified(world["second"])
    duplicates.merge(world["pair"], by=world["staff"], keep=world["main"])
    world["second"].refresh_from_db()
    assert duplicates.is_verified(world["second"])
    assert world["second"] not in organisations_to_verify(world["staff"])     # nothing left to check


def test_web_flow_decline_from_the_card_then_merge_then_undo(world):
    client = staff_client(world["staff"])
    page = client.get(reverse("awards:duplicates")).content.decode()
    assert "Can't merge yet" in page and "Decline as duplicate" in page

    client.post(reverse("awards:reject_report", args=[world["second_a"].pk]),
                {"note": "Duplicate entry", "next": reverse("awards:duplicates")})
    world["second_a"].refresh_from_db()
    assert world["second_a"].status == Application.Status.REJECTED

    url = reverse("awards:duplicate_decide", args=[world["pair"].pk])
    client.post(url, {"action": "merge", "keep": world["main"].pk, "note": "Same PAN"})
    world["second"].refresh_from_db()
    assert world["second"].merged_into_id == world["main"].pk
    decided = client.get(reverse("awards:duplicates") + "?show=decided").content.decode()
    assert tab_counts(decided) == {"Award A": 1, "Award B": 0, "Award C": 0, "Not in the same award": 0}

    client.post(url, {"action": "undo"})
    world["second"].refresh_from_db()
    world["pair"].refresh_from_db()
    assert world["second"].merged_into is None and world["pair"].status == C.Status.OPEN


def test_keep_separate_is_remembered_by_later_scans(world):
    duplicates.keep_separate(world["pair"], by=world["staff"], note="Different companies")
    duplicates.scan()
    assert C.objects.get().status == C.Status.SEPARATE
    with pytest.raises(BusinessRuleError, match="already been decided"):
        duplicates.merge(world["pair"], by=world["staff"], keep=world["main"])


def test_an_entry_cannot_be_accepted_while_its_duplicate_also_entered_the_award(world):
    world["second"].verification_status = ApplicantProfile.Verification.VERIFIED
    world["second"].save()
    with pytest.raises(BusinessRuleError, match="Duplicate review"):
        applications.accept_entry(world["second_a"], by=world["staff"])
    duplicates.keep_separate(world["pair"], by=world["staff"])
    applications.accept_entry(world["second_a"], by=world["staff"])
    assert world["second_a"].status == Application.Status.ACCEPTED


def test_entries_page_flags_possible_duplicates(world):
    page = staff_client(world["staff"]).get(reverse("awards:entries")).content.decode()
    assert "Possible duplicate" in page


def test_every_decision_is_audited(world):
    from apps.audit.models import AuditLog
    duplicates.keep_separate(world["pair"], by=world["staff"])
    duplicates.undo(world["pair"], by=world["staff"])
    entries = AuditLog.objects.filter(entity="duplicatecandidate", entity_id=str(world["pair"].pk))
    assert entries.count() == 2 and all(e.user == world["staff"] for e in entries)


def test_duplicate_review_is_for_programme_staff_only(world, client):
    from .factories import ManagerFactory
    manager = ManagerFactory(awards=[world["a"]])
    for person in (manager, LeaderFactory()):
        c = staff_client(person)
        home = c.get(reverse("awards:staff_home" if person.role == "manager" else "dashboard:overview"))
        assert reverse("awards:duplicates") not in home.content.decode()                   # no menu item, no tile
        assert c.get(reverse("awards:duplicates")).status_code == 403
        assert c.post(reverse("awards:duplicate_decide", args=[world["pair"].pk]),
                      {"action": "separate"}).status_code == 403
        with pytest.raises(BusinessRuleError, match="Programme staff decide duplicates"):
            duplicates.keep_separate(world["pair"], by=person)


def test_leaders_have_no_all_applications_page(db):
    from django.urls import NoReverseMatch
    with pytest.raises(NoReverseMatch):
        reverse("dashboard:review")
    leader = LeaderFactory()
    page = staff_client(leader).get(reverse("dashboard:overview")).content.decode()
    assert "All applications" not in page and "Duplicate review" not in page
