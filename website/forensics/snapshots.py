import json

from django.core.serializers.json import DjangoJSONEncoder

DATA_FIELDS = ("first_name", "last_name", "email", "phone", "address", "city", "state", "zipcode")
SNAPSHOT_FIELDS = ("id", *DATA_FIELDS, "created_at", "updated_at")


def snapshot(instance):
    data = {field: getattr(instance, field) for field in SNAPSHOT_FIELDS}
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def differences(before, after):
    return sorted(field for field in SNAPSHOT_FIELDS
                  if (before or {}).get(field) != (after or {}).get(field))
