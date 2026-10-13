from django.contrib import admin

from .models import Application, Organisation

admin.site.register(Organisation)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["organisation", "award", "status", "edit_request", "updated_at"]
    list_filter = ["award", "status", "edit_request"]
