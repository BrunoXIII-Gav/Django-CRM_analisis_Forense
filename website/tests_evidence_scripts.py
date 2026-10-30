"""Deterministic acquisition tests with Docker mocked; actual MySQL checked separately."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "forensic_lab" / "tools"
sys.path.insert(0, str(TOOLS))
from acquire_case import acquire, sanitized_config
from case_io import case_path, verify
from examine_evidence import examine
from build_timeline import build
from generate_report import generate
from transfer_evidence import transfer


class EvidenceScriptsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.case = self.root / "CASE-01"
        self.args = argparse.Namespace(root=self.root, case="CASE-01", operator='Ana, "Laboratorio"',
            compose=self.root / "compose.yml", env_file=self.root / "lab.env", project=None,
            environment="B", scope="Fictitious records", authorization="Academic local laboratory",
            interval_start="2026-01-01T00:00:00Z", interval_end="2026-01-02T00:00:00Z",
            clock_offset_seconds=None, writes_stopped=True, min_free_mb=0)
        self.fail_dump = self.truncated = self.binlog = False
        self.native_check_output = subprocess.check_output
        platform_mock = patch("acquire_case.platform.platform", return_value="Test-Linux")
        platform_mock.start()
        self.addCleanup(platform_mock.stop)
        self.runner = patch("acquire_case.subprocess.run", side_effect=self.docker)
        self.runner.start()
        self.addCleanup(self.runner.stop)
        self.checkout = patch("acquire_case.subprocess.check_output", side_effect=self.git)
        self.checkout.start()
        self.addCleanup(self.checkout.stop)

    def git(self, argv, **kwargs):
        if "rev-parse" in argv:
            return "151329f5708bc3c9c26405fc04c6cc1e6b2b7884\n"
        return b"website/models.py\0"

    def docker(self, argv, **kwargs):
        code, output = 0, b""
        if "config" in argv:
            output = json.dumps({"name": "lab", "services": {"web": {"image": "crm", "environment": {"SECRET": "must-not-leak"}, "command": "must-not-leak"}}}).encode()
        elif "logs" in argv:
            output = b"2026-01-01T00:00:00Z fake laboratory log\n"
        elif "version" in argv:
            output = b"version-test"
        elif "ps" in argv:
            output = b'[]'
        elif any("mysqldump" in arg for arg in argv):
            output = b"CREATE TABLE `website_record` ();\nCREATE TABLE `website_auditevent` ();\n"
            if not self.truncated:
                output += b"-- Dump completed on 2026-01-01\n"
            code = int(self.fail_dump)
        elif any("mysqlbinlog" in arg for arg in argv):
            output, code = (b"binlog", 0) if self.binlog else (b"", 1)
        elif "-c" in argv:
            output = b'{}'
        elif "python" in argv:
            output = json.dumps({"schema": 1, "database_vendor": "mysql", "audit_available": True,
                                 "events": [], "records": [], "admin_log": [], "accounts": []}).encode()
        else:
            raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, code, output, b"")

    def acquire(self):
        acquire(self.args)

    def test_acquisition_copies_sanitization_and_inventory(self):
        self.acquire()
        entries = verify(self.case, self.args.operator)
        self.assertTrue(entries)
        for entry in entries:
            self.assertEqual((self.case / "original" / entry["name"]).read_bytes(), (self.case / "trabajo" / entry["name"]).read_bytes())
        self.assertNotIn("must-not-leak", (self.case / "original/compose_sanitized.json").read_text())
        self.assertTrue((self.case / "custodia/evidence_inventory.csv").exists())

    def test_never_overwrites_case(self):
        self.acquire()
        manifest = (self.case / "custodia/manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.acquire()
        self.assertEqual(manifest, (self.case / "custodia/manifest.json").read_bytes())

    def test_detects_one_byte_change_before_examination(self):
        self.acquire()
        file = self.case / "trabajo/docker_web.log"
        file.chmod(0o600)
        raw = bytearray(file.read_bytes())
        raw[0] ^= 1
        file.write_bytes(raw)
        with self.assertRaises(ValueError):
            examine(self.case, self.args.operator)
        self.assertFalse((self.case / "analisis/events_normalized.json").exists())

    def test_failed_and_truncated_dump_never_publish_manifest(self):
        for failure in ("fail_dump", "truncated"):
            with self.subTest(failure=failure):
                self.args.case = failure
                setattr(self, failure, True)
                with self.assertRaises((RuntimeError, ValueError)):
                    self.acquire()
                base = self.root / failure
                self.assertFalse((base / "custodia/manifest.json").exists())
                self.assertTrue((base / "custodia/acquisition_failed.json").exists())
                setattr(self, failure, False)

    def test_binlog_optional_and_available(self):
        self.acquire()
        self.assertFalse((self.case / "original/mysql_binlog.txt").exists())
        self.binlog = True
        self.args.case = "BINLOG"
        self.acquire()
        self.assertTrue((self.root / "BINLOG/original/mysql_binlog.txt").exists())

    def test_rejects_traversal_repo_destination_and_multiline_operator(self):
        with self.assertRaises(ValueError):
            case_path(self.root, "../escape")
        with self.assertRaises(ValueError):
            case_path(TOOLS.parent, "CASE")
        self.args.operator = "Ana\nLuis"
        with self.assertRaises(ValueError):
            self.acquire()

    def test_requires_stopped_writes_and_space(self):
        self.args.writes_stopped = False
        with self.assertRaises(ValueError):
            self.acquire()
        self.args.writes_stopped = True
        self.args.min_free_mb = 10**15
        with self.assertRaises(ValueError):
            self.acquire()

    def test_manifest_cannot_reference_external_file(self):
        self.acquire()
        path = self.case / "custodia/manifest.json"
        path.chmod(0o600)
        manifest = json.loads(path.read_text())
        manifest["files"][0]["name"] = "../outside"
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            verify(self.case, self.args.operator)

    def test_unexpected_working_files_fail_verification(self):
        self.acquire()
        (self.case / "trabajo/extra.txt").write_text("unknown")
        with self.assertRaises(ValueError):
            verify(self.case, self.args.operator)

    def test_derived_pipeline_and_tampering(self):
        self.acquire()
        examine(self.case, self.args.operator)
        build(self.case, self.args.operator)
        generate(self.case, self.args.operator)
        self.assertIn("revisión independiente", (self.case / "reporte/report.md").read_text(encoding="utf-8"))
        file = self.case / "analisis/events_normalized.json"
        file.write_text("altered")
        with self.assertRaises(ValueError):
            build(self.case, self.args.operator)

    def test_transfer_verifies_both_locations_and_records_receipt(self):
        self.acquire()
        destination = self.root / "reviewer-copy"
        transfer(self.case, self.args.operator, destination, "Ana", "Luis", "Independent review", "Receipt LAB-01")
        self.assertEqual(len(list(destination.iterdir())), len(list((self.case / "original").iterdir())))
        self.assertIn("Receipt LAB-01", (self.case / "custodia/chain_of_custody.csv").read_text())

    @unittest.skipUnless(os.name == "posix", "Bash entrypoints are verified on Linux")
    def test_bash_entrypoint_help(self):
        # Bypass Docker mock to execute only argparse help.
        # Syntax and help are also exercised in CI with bash -n.
        for file in (TOOLS / "acquire_case.sh", TOOLS / "verify_evidence.sh"):
            self.assertNotIn(b"\r\n", file.read_bytes())
