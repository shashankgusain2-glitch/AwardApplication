"""Shared pieces of the service layer (business logic lives in each app's services.py)."""


class BusinessRuleError(Exception):
    """An action that breaks a business rule. The API turns it into a 400 with this message."""
