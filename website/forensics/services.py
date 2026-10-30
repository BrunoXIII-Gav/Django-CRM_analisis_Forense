"""One transaction for each business operation and its audit event."""
from django.conf import settings
from django.db import router, transaction

from website.models import AuditEvent, Record
from .context import current_context, service_active
from .snapshots import DATA_FIELDS, differences, snapshot


def write_event(action, instance, before, after, using, request=None):
    ctx = getattr(request, "forensic_context", None) or current_context.get() or {}
    request = request or ctx.get("request")
    user = getattr(request, "user", None)
    authenticated = bool(user and user.is_authenticated)
    changed = differences(before, after)
    noop = action == "UPDATE" and not set(changed).intersection(DATA_FIELDS)
    return AuditEvent.objects.using(using).create(
        username=user.get_username() if authenticated else "",
        user_id=user.pk if authenticated else None,
        ip_address=ctx.get("ip"), correlation_id=ctx.get("correlation_id", ""),
        request_id=ctx.get("request_id", ""), source=ctx.get("source", ""),
        user_agent=ctx.get("user_agent", ""), case_tag=settings.FORENSIC_CASE_TAG,
        action=action, model_name="Record", object_id=str(instance.pk),
        before=before, after=after, changed_fields=changed,
        outcome="noop" if noop else "success", committed=True,
    )


def _validated_data(data):
    unknown = set(data) - set(DATA_FIELDS)
    if unknown:
        raise ValueError("Unsupported Record fields: " + ", ".join(sorted(unknown)))
    return data


def create_record(data, *, request=None, using=None):
    using = using or router.db_for_write(Record)
    data = _validated_data(data)
    with transaction.atomic(using=using):
        token = service_active.set(True)
        try:
            record = Record.objects.using(using).create(**data)
            write_event("CREATE", record, None, snapshot(record), using, request)
            return record
        finally:
            service_active.reset(token)


def update_record(pk, data, *, request=None, using=None):
    using = using or router.db_for_write(Record)
    data = _validated_data(data)
    with transaction.atomic(using=using):
        record = Record.objects.using(using).select_for_update().get(pk=pk)
        before = snapshot(record)
        token = service_active.set(True)
        try:
            changed = [field for field, value in data.items() if getattr(record, field) != value]
            for field in changed:
                setattr(record, field, data[field])
            if changed:
                record.save(using=using, update_fields=[*changed, "updated_at"])
                record.refresh_from_db(using=using)
            write_event("UPDATE", record, before, snapshot(record), using, request)
            return record
        finally:
            service_active.reset(token)


def delete_record(pk, *, request=None, using=None):
    using = using or router.db_for_write(Record)
    with transaction.atomic(using=using):
        record = Record.objects.using(using).select_for_update().get(pk=pk)
        before = snapshot(record)
        token = service_active.set(True)
        try:
            write_event("DELETE", record, before, None, using, request)
            record.delete(using=using)
        finally:
            service_active.reset(token)


def delete_records(queryset, *, request=None):
    using = queryset.db
    with transaction.atomic(using=using):
        # Stable lock order; the whole admin action rolls back if any event fails.
        ids = list(queryset.select_for_update().order_by("pk").values_list("pk", flat=True))
        for pk in ids:
            delete_record(pk, request=request, using=using)
