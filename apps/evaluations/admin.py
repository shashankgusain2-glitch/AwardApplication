from django.contrib import admin

from .models import CriterionScore, Evaluation, ScoreChange, ScoreChangeRequest


class CriterionScoreInline(admin.TabularInline):
    model = CriterionScore
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ["assignment", "status", "total_score", "submitted_at"]
    list_filter = ["status"]
    search_fields = ["assignment__report__reference", "assignment__judge__email"]
    inlines = [CriterionScoreInline]


@admin.register(ScoreChangeRequest)
class ScoreChangeRequestAdmin(admin.ModelAdmin):
    list_display = ["evaluation", "status", "decided_by", "created_at"]
    list_filter = ["status"]


@admin.register(ScoreChange)
class ScoreChangeAdmin(admin.ModelAdmin):
    """Read-only: score changes are a permanent record (Rule 3)."""
    list_display = ["evaluation", "criterion", "old_score", "new_score", "changed_by", "created_at"]
    search_fields = ["evaluation__assignment__report__reference", "changed_by__email"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
