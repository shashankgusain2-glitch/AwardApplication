"""
Production: secrets and hosts must come from the environment; HTTPS only.

Run `python manage.py check --deploy` against these settings before every
release. The runbook is docs/Deployment.md.
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import DATABASES, DB_TRANSACTION_POOLER, LOGGING, env

DEBUG = False
SECRET_KEY = env("SECRET_KEY")                 # required: no default in production

# Hosts: your own domain(s) from ALLOWED_HOSTS, plus the address Render or Railway
# gives the service (they set these variables themselves).
PLATFORM_HOSTS = [h for h in (env("RENDER_EXTERNAL_HOSTNAME", default=""),
                              env("RAILWAY_PUBLIC_DOMAIN", default="")) if h]
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[]) + PLATFORM_HOSTS
if env("RAILWAY_ENVIRONMENT", default=""):
    ALLOWED_HOSTS.append("healthcheck.railway.app")   # Railway's health checker uses this host name
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS (your domain), or deploy on Render/Railway.")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# The platform's health check calls the app directly over plain HTTP: don't redirect it.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)   # turn on once the domain is settled
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[]) + [f"https://{h}" for h in PLATFORM_HOSTS]
# Links in emails: SITE_URL if set, else the platform address.
SITE_URL = env("SITE_URL", default=f"https://{PLATFORM_HOSTS[0]}" if PLATFORM_HOSTS else "http://localhost:8000")
# Reuse database connections between requests (a transaction pooler does that job itself).
DATABASES["default"]["CONN_MAX_AGE"] = 0 if DB_TRANSACTION_POOLER else env.int("CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# --- Files ------------------------------------------------------------------------
# Static files: compressed, with hashed names, served by WhiteNoise.
# Uploaded files: an S3-compatible bucket when one is configured (private,
# signed URLs); otherwise the local media folder (single-server setups only).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)     # for DO Spaces, Cloudflare R2…
    AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", default=None)   # "path" for Supabase Storage
    AWS_DEFAULT_ACL = None                 # private bucket
    AWS_QUERYSTRING_AUTH = True            # signed, expiring download links
    AWS_QUERYSTRING_EXPIRE = 300
    AWS_S3_FILE_OVERWRITE = False

# --- Logs: stdout only (the hosting platform collects them) -----------------------
LOGGING = {
    **LOGGING,
    "handlers": {"console": LOGGING["handlers"]["console"]},
    "root": {**LOGGING["root"], "handlers": ["console"]},
    "loggers": {name: {**cfg, "handlers": ["console"]} for name, cfg in LOGGING["loggers"].items()},
}

# --- Error tracking (Sentry), only when a DSN is set -------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,            # applicant data (GSTIN, PAN, emails) stays out of Sentry
    )
