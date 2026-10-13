"""Errors use the same shape as successes: {success: false, data: null, message, errors}."""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.services import BusinessRuleError

logger = logging.getLogger("apps.api")


def _message(errors, fallback):
    if isinstance(errors, dict) and "detail" in errors:
        return str(errors["detail"])
    if isinstance(errors, dict) and "non_field_errors" in errors:
        return str(errors["non_field_errors"][0])
    if isinstance(errors, list) and errors:
        return str(errors[0])
    if isinstance(errors, dict) and errors:   # field errors: name the first one
        field, problems = next(iter(errors.items()))
        first = problems[0] if isinstance(problems, list) and problems else problems
        if isinstance(first, dict):   # nested (e.g. items[0].judge): stay generic
            return "Check the highlighted fields."
        return f"{field}: {first}"
    return fallback


def envelope_exception_handler(exc, context):
    # Business rules broken in the service layer → 400 with a clear message.
    if isinstance(exc, BusinessRuleError):
        exc = exceptions.ValidationError({"detail": str(exc)})
    elif isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError({"detail": exc.messages[0] if exc.messages else "Invalid data."})
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()

    response = exception_handler(exc, context)
    if response is None:   # unexpected error: log it, don't leak details
        logger.exception("Unhandled API error", exc_info=exc)
        return Response({"success": False, "data": None, "message": "Something went wrong. Please try again.",
                         "errors": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    errors = response.data
    response.data = {
        "success": False,
        "data": None,
        "message": _message(errors, "Request failed."),
        "errors": errors if not (isinstance(errors, dict) and set(errors) == {"detail"}) else None,
    }
    return response
