from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation

User = get_user_model()


class LoginForm(forms.Form):
    """
    Email + password for ONE role (the tab the user is on).
    The role is checked here, on the server: a judge's details fail on the
    Applicant tab even if the password is right.
    """
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))
    password = forms.CharField(label="Password", strip=False,
                               widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, *args, role, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get("email"), cleaned.get("password")
        if email and password:
            user = authenticate(self.request, email=email, password=password)
            # Same message for "no account", "wrong password" and "wrong tab",
            # so the form doesn't reveal which accounts exist.
            if user is None or user.role != self.role:
                role_label = User.Role(self.role).label
                article = "an" if role_label[0] in "AEIOU" else "a"
                raise forms.ValidationError(
                    f"Incorrect email or password for {article} {role_label} account. "
                    f"Check you're on the right tab.")
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
            candidate = User(email=cleaned.get("email", ""), first_name=cleaned.get("full_name", ""))
            try:
                password_validation.validate_password(p1, candidate)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def save(self):
        first, _, last = self.cleaned_data["full_name"].strip().partition(" ")
        user = User(email=self.cleaned_data["email"], username=self.cleaned_data["email"],
                    first_name=first, last_name=last, role=User.Role.APPLICANT)
        user.set_password(self.cleaned_data["password1"])   # stored hashed
        user.save()
        return user
