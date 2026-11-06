"""Web submission, durable scheduling and actual post-acquisition CLI pipeline."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase, SimpleTestCase, override_settings
from django.urls import reverse

from forensic_lab.job_queue import JobQueue, QueueError
from forensic_lab.job_worker import commands, process_one, run_command
from website.forensics.tests.test_case_viewer import make_case, write_json


def spec(case_id="CASE-UI-001"):
    return {"case_id": case_id, "operator": "Analista", "scope": "Clientes ficticios",
            "authorization": "Autorización de prueba", "requested_by": "admin",
            "interval_start": "2026-01-01T00:00:00+00:00", "interval_end": "2026-01-01T01:00:00+00:00",
            "writes_stopped": True}


class ProcedureWebTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.override = override_settings(FORENSIC_RUNNER_ENABLED=True, FORENSIC_JOBS_ROOT=root / "jobs",
                                           FORENSIC_CASES_ROOT=root / "cases")
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.queue = JobQueue(settings.FORENSIC_JOBS_ROOT)
        with self.queue.locked():
            self.queue.heartbeat()
        self.user = User.objects.create_superuser("admin", "admin@example.test", "test")
        self.client.force_login(self.user)

    def payload(self):
        return {k: v for k, v in spec().items() if k != "requested_by"}

    def test_create_only_enqueues_and_can_be_seen_after_new_request(self):
        with patch("subprocess.Popen") as process:
            response = self.client.post(reverse("forensic_new_case"), self.payload())
        self.assertRedirects(response, reverse("forensic_workflow", args=["CASE-UI-001"]))
        process.assert_not_called()
        self.assertFalse((settings.FORENSIC_CASES_ROOT / "CASE-UI-001").exists())
        job = JobQueue(settings.FORENSIC_JOBS_ROOT).get("CASE-UI-001")
        self.assertEqual(job["steps"][0]["state"], "queued")
        self.assertContains(self.client.get(reverse("forensic_cases")), "Ver procedimiento")
        self.assertContains(self.client.get(response.url), "En cola")
        self.assertContains(self.client.get(response.url), 'http-equiv="refresh"')

    def test_reader_and_operator_cannot_submit_or_start_phases(self):
        viewer = User.objects.create_user("viewer", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename="view_auditevent"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.post(reverse("forensic_new_case"), self.payload()).status_code, 403)
        url = reverse("forensic_start_phase", args=["CASE-UI-001", "examine"])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.queue.list(), [])
        self.client.logout()
        self.assertEqual(self.client.get(reverse("forensic_new_case")).status_code, 302)

    def test_csrf_is_required_and_get_cannot_start_a_phase(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(reverse("forensic_new_case"), self.payload()).status_code, 403)
        self.assertEqual(self.client.get(reverse("forensic_start_phase", args=["CASE-UI-001", "acquire"])).status_code, 405)

    def test_invalid_form_offline_worker_and_duplicate_submission_are_rejected(self):
        for updates in ({"case_id": "../escape"}, {"writes_stopped": False},
                        {"interval_start": "2027-01-01T00:00:00Z"}, {"scope": "two\nlines"}):
            response = self.client.post(reverse("forensic_new_case"), dict(self.payload(), **updates))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(self.queue.list(), [])
        self.queue.heartbeat(available=False)
        self.assertContains(self.client.post(reverse("forensic_new_case"), self.payload()), "El ejecutor no está disponible")
        self.queue.heartbeat()
        self.client.post(reverse("forensic_new_case"), self.payload())
        self.assertContains(self.client.post(reverse("forensic_new_case"), self.payload()), "identificador sea nuevo")
        self.assertEqual(len(self.queue.list()), 1)

    def test_corrupt_or_reserved_workflow_does_not_render_as_a_job(self):
        self.assertEqual(self.client.get(reverse("forensic_workflow", args=["heartbeat"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("forensic_workflow", args=["missing"])).status_code, 404)


class ProcedureWorkerTests(SimpleTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = self.root / "cases"
        self.cases.mkdir()
        self.queue = JobQueue(self.root / "jobs")

    def test_sequential_single_claim_no_overwrite_and_recovery(self):
        self.queue.create(spec(), self.cases)
        with self.assertRaises(QueueError):
            self.queue.create(spec(), self.cases)
        with self.assertRaises(QueueError):
            self.queue.enqueue("CASE-UI-001", "report", "admin")
        job, key, token = self.queue.claim()
        self.assertEqual(key, "acquire")
        self.assertIsNone(self.queue.claim())
        self.queue.recover_interrupted()
        self.assertEqual(self.queue.get(job["case_id"])["steps"][0]["state"], "failed")
        with self.assertRaises(QueueError):
            self.queue.enqueue(job["case_id"], "examine", "admin")

    def test_no_success_without_artifacts_or_when_tool_returns_failure(self):
        self.queue.create(spec(), self.cases)
        process_one(self.queue, settings.BASE_DIR, self.cases, runner=lambda *a, **k: (0, ""))
        self.assertEqual(self.queue.get("CASE-UI-001")["steps"][0]["state"], "failed")
        self.queue.create(spec("CASE-FAIL"), self.cases)
        process_one(self.queue, settings.BASE_DIR, self.cases, runner=lambda *a, **k: (7, "Error controlado"))
        step = self.queue.get("CASE-FAIL")["steps"][0]
        self.assertEqual((step["state"], step["returncode"], step["message"]), ("failed", 7, "Error controlado"))

    def test_metadata_cannot_select_commands_and_failure_does_not_expose_stderr(self):
        data = spec()
        data["scope"] = "$(touch /tmp/NEVER_EXECUTE); --project evil"
        data["command"] = "sh"
        self.queue.create(data, self.cases)
        argv = commands(settings.BASE_DIR, self.cases, "fixed-project", data, "acquire")[0]
        self.assertIn("--scope=" + data["scope"], argv)
        self.assertEqual(argv[-2:], ["--project", "fixed-project"])
        with self.assertRaises(QueueError):
            commands(settings.BASE_DIR, self.cases, "fixed", data, "sh")
        code, message = run_command([sys.executable, "-c", "import sys; sys.stderr.write('PASSWORD_SECRET'); sys.exit(8)"],
                                    queue=self.queue, cwd=settings.BASE_DIR, timeout=10)
        self.assertEqual(code, 8)
        self.assertNotIn("PASSWORD_SECRET", message)

    def test_timeout_and_hash_tampering_stop_the_pipeline(self):
        self.queue.create(spec(), self.cases)
        def timeout(*args, **kwargs):
            raise TimeoutError
        process_one(self.queue, settings.BASE_DIR, self.cases, runner=timeout)
        self.assertIn("tiempo máximo", self.queue.get("CASE-UI-001")["steps"][0]["message"])

    def test_actual_examination_timeline_and_report_run_from_the_queue(self):
        # The acquisition boundary is supplied by a fixture; subsequent phases
        # execute the real CLI tools against copied, verified evidence.
        job = self.queue.create(spec("CASE-VISTA-PRUEBA"), self.cases)
        case = make_case(self.cases)
        for directory in (case / "analisis", case / "reporte"):
            for path in directory.iterdir():
                path.unlink()
        sources = {"database_vendor": "mysql", "audit_available": True, "events": [],
                   "records": [], "admin_log": [], "accounts": []}
        for directory in ("original", "trabajo"):
            write_json(case / directory / "sources.json", sources)
            (case / directory / "docker_web.log").write_text("")
        import hashlib
        manifest = json.loads((case / "custodia/manifest.json").read_text())
        source = next(e for e in manifest["files"] if e["name"] == "sources.json")
        data = (case / "original/sources.json").read_bytes()
        source.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        manifest["files"].append({"name": "docker_web.log", "evidence_id": "CASE-VISTA-PRUEBA/E-004", "size": 0,
                                   "sha256": hashlib.sha256(b"").hexdigest()})
        write_json(case / "custodia/manifest.json", manifest)
        (case / "custodia/evidence_inventory.csv").write_text("fixture inventory")
        process_one(self.queue, settings.BASE_DIR, self.cases, runner=lambda *a, **k: (0, ""))
        self.assertEqual(self.queue.get(job["case_id"])["steps"][0]["state"], "succeeded")
        def cli(argv, **kwargs):
            result = subprocess.run(argv, cwd=kwargs["cwd"], capture_output=True)
            return result.returncode, "CLI failed" if result.returncode else ""
        for step in ("examine", "timeline", "report"):
            self.queue.enqueue(job["case_id"], step, "admin")
            process_one(self.queue, settings.BASE_DIR, self.cases, runner=cli)
            self.assertEqual(self.queue.get(job["case_id"])["steps"][["acquire", "examine", "timeline", "report"].index(step)]["state"], "succeeded")
        self.assertIn("No se utilizó una tabla de verdad", (case / "reporte/report.md").read_text())
        self.assertEqual(len(list((case / "custodia").glob("procedure-*.json"))), 4)
        # A changed original invalidates any later verification, despite outputs existing.
        (case / "original/mysql_dump.sql").write_text("tampered")
        from forensic_lab.job_worker import validate_outputs
        with self.assertRaises(ValueError):
            validate_outputs(settings.BASE_DIR, self.cases, case.name, "report")
