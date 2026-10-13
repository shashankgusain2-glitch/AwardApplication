from django.contrib import admin

from .models import Application, Attachment


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ["original_name", "size_bytes", "content_type", "uploaded_by", "created_at"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["reference", "title", "applicant", "award", "status", "submitted_at", "is_deleted"]
    list_filter = ["status", "award", "edit_requested", "is_deleted"]
    search_fields = ["reference", "title", "applicant__email"]
    raw_id_fields = ["applicant"]
    readonly_fields = ["reference", "form_version", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [AttachmentInline]

    def get_queryset(self, request):
        return Application.all_objects.select_related("applicant", "award")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["original_name", "application", "content_type", "size_bytes", "created_at"]
    search_fields = ["original_name", "application__reference"]
