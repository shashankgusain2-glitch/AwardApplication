"""Local development: debug on, emails printed, any local frontend allowed."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:3000", "http://localhost:5173",
])

# The Postman collection makes about a dozen login and sign-up calls in one
# run, so local development allows more per minute. Production keeps the
# stricter limit from base.py (THROTTLE_LOGIN, 10/minute by default).
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"] = env("THROTTLE_LOGIN_DEV", default="60/minute")
