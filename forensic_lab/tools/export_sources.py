"""Read-only source extraction; also runs against the uninstrumented baseline."""
import json
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dcrm.settings.lab")
import django
django.setup()
from django.apps import apps
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils.timezone import now
from website.models import Record

with transaction.atomic():
    try:
        AuditEvent = apps.get_model("website", "AuditEvent")
    except LookupError:
        AuditEvent = None
    bundle = {
        "schema": 1, "exported_at_utc": now(), "database_vendor": connection.vendor,
        "audit_available": AuditEvent is not None,
        "events": list(AuditEvent.objects.order_by("timestamp", "id").values()) if AuditEvent else [],
        "records": list(Record.objects.order_by("pk").values()),
        "admin_log": list(LogEntry.objects.filter(content_type__app_label="website", content_type__model="record")
                          .order_by("action_time", "id").values("id", "action_time", "user_id", "object_id", "action_flag", "change_message")),
        "accounts": list(User.objects.order_by("pk").values("id", "username", "is_staff", "is_superuser")),
    }
print(json.dumps(bundle, cls=DjangoJSONEncoder, ensure_ascii=False))
