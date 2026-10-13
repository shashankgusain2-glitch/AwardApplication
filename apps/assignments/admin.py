from django.contrib import admin

from .models import ConflictOfInterest, JudgeAssignment


@admin.register(JudgeAssignment)
class JudgeAssignmentAdmin(admin.ModelAdmin):
    list_display = ["report", "judge", "round", "status", "assigned_by", "assigned_at"]
    list_filter = ["status", "round", "report__award"]
    search_fields = ["report__reference", "judge__email"]
    raw_id_fields = ["judge", "report", "assigned_by"]


@admin.register(ConflictOfInterest)
class ConflictOfInterestAdmin(admin.ModelAdmin):
    list_display = ["judge", "applicant_profile", "reason", "recorded_by", "created_at"]
    search_fields = ["judge__email", "applicant_profile__organisation_name"]
    raw_id_fields = ["judge", "applicant_profile", "recorded_by"]
