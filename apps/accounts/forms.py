from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation

User = get_user_model()


class LoginForm(forms.Form):
    """
    One login for everyone: email + password. The account's role (stored on
    the user, never chosen by the person logging in) decides where they go.
    """
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))
    password = forms.CharField(label="Password", strip=False,
                               widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get("email"), cleaned.get("password")
        if email and password:
            user = authenticate(self.request, email=email, password=password)
            # Same message for "no account" and "wrong password",
            # so the form doesn't reveal which accounts exist.
            if user is None:
                raise forms.ValidationError("Incorrect email or password.")
            self.user = user
        return cleaned


class SignUpForm(forms.Form):
    """Applicants register themselves. Every new account here is an applicant."""
    full_name = forms.CharField(label="Full name", max_length=150,
                                widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label="Work email", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password1 = forms.CharField(label="Password", strip=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
                                help_text="At least 8 characters; not too common or all numbers.")
    password2 = forms.CharField(label="Confirm password", strip=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    # Marked * on the page: no account without the organisation, its GSTIN and the PAN.
    organisation_name = forms.CharField(label="Organisation name *", max_length=200,
                                        widget=forms.TextInput(attrs={"autocomplete": "organization"}),
                                        help_text="Required.")
    gstin = forms.CharField(label="GSTIN *", max_length=20,
                            help_text="Required. 15 characters, like 27ABCDE1234F1Z5.",
                            error_messages={"required": "Enter the organisation's GSTIN."})
    holder_pan = forms.CharField(label="PAN of authorised person *", max_length=20,
                                 help_text="Required. 10 characters, like ABCDE1234F.",
                                 error_messages={"required": "Enter the PAN of the authorised person."})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Log in instead.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords don't match.")
        if p1:
            candidate = User(email=cleaned.get("email", ""), name=cleaned.get("full_name", ""))
            try:
                password_validation.validate_password(p1, candidate)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        self._check_organisation(cleaned)
        return cleaned

    def _check_organisation(self, cleaned):
        """The same GSTIN and PAN rules as the organisation profile (format, one profile per GSTIN)."""
        from .api.serializers import ApplicantProfileSerializer

        fields = ("organisation_name", "gstin", "holder_pan")
        if any(f not in cleaned for f in fields):
            return                                     # already reported as missing
        organisation = ApplicantProfileSerializer(data={f: cleaned[f] for f in fields})
        if organisation.is_valid():
            cleaned.update({f: organisation.validated_data[f] for f in fields})
            return
        for field, problems in organisation.errors.items():
            self.add_error(field if field in fields else None, [str(p) for p in problems])

    def save(self):
        from .services import register_applicant
        data = self.cleaned_data
        return register_applicant(email=data["email"], password=data["password1"], name=data["full_name"].strip(),
                                  organisation_name=data["organisation_name"].strip(), gstin=data["gstin"],
                                  holder_pan=data["holder_pan"])
