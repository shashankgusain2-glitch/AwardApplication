from django.contrib import admin

from .models import Assignment, Conflict, JudgeProfile, Round2Meeting, ScoreChange, ScoreChangeRequest

admin.site.register([JudgeProfile, Conflict, Assignment, ScoreChangeRequest, Round2Meeting])


@admin.register(ScoreChange)
class ScoreChangeAdmin(admin.ModelAdmin):
    """Read-only: score changes are a permanent record (Rule 3)."""
    list_display = ["assignment", "criterion", "old_value", "new_value", "changed_by", "changed_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
