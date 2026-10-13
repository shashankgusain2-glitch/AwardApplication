from django.contrib import admin

from .models import Award, AwardRound, Criterion, FormVersion


class AwardRoundInline(admin.TabularInline):
    model = AwardRound
    extra = 0


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 0


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "closes_on", "judges_per_report", "blind_judging", "is_deleted"]
    list_filter = ["status", "blind_judging", "applicant_type", "is_deleted"]
    search_fields = ["name", "slug", "sector"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [AwardRoundInline, CriterionInline]

    def get_queryset(self, request):
        return Award.all_objects.all()   # admins also see soft-deleted awards


@admin.register(FormVersion)
class FormVersionAdmin(admin.ModelAdmin):
    list_display = ["award", "version", "published_at", "created_at"]
    list_filter = ["award"]

    def get_readonly_fields(self, request, obj=None):
        return ["award", "version", "questions", "published_at"] if obj and obj.published_at else []
