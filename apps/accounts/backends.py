from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Log in with email + password (case-insensitive email).
    The role check happens in the login form, not here, so this backend
    stays usable by the admin site and password reset.
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        email = email or username
        if not email or not password:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            # Hash anyway so a missing account takes as long as a wrong password.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
