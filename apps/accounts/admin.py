from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ApplicantProfile, JudgeProfile, User


@admin.register(User)
class RoleUserAdmin(UserAdmin):
    """Admins and leaders create staff, judge and leader accounts here and set each user's role."""
    list_display = ["email", "name", "role", "is_active", "created_at"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "name"]
    ordering = ["email"]
    readonly_fields = ["created_at", "updated_at", "last_login", "date_joined"]
    fieldsets = (
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["name", "role"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Dates", {"fields": ["last_login", "date_joined", "created_at", "updated_at"]}),
    )
    add_fieldsets = ((None, {"classes": ["wide"], "fields": ["email", "name", "role", "password1", "password2"]}),)


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ["organisation_name", "user", "gstin", "verification_status", "verified_at"]
    list_filter = ["verification_status", "organisation_size", "state"]
    search_fields = ["organisation_name", "gstin", "user__email", "contact_name"]
    raw_id_fields = ["user", "verified_by"]


@admin.register(JudgeProfile)
class JudgeProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "expertise", "priority", "max_open_assignments"]
    list_filter = ["awards"]
    search_fields = ["user__email", "user__name", "expertise"]
    filter_horizontal = ["awards"]
