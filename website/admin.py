from django.contrib import admin

from .models import AuditEvent, Record
from .forensics import services


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "city", "state", "created_at")
    list_filter = ("state", "city", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        data = {field: form.cleaned_data[field] for field in services.DATA_FIELDS}
        saved = (services.update_record(obj.pk, data, request=request) if change
                 else services.create_record(data, request=request))
        # Django uses this same object for LogEntry, redirects and save_related.
        for field in obj._meta.concrete_fields:
            setattr(obj, field.attname, getattr(saved, field.attname))
        obj._state.adding = False
        obj._state.db = saved._state.db

    def delete_model(self, request, obj):
        services.delete_record(obj.pk, request=request)

    def delete_queryset(self, request, queryset):
        services.delete_records(queryset, request=request)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("id", "timestamp", "username", "action", "model_name", "object_id", "source", "ip_address")
    list_filter = ("action", "source", "timestamp")
    search_fields = ("username", "object_id", "correlation_id", "request_id", "event_id", "case_tag")
    ordering = ("-id",)
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
