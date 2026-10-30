from django.contrib import admin

from .models import AuditEvent, Record


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "city", "state", "created_at")
    list_filter = ("state", "city", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("id", "timestamp", "username", "action", "model_name", "object_id", "source", "ip_address")
    list_filter = ("action", "source", "timestamp")
    search_fields = ("username", "object_id", "correlation_id", "request_id")
    ordering = ("-id",)
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
