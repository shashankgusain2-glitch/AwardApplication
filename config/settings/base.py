"""
Settings shared by every environment (dev, test, prod).

Values that change between machines (secrets, database, hosts, debug) come
from environment variables or a .env file; see .env.example. Nothing secret
is hard-coded here.

Per-award settings (rounds, blind judging, form questions) are NOT here:
they live in the database so staff can change them without code.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key-change-me-in-env-0123456789")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Project apps: data + business logic + API
    "apps.core",
    "apps.accounts",
    "apps.awards",
    "apps.applications",
    "apps.assignments",
    "apps.evaluations",
    "apps.notifications",
    "apps.audit",
    # Project apps: server-rendered portal screens (sample data until Phase 3)
    "apps.entries",
    "apps.judging",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # serves /static/ itself (no Nginx needed for it)
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
            ],
            "builtins": ["apps.core.templatetags.ui"],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
# Set DB_TRANSACTION_POOLER=True when DATABASE_URL goes through a transaction-mode pooler
# (Supabase pooler on port 6543, PgBouncer). Such poolers can't keep server-side cursors
# open between queries, so Django must not use them. Direct or "session" connections: leave False.
DB_TRANSACTION_POOLER = env.bool("DB_TRANSACTION_POOLER", default=False)
if DB_TRANSACTION_POOLER:
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# Custom user model: set before the first migration; hard to change later.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"     # filled by collectstatic (production image)
STATIC_ROOT.mkdir(exist_ok=True)
WHITENOISE_USE_FINDERS = env.bool("DEBUG", default=False)   # in development, serve straight from static/

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="awards@awards.example")
# Used when EMAIL_BACKEND is the SMTP backend (production: SES, Postmark, SendGrid…)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 10
# Links in notification emails start with this (no trailing slash)
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# --- Web login (server-rendered pages) ---------------------------------------
# Log in with email + password. Passwords are stored hashed (salted
# PBKDF2-SHA256, Django's default), never as plain text.
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailBackend"]
LOGIN_URL = "accounts:login"
LOGOUT_REDIRECT_URL = "core:home"

SESSION_COOKIE_HTTPONLY = True             # not readable by JavaScript
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60           # log in again after 8 hours
PASSWORD_RESET_TIMEOUT = 60 * 60           # reset links work for 1 hour

# --- REST API -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",   # lets logged-in web users use /api/docs/
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["apps.core.api.renderers.EnvelopeJSONRenderer"],
    "EXCEPTION_HANDLER": "apps.core.api.exceptions.envelope_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.core.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/minute"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "login": env("THROTTLE_LOGIN", default="10/minute"),   # slows down password guessing
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=1)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default="") or SECRET_KEY,   # blank in .env → use SECRET_KEY
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Awards Platform API",
    "DESCRIPTION": "Applications, judge assignments and evaluations. Every response uses "
                   "{success, data, message, errors}.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": "apps.applications.models.Application.Status",
        "AssignmentStatusEnum": "apps.assignments.models.JudgeAssignment.Status",
        "EvaluationStatusEnum": "apps.evaluations.models.Evaluation.Status",
        "ChangeRequestStatusEnum": "apps.evaluations.models.ScoreChangeRequest.Status",
        "AwardStatusEnum": "apps.awards.models.Award.Status",
        "VerificationStatusEnum": "apps.accounts.models.ApplicantProfile.Verification",
    },
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# --- Logging: console + rotating file -------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "app.log",
            "maxBytes": 5 * 1024 * 1024,   # 5 MB per file
            "backupCount": 5,
            "formatter": "standard",
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
    },
}
