from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PreserveAuditHistoryTests(TransactionTestCase):
    def test_populated_0003_migrates_to_distinct_uuids_without_rewriting_history(self):
        executor = MigrationExecutor(connection)
        old_target = [("website", "0003_auditevent")]
        new_target = [("website", "0004_alter_record_options_auditevent_case_tag_and_more")]
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            Event = old_apps.get_model("website", "AuditEvent")
            for i in range(2):
                Event.objects.create(action="UPDATE", model_name="Record", object_id=str(i),
                    username="legacy", correlation_id="old-session-hash", before={"city": "Lima"}, after={"city": "Cusco"})
            original = list(Event.objects.order_by("id").values("id", "timestamp", "correlation_id", "before", "after"))
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            apps = executor.loader.project_state(new_target).apps
            events = apps.get_model("website", "AuditEvent").objects.order_by("id")
            self.assertEqual(list(events.values("id", "timestamp", "correlation_id", "before", "after")), original)
            self.assertEqual(len(set(events.values_list("event_id", flat=True))), 2)
            self.assertEqual(set(events.values_list("outcome", flat=True)), {"legacy_unknown"})
            self.assertEqual(set(events.values_list("committed", flat=True)), {None})
        finally:
            MigrationExecutor(connection).migrate(new_target)
