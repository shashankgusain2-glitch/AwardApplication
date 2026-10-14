"""Tests: fast, isolated and quiet."""
from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK

DEBUG = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Fast hashing in tests (real PBKDF2 is checked by tests marked real_hashing).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# No rate limits in tests, except where a test turns them on.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon": None, "user": None, "login": None},
}
SECRET_KEY = "test-only-secret-key-long-enough-for-hs256-0123456789"

LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"null": {"class": "logging.NullHandler"}},
           "root": {"handlers": ["null"]}}

# Open and close awards by their dates on every request, so tests see the change at once.
AWARD_DATE_RULES_EVERY = 0
