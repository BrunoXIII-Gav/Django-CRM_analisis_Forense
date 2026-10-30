"""Run with manage.py shell < ... ; refuses nonempty databases (no destructive reset)."""
import os
from datetime import datetime, timezone
from django.contrib.auth.models import User
from django.db import transaction
from website.models import Record


def seed():
    if User.objects.exists() or Record.objects.exists():
        raise RuntimeError("Seed requires an empty laboratory; use a new Compose project/volume")
    password = os.environ["LAB_DEMO_PASSWORD"]
    with transaction.atomic():
        User.objects.create_superuser("lab_admin", "admin@example.test", password)
        User.objects.create_user("lab_operator", "operator@example.test", password)
        records = [Record(id=i, first_name=name, last_name="Ficticio", email=f"client{i}@example.test",
                          phone=f"90000000{i}", address=f"Laboratorio {i}", city="Lima", state="Lima", zipcode="12345")
                   for i, name in enumerate(("Ana", "Luis", "Rosa"), 1)]
        Record.objects.bulk_create(records)
        initial_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        Record.objects.all().update(created_at=initial_time, updated_at=initial_time)
    print("Seed created: 2 accounts, 3 fictitious clients; no incident events")


seed()
