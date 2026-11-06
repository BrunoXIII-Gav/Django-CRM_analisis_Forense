"""Permission, evidence isolation and truthful presentation of case artifacts."""
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_derived(case, relative, data):
    path = case / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    write_json(Path(str(path) + ".provenance.json"), {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "derived_id": "CASE-VISTA-PRUEBA/D-001", "sources": [],
    })


def make_case(root):
    """Synthetic test data only, never published as laboratory evidence."""
    case = root / "CASE-VISTA-PRUEBA"
    for directory in ("original", "trabajo", "custodia", "analisis", "reporte"):
        (case / directory).mkdir(parents=True)
    metadata = {"case_id": case.name, "scope": "Vista de prueba con clientes ficticios",
                "environment": "B", "operator": "Analista de prueba", "authorization": "Prueba de interfaz",
                "interval_start": "2026-01-01T00:00:00Z", "interval_end": "2026-01-01T00:01:00Z",
                "started_at_utc": "2026-01-01T00:02:00Z", "finished_at_utc": "2026-01-01T00:02:02Z",
                "clock_offset_seconds": None, "binlog": "Unavailable in test fixture",
                "commands": [{"argv": ["DO_NOT_SHOW_RAW_COMMANDS"]}]}
    write_json(case / "trabajo/acquisition.json", metadata)
    entries = []
    for i, (name, data) in enumerate((("acquisition.json", (case / "trabajo/acquisition.json").read_bytes()),
                                     ("sources.json", b'RAW_SOURCES_SECRET'), ("mysql_dump.sql", b'SQL_PASSWORD_SECRET')), 1):
        for directory in ("original", "trabajo"):
            (case / directory / name).write_bytes(data)
        entries.append({"name": name, "evidence_id": f"{case.name}/E-{i:03}", "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(), "source": "MySQL B",
                        "acquired_at_utc": "2026-01-01T00:02:01Z"})
    write_json(case / "custodia/manifest.json", {"case_id": case.name, "files": entries})
    with (case / "custodia/chain_of_custody.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["evidence_id", "action", "time_utc", "operator", "result", "sha256"])
        writer.writeheader()
        for entry in entries:
            for directory in ("original", "trabajo"):
                writer.writerow({"evidence_id": entry["evidence_id"], "action": "VERIFY_" + directory,
                                 "time_utc": "2026-01-01T00:03:00Z", "operator": "Analista de prueba",
                                 "result": "OK", "sha256": entry["sha256"]})
    event = {"event_id": "event-test-1", "time_utc": "2026-01-01T00:00:01Z", "actor_username": "lab_operator",
             "record_id": "1", "action": "UPDATE", "channel": "web", "request_id": "request-test-1",
             "session_correlation_id": "session-test-1", "before": {"city": "Lima", "password": "SNAPSHOT_SECRET"},
             "after": {"city": "Arequipa"}, "outcome": "success", "support": "single_source",
             "evidence_id": entries[1]["evidence_id"], "source_file": "sources.json", "source_locator": "events[0]"}
    write_derived(case, "analisis/events_normalized.json", [event])
    write_derived(case, "analisis/changes_by_record.json", [])
    write_derived(case, "analisis/timeline.md", "# Cronología de prueba")
    write_derived(case, "analisis/inconsistencies.txt", "Contraste de solicitud ausente")
    write_derived(case, "reporte/report.md", "# Informe de prueba\n<script>alert('xss')</script>\nSin revisión independiente.")
    write_derived(case, "reporte/metrics.json", {"reconstruction_pct": 0, "integrity_pct": 100,
                                               "custody_transfer_pct": None, "acquisition_seconds": 2})
    (root / "truth-B.json").write_text("GROUND_TRUTH_SECRET", encoding="utf-8")
    return case


class CaseViewerTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.override = override_settings(FORENSIC_CASES_ROOT=self.root)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.case = make_case(self.root)
        self.user = User.objects.create_user("viewer", password="test", is_staff=True)
        self.user.user_permissions.add(Permission.objects.get(codename="view_auditevent"))
        self.client.force_login(self.user)
        self.url = reverse("forensic_case", args=[self.case.name])

    def test_access_requires_login_staff_and_audit_permission(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        operator = User.objects.create_user("operator", password="test")
        self.client.force_login(operator)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        operator.is_staff = True
        operator.save()
        self.assertEqual(self.client.get(reverse("forensic_cases")).status_code, 403)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_all_tabs_and_menu_read_without_mutating_evidence(self):
        snapshot = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        for tab in ("procedimiento", "evidencias", "reconstruccion", "informe"):
            response = self.client.get(self.url, {"tab": tab})
            self.assertEqual(response.status_code, 200)
            for hidden in ("SQL_PASSWORD_SECRET", "RAW_SOURCES_SECRET", "SNAPSHOT_SECRET", "GROUND_TRUTH_SECRET", "DO_NOT_SHOW_RAW_COMMANDS"):
                self.assertNotContains(response, hidden)
        self.assertContains(self.client.get(reverse("home")), "Casos forenses")
        self.assertEqual(snapshot, {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()})

    def test_reconstruction_shows_snapshots_session_and_source_link(self):
        response = self.client.get(self.url, {"tab": "reconstruccion"})
        for text in ("Lima", "Arequipa", "session-test-1", "request-test-1", "events[0]", "Observaciones y límites"):
            self.assertContains(response, text)
        self.assertContains(response, "?tab=evidencias#evidence-2")
        self.assertContains(self.client.get(self.url, {"tab": "reconstruccion", "q": "session-test-1"}), "Arequipa")
        self.assertContains(self.client.get(self.url, {"tab": "reconstruccion", "q": "no-such-session"}), "No hay coincidencias")

    def test_empty_missing_and_partial_cases_have_honest_states(self):
        with override_settings(FORENSIC_CASES_ROOT=self.root / "absent"):
            self.assertContains(self.client.get(reverse("forensic_cases")), "Aún no hay expedientes")
        partial = self.root / "CASE-PARTIAL"
        write_json(partial / "custodia/acquisition_failed.json", {"error": "SECRET_ERROR"})
        response = self.client.get(reverse("forensic_case", args=[partial.name]))
        self.assertContains(response, "Adquisición parcial o fallida")
        self.assertContains(response, "Sin información suficiente")
        self.assertNotContains(response, "SECRET_ERROR")
        self.assertEqual(self.client.get(reverse("forensic_case", args=["UNKNOWN"])).status_code, 404)

    def test_changed_derived_or_metadata_are_not_presented(self):
        (self.case / "analisis/events_normalized.json").write_text('[{"actor_username":"CORRUPTED"}]')
        response = self.client.get(self.url, {"tab": "reconstruccion"})
        self.assertContains(response, "hash discrepante")
        self.assertNotContains(response, "CORRUPTED")
        (self.case / "trabajo/acquisition.json").write_text('{"operator":"ALTERED"}')
        self.assertNotContains(self.client.get(self.url), "ALTERED")

    def test_verification_is_historical_and_wrong_record_digest_is_discrepancy(self):
        # Changing a large evidence file does not trigger silent verification on GET.
        (self.case / "original/mysql_dump.sql").write_text("Changed after last recorded check")
        response = self.client.get(self.url, {"tab": "evidencias"})
        self.assertContains(response, "Coincidencia registrada")
        self.assertContains(response, "registros históricos")
        path = self.case / "custodia/chain_of_custody.csv"
        with path.open("a") as stream:
            stream.write(f"{self.case.name}/E-003,VERIFY_original,2026-01-02T00:00:00Z,Analyst,OK,{'0' * 64}\n")
        self.assertContains(self.client.get(self.url, {"tab": "evidencias"}), "Discrepancia registrada")

    def test_latest_report_numeric_revision_and_matching_metrics_safe_text(self):
        write_derived(self.case, "reporte/report-v2.md", "Older report")
        write_derived(self.case, "reporte/metrics-v2.json", {"reconstruction_pct": 75})
        write_derived(self.case, "reporte/report-v10.md", "Latest report <img src=x onerror=alert(1)>")
        response = self.client.get(self.url, {"tab": "informe"})
        self.assertContains(response, "report-v10.md")
        self.assertContains(response, "&lt;img")
        self.assertNotContains(response, "<img")
        self.assertNotContains(response, "75.00")
        self.assertContains(response, "Sin información")
        self.assertContains(response, "Sin constancia en el visor")

    def test_zero_is_not_missing_and_report_html_is_escaped(self):
        response = self.client.get(self.url, {"tab": "informe"})
        self.assertContains(response, "0.00")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")

    def test_untrusted_symlinks_and_manifest_paths_are_rejected(self):
        external = self.root / "external.json"
        external.write_text('[{"actor_username":"EXTERNAL_SECRET"}]')
        events = self.case / "analisis/events_normalized.json"
        events.unlink()
        events.symlink_to(external)
        self.assertNotContains(self.client.get(self.url, {"tab": "reconstruccion"}), "EXTERNAL_SECRET")
        (self.root / "CASE-LINK").symlink_to(self.case, target_is_directory=True)
        self.assertEqual(self.client.get(reverse("forensic_case", args=["CASE-LINK"])).status_code, 404)
        write_json(self.case / "custodia/manifest.json", {"files": [{"name": "../external.json", "evidence_id": "X", "sha256": "0" * 64, "size": 1}]})
        self.assertContains(self.client.get(self.url), "no válidos")
        self.assertNotContains(self.client.get(reverse("forensic_cases")), "CASE-LINK")

    def test_malformed_inputs_are_reported_without_server_errors(self):
        write_derived(self.case, "analisis/events_normalized.json", [{"action": {}, "support": [], "outcome": {}, "before": []}])
        self.assertEqual(self.client.get(self.url, {"tab": "reconstruccion"}).status_code, 200)
        (self.case / "custodia/manifest.json").write_text("broken json")
        self.assertContains(self.client.get(self.url), "formato JSON no válido")

    def test_reconstruction_pagination_preserves_the_search_and_handles_non_files(self):
        rows = [{"event_id": f"EV-{i:03}", "actor_username": "matching-account", "record_id": str(i)}
                for i in range(60)]
        write_derived(self.case, "analisis/events_normalized.json", rows)
        response = self.client.get(self.url, {"tab": "reconstruccion", "q": "matching-account", "page": 2})
        self.assertEqual(len(response.context["events_page"]), 25)
        self.assertContains(response, "q=matching-account")
        self.assertContains(response, "Cliente 25")
        path = self.case / "analisis/events_normalized.json"
        path.unlink()
        path.mkdir()
        response = self.client.get(self.url, {"tab": "reconstruccion"})
        self.assertContains(response, "ruta no permitida")
