"""
Opens and closes awards by their dates (awards.services.apply_date_rules) as requests come in,
so no scheduler (cron) is needed. Runs at most once every AWARD_DATE_RULES_EVERY seconds
per server process (default 60; 0 = every request, used by the tests).
"""
import logging
import time

from django.conf import settings

from .services import apply_date_rules

logger = logging.getLogger(__name__)


class AwardDateRulesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.every = getattr(settings, "AWARD_DATE_RULES_EVERY", 60)
        self.last_run = None

    def __call__(self, request):
        now = time.monotonic()
        if self.last_run is None or now - self.last_run >= self.every:
            self.last_run = now
            try:
                apply_date_rules()
            except Exception:   # never let this break a page; it runs again on a later request
                logger.exception("Couldn't apply award opening/closing dates")
        return self.get_response(request)
