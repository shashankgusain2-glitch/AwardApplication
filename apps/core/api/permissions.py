"""
Role permissions for the API. The role comes from the logged-in user's
account (request.user.role), never from the request body or URL.
"""
from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    roles = ()
    message = "Your role can't do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.roles)


class IsApplicant(HasRole):
    roles = ("applicant",)


class IsStaff(HasRole):
    roles = ("staff", "manager")   # award managers do staff work on their awards


class IsJudge(HasRole):
    roles = ("judge",)


class IsLeader(HasRole):
    roles = ("leader",)


class IsStaffOrLeader(HasRole):
    """Staff, award managers and leaders. What each sees is narrowed by apps/awards/access.py."""
    roles = ("staff", "manager", "leader")


class IsOwner(BasePermission):
    """Object-level: the object belongs to the user (checks `owner_field` on the view, default "user")."""
    message = "This isn't yours."

    def has_object_permission(self, request, view, obj):
        field = getattr(view, "owner_field", "user")
        return getattr(obj, f"{field}_id", None) == request.user.id
