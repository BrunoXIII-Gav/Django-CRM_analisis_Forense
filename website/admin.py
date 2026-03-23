from django.contrib import admin

from .models import Record


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "city", "state", "created_at")
    list_filter = ("state", "city", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
