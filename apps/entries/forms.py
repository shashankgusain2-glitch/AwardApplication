from django import forms

from .models import Organisation
from .validators import clean_id, is_valid_gstin, is_valid_pan


class EmailForm(forms.Form):
    email = forms.EmailField(label="Work email", widget=forms.EmailInput(attrs={"autocomplete": "email"}))


class CodeForm(forms.Form):
    code = forms.CharField(label="6-digit code", max_length=6, min_length=6,
                           widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}))


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ["name", "gstin", "holder_pan"]
        labels = {"name": "Organisation name"}
        help_texts = {
            "gstin": "15 characters, e.g. 27ABCDE1234F1Z5",
            "holder_pan": "PAN of the person who holds the organisation, e.g. ABCDE1234F",
        }

    def clean_gstin(self):
        gstin = clean_id(self.cleaned_data["gstin"])
        if not is_valid_gstin(gstin):
            raise forms.ValidationError("This doesn't look like a valid GSTIN. Check the 15 characters.")
        if Organisation.objects.filter(gstin=gstin).exists():
            raise forms.ValidationError(
                "This GSTIN is already registered. If this is your organisation, please contact the awards team.")
        return gstin

    def clean_holder_pan(self):
        pan = clean_id(self.cleaned_data["holder_pan"])
        if not is_valid_pan(pan):
            raise forms.ValidationError("This doesn't look like a valid PAN. It should be like ABCDE1234F.")
        return pan


def application_form(questions, data=None, initial=None, require_all=False, disabled=False):
    """
    Build a form from an award's stored questions.
    Drafts can be saved with gaps; required questions are checked only on submit.
    """
    fields = {}
    for q in questions:
        kwargs = {"label": q["label"], "required": require_all and q.get("required", False), "disabled": disabled}
        if q["type"] == "number":
            field = forms.IntegerField(min_value=0, **kwargs)
        elif q["type"] == "textarea":
            field = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), max_length=3000, **kwargs)
        else:
            field = forms.CharField(max_length=200, **kwargs)
        fields[q["key"]] = field
    form_class = type("ApplicationForm", (forms.Form,), fields)
    return form_class(data=data, initial=initial)


class EditRequestForm(forms.Form):
    reason = forms.CharField(label="Why do you need to change your application?",
                             widget=forms.Textarea(attrs={"rows": 3}), max_length=1000)
