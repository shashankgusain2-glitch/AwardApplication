from django import forms

from apps.awards.models import Award
from apps.entries.models import Organisation
from apps.judging.models import JudgeProfile


class JudgeForm(forms.Form):
    name = forms.CharField(max_length=200)
    email = forms.EmailField()
    expertise = forms.CharField(max_length=200, required=False)
    priority = forms.IntegerField(min_value=1, max_value=99, initial=5, help_text="1 = first choice")
    max_load = forms.IntegerField(min_value=1, max_value=50, initial=10, label="Most reports at once")
    panels = forms.ModelMultipleChoiceField(queryset=Award.objects.all(), widget=forms.CheckboxSelectMultiple,
                                            label="Selected for events", required=False)


class ConflictForm(forms.Form):
    judge = forms.ModelChoiceField(queryset=JudgeProfile.objects.all())
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.all())
    note = forms.CharField(max_length=300, required=False, help_text="e.g. former employer, family link")


class RejectForm(forms.Form):
    reason = forms.CharField(max_length=300, label="Why it failed the proof check")


class Round2Form(forms.Form):
    scheduled_at = forms.DateTimeField(label="Meeting date and time",
                                       widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    meeting_link = forms.URLField(label="Online meeting link", assume_scheme="https")
    judges = forms.ModelMultipleChoiceField(queryset=JudgeProfile.objects.none(),
                                            widget=forms.CheckboxSelectMultiple, label="Judges in the meeting")

    def __init__(self, *args, judges=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["judges"].queryset = judges if judges is not None else JudgeProfile.objects.none()


class EventSettingsForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = ["judges_per_report", "is_open", "deadline"]
        labels = {"judges_per_report": "Judges per report", "is_open": "Open for applications"}
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}


class NewQuestionForm(forms.Form):
    label = forms.CharField(max_length=200, required=False, label="New question")
    type = forms.ChoiceField(choices=[("text", "Short text"), ("textarea", "Long text"), ("number", "Number")])
    required = forms.BooleanField(required=False, initial=True)
