import io
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from website.models import AuditEvent, Record
from website.tests_forensic import DATOS
from website.forensics import services


class ServiceTests(TestCase):
    def test_noop_keeps_timestamps_and_records_classification(self):
        r = services.create_record(DATOS)
        before = r.updated_at
        services.update_record(r.pk, {"city": "Lima"})
        r.refresh_from_db()
        event = AuditEvent.objects.get(action="UPDATE")
        self.assertEqual(r.updated_at, before)
        self.assertEqual(event.outcome, "noop")
        self.assertEqual(event.changed_fields, [])
        self.assertEqual(event.before, event.after)

    def test_failure_rolls_back_each_service_operation(self):
        r = services.create_record(DATOS)
        for operation in (
            lambda: services.create_record(DATOS),
            lambda: services.update_record(r.pk, {"city": "Cusco"}),
            lambda: services.delete_record(r.pk),
        ):
            with self.subTest(operation=operation), patch.object(services, "write_event", side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    operation()
            self.assertEqual(Record.objects.count(), 1)
            self.assertEqual(Record.objects.get().city, "Lima")
            self.assertEqual(AuditEvent.objects.count(), 1)

    def test_outer_rollback_removes_business_and_events(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                services.create_record(DATOS)
                raise RuntimeError
        self.assertFalse(Record.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())

    def test_export_is_read_only_filtered_and_has_no_credentials(self):
        r = services.create_record(DATOS)
        out = io.StringIO()
        call_command("export_audit", record_id=r.pk, stdout=out)
        bundle = json.loads(out.getvalue())
        self.assertEqual(len(bundle["events"]), 1)
        self.assertEqual(bundle["events"][0]["object_id"], str(r.pk))
        self.assertNotIn("password", out.getvalue())
        self.assertEqual(AuditEvent.objects.count(), 1)
        for args in ({"since": "2026-01-01"}, {"until": "bad"},
                     {"since": "2026-12-01T00:00:00Z", "until": "2026-01-01T00:00:00Z"}):
            with self.assertRaises(CommandError):
                call_command("export_audit", **args, stdout=io.StringIO())

    def test_unapproved_snapshot_fields_rejected(self):
        with self.assertRaises(ValueError):
            services.create_record({**DATOS, "password": "secret"})
        self.assertFalse(Record.objects.exists())


class ChannelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("tester", "tester@example.test", "x")
        self.client.force_login(self.user)

    def test_real_admin_bulk_action_is_atomic_and_unique(self):
        ids = [services.create_record(DATOS).pk for _ in range(2)]
        url = "/admin/website/record/"
        response = self.client.post(url, {"action": "delete_selected", "_selected_action": ids, "post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Record.objects.exists())
        events = AuditEvent.objects.filter(action="DELETE")
        self.assertEqual(events.count(), 2)
        self.assertEqual({e.source for e in events}, {"admin"})
        self.assertEqual(len({e.request_id for e in events}), 1)

    def test_bulk_failure_reverts_previous_deletions_and_admin_logs(self):
        ids = [services.create_record(DATOS).pk for _ in range(2)]
        original = services.write_event
        calls = []
        def fail_second(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("audit unavailable")
            return original(*args, **kwargs)
        with patch.object(services, "write_event", side_effect=fail_second), self.assertRaises(RuntimeError):
            self.client.post("/admin/website/record/", {"action": "delete_selected", "_selected_action": ids, "post": "yes"})
        self.assertEqual(Record.objects.count(), 2)
        self.assertEqual(AuditEvent.objects.count(), 2)

    def test_invalid_requests_and_admin_permissions_do_not_change_records(self):
        for url, content_type in (("/record/add/", "application/x-www-form-urlencoded"),
                                  ("/api/records/", "application/json"),
                                  ("/admin/website/record/add/", "application/x-www-form-urlencoded")):
            self.client.post(url, {} if content_type.endswith("json") else "", content_type=content_type)
        self.assertFalse(Record.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())
        user = User.objects.create_user("limited", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.post("/admin/website/record/add/", DATOS).status_code, 403)
        self.assertFalse(AuditEvent.objects.exists())

    def test_service_failure_at_each_http_channel(self):
        for url, content_type in (("/record/add/", "application/x-www-form-urlencoded"),
                                  ("/api/records/", "application/json"),
                                  ("/admin/website/record/add/", "application/x-www-form-urlencoded")):
            with self.subTest(url=url), patch.object(services, "write_event", side_effect=RuntimeError), self.assertRaises(RuntimeError):
                if content_type.endswith("json"):
                    self.client.post(url, DATOS, content_type=content_type)
                else:
                    self.client.post(url, DATOS)
            self.assertFalse(Record.objects.exists())
            self.assertFalse(AuditEvent.objects.exists())


class ConcurrentTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_writers_capture_consecutive_persisted_states(self):
        r = services.create_record(DATOS)
        barrier = threading.Barrier(2)
        def write(city):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                services.update_record(r.pk, {"city": city})
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(write, city) for city in ("Cusco", "Piura")]
            for future in futures:
                future.result(timeout=20)
        events = list(AuditEvent.objects.filter(action="UPDATE").order_by("id"))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].before["city"], "Lima")
        self.assertEqual(events[1].before, events[0].after)
        self.assertEqual(Record.objects.get(pk=r.pk).city, events[1].after["city"])
