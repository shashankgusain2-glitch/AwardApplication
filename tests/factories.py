"""Test data factories (factory_boy). Fake data only."""
import factory
from django.utils import timezone

from apps.accounts.models import ApplicantProfile, JudgeProfile, User
from apps.applications.models import Application
from apps.awards.models import Award, AwardRound, Criterion, FormVersion

PASSWORD = "Test-pass-2026!"

QUESTIONS = [
    {"key": "org", "label": "Organisation name", "type": "text", "required": True, "identifying": True},
    {"key": "city", "label": "City", "type": "text", "required": False, "identifying": True},
    {"key": "story", "label": "What did you improve?", "type": "textarea", "required": True, "identifying": False},
]


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    role = User.Role.APPLICANT
    password = factory.PostGenerationMethodCall("set_password", PASSWORD)

    @factory.post_generation
    def _save(obj, create, extracted, **kwargs):
        if create:
            obj.save()


class StaffFactory(UserFactory):
    role = User.Role.STAFF


class LeaderFactory(UserFactory):
    role = User.Role.LEADER


class AwardFactory(factory.django.DjangoModelFactory):
    """An open award with one desk round, a published form and two criteria (40 + 60)."""
    class Meta:
        model = Award
        skip_postgeneration_save = True

    slug = factory.Sequence(lambda n: f"award-{n}")
    name = factory.Sequence(lambda n: f"Award {n}")
    status = Award.Status.OPEN
    judges_per_report = 2
    blind_judging = False

    @factory.post_generation
    def setup(obj, create, extracted, **kwargs):
        if not create:
            return
        AwardRound.objects.create(award=obj, number=1, kind="desk")
        FormVersion.objects.create(award=obj, version=1, questions=QUESTIONS, published_at=timezone.now())
        Criterion.objects.create(award=obj, key="approach", label="Approach", weight=40, order=0)
        Criterion.objects.create(award=obj, key="results", label="Results", weight=60, order=1)


class JudgeFactory(UserFactory):
    """A judge on the given awards' panels (pass awards=[...])."""
    role = User.Role.JUDGE

    @factory.post_generation
    def awards(obj, create, extracted, **kwargs):
        if not create:
            return
        profile = JudgeProfile.objects.create(user=obj, priority=5, max_open_assignments=10)
        if extracted:
            profile.awards.set(extracted)


class ApplicantProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ApplicantProfile

    user = factory.SubFactory(UserFactory)
    organisation_name = factory.Sequence(lambda n: f"Organisation {n} Pvt Ltd")
    gstin = factory.Sequence(lambda n: f"27AAAAA{n:04d}A1Z5")
    verification_status = ApplicantProfile.Verification.VERIFIED


class ApplicationFactory(factory.django.DjangoModelFactory):
    """A submitted report from a verified organisation."""
    class Meta:
        model = Application

    applicant = factory.LazyAttribute(lambda o: ApplicantProfileFactory().user)
    award = factory.SubFactory(AwardFactory)
    form_version = factory.LazyAttribute(lambda o: o.award.current_form)
    reference = factory.Sequence(lambda n: f"TST-2026-{n:05d}")
    title = factory.Sequence(lambda n: f"Report {n}")
    content = factory.LazyAttribute(lambda o: {"org": "Secret Org Ltd", "city": "Pune", "story": "We cut waste."})
    status = Application.Status.SUBMITTED
    submitted_at = factory.LazyFunction(timezone.now)
