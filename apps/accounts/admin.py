from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class RoleUserAdmin(UserAdmin):
    """Admins create staff, judge and leader accounts here and set each user's role."""
    list_display = ["email", "first_name", "last_name", "role", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    fieldsets = UserAdmin.fieldsets + (("Role in the awards platform", {"fields": ["role"]}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role in the awards platform", {"fields": ["email", "role"]}),)
