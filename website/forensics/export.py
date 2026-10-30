"""Explicit forensic export: no authentication credentials or session cookies."""
from datetime import datetime, timezone

from django.contrib.admin.models import LogEntry
from django.db import transaction

from website.models import AuditEvent, Record


def export_bundle(*, case_tag=None, since=None, until=None, record_id=None):
    with transaction.atomic():
        events = AuditEvent.objects.order_by("timestamp", "id")
        if case_tag is not None:
            events = events.filter(case_tag=case_tag)
        if since:
            events = events.filter(timestamp__gte=since)
        if until:
            events = events.filter(timestamp__lte=until)
        if record_id is not None:
            events = events.filter(object_id=str(record_id))
        return {
            "schema": 1, "exported_at_utc": datetime.now(timezone.utc).isoformat(),
            "filters": {"case_tag": case_tag, "since": since, "until": until, "record_id": record_id},
            "events": list(events.values()),
            "admin_log": list(LogEntry.objects.filter(content_type__app_label="website", content_type__model="record")
                              .order_by("action_time", "id").values("id", "action_time", "user_id", "object_id", "action_flag", "change_message")),
            "records": list(Record.objects.order_by("pk").values()),
        }
