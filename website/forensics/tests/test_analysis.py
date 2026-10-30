import copy
from pathlib import Path
import sys
from django.test import SimpleTestCase
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "forensic_lab/tools"))
from generate_report import complete, evaluate
from examine_evidence import utc
from website.tests_forensic import DATOS


class AnalysisTests(SimpleTestCase):
    def setUp(self):
        state = {**DATOS, "id": 1, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
        self.row = {"event_id": "event-1", "time_utc": "2026-01-01T05:00:00+00:00", "actor_id": 1,
                    "actor_username": "operator", "record_id": "1", "action": "UPDATE", "channel": "api",
                    "before": state, "after": {**state, "city": "Cusco"}, "outcome": "success", "committed": True,
                    "evidence_id": "CASE/E-001"}
        self.operation = {"operation_id": "OP-1", "started_at_utc": "2026-01-01T00:00:00-05:00",
                          "finished_at_utc": "2026-01-01T00:00:01-05:00", "actor_username": "operator", "record_id": 1,
                          "action": "UPDATE", "channel": "api", "classification": "change", "expected_after": {"city": "Cusco"},
                          "expected_before": {"city": "Lima"}, "rule": "fictional scenario", "legitimate": False}

    def test_offsets_normalized_and_each_event_only_matches_once(self):
        self.assertEqual(utc("2026-01-01T00:00:00-05:00"), "2026-01-01T05:00:00+00:00")
        metrics = evaluate([self.row], {"operations": [self.operation, {**self.operation, "operation_id": "OP-2"}]})
        self.assertEqual(metrics["reconstructed"], 1)
        self.assertEqual(metrics["reconstruction_pct"], 50)

    def test_missing_snapshots_wrong_values_and_ambiguous_events_are_incomplete(self):
        self.assertFalse(complete({**self.row, "before": {}}))
        self.assertFalse(complete({**self.row, "committed": None}))
        metrics = evaluate([self.row, {**self.row, "event_id": "duplicate-observation"}], {"operations": [self.operation]})
        self.assertEqual(metrics["reconstructed"], 0)
        bad = copy.deepcopy(self.row)
        bad["after"]["city"] = "other"
        self.assertEqual(evaluate([bad], {"operations": [self.operation]})["reconstructed"], 0)

    def test_zero_denominator_and_noop_are_not_improvements(self):
        metrics = evaluate([], {"operations": [{**self.operation, "classification": "noop"}]})
        self.assertIsNone(metrics["reconstruction_pct"])
        self.assertIsNone(metrics["audit_coverage_pct"])
        self.assertEqual(metrics["excluded_noops_and_failures"], 1)
