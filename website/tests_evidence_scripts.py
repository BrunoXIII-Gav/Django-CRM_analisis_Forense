"""Pruebas del flujo de archivos con Docker simulado, sin tocar contenedores."""

import csv
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parent.parent


class EvidenceScriptsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name)
        (self.cwd / "docker-compose.yml").write_text("services: {}\n")
        executable_dir = self.cwd / "bin"
        executable_dir.mkdir()
        docker = executable_dir / "docker"
        docker.write_text('''#!/usr/bin/env python3
import os
import sys

args = sys.argv[1:]
command = args[-1]
if args == ["compose", "version"]:
    print("Docker Compose simulado")
elif "logs" in args:
    print("Log simulado de " + command)
elif command == "config":
    print("services: {}")
elif "mysqldump" in command:
    print("-- dump simulado")
    sys.exit(1 if os.environ.get("FAIL_DUMP") else 0)
elif "SELECT @@log_bin" in command:
    print(os.environ.get("LOG_BIN", "0"))
elif "mysqlbinlog" in command:
    print("binlog simulado")
    sys.exit(1 if os.environ.get("FAIL_BINLOG") else 0)
else:
    sys.exit(2)
''')
        docker.chmod(0o700)
        self.env = {**os.environ, "PATH": str(executable_dir) + os.pathsep + os.environ["PATH"]}
        self.base = self.cwd / "evidencias" / "CASO-01"

    def run_script(self, script, case="CASO-01", responsible='Ana, "Laboratorio"'):
        return subprocess.run(
            ["bash", str(PROJECT_DIR / script), case, responsible],
            cwd=self.cwd, env=self.env, capture_output=True, text=True,
        )

    def acquire(self):
        result = self.run_script("adquirir_evidencias.sh")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_adquisicion_verificacion_y_custodia(self):
        self.acquire()
        result = self.run_script("verificar_integridad.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("originales: OK", result.stdout)
        self.assertIn("trabajo: OK", result.stdout)
        for original in (self.base / "originales").iterdir():
            self.assertEqual(original.read_bytes(), (self.base / "trabajo" / original.name).read_bytes())
            self.assertEqual(original.stat().st_mode & 0o222, 0)
        with (self.base / "cadena_custodia.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertTrue(all(row["responsable"] == 'Ana, "Laboratorio"' for row in rows))
        self.assertEqual([row["sha256"] for row in rows[-2:]], ["OK", "OK"])
        self.assertEqual(self.base.stat().st_mode & 0o077, 0)

    def test_no_sobrescribe_caso_existente(self):
        self.acquire()
        manifest = (self.base / "manifiesto_sha256.txt").read_bytes()
        custody = (self.base / "cadena_custodia.csv").read_bytes()
        self.assertNotEqual(self.run_script("adquirir_evidencias.sh").returncode, 0)
        self.assertEqual((self.base / "manifiesto_sha256.txt").read_bytes(), manifest)
        self.assertEqual((self.base / "cadena_custodia.csv").read_bytes(), custody)

    def test_detecta_alteracion_en_ambas_copias(self):
        self.acquire()
        for directory in ("originales", "trabajo"):
            evidence = self.base / directory / "docker_web.log"
            evidence.chmod(0o600)
            evidence.write_text("alterado\n")
        result = self.run_script("verificar_integridad.sh")
        self.assertEqual(result.returncode, 1)
        self.assertIn("originales: FALLO", result.stdout)
        self.assertIn("trabajo: FALLO", result.stdout)

    def test_fallo_dump_no_publica_manifiesto(self):
        self.env["FAIL_DUMP"] = "1"
        self.assertNotEqual(self.run_script("adquirir_evidencias.sh").returncode, 0)
        self.assertFalse((self.base / "manifiesto_sha256.txt").exists())
        self.assertNotEqual(self.run_script("verificar_integridad.sh").returncode, 0)

    def test_binlog_opcional_conserva_estado_de_fallo(self):
        self.env.update(LOG_BIN="1", FAIL_BINLOG="1")
        self.acquire()
        self.assertFalse((self.base / "originales" / "mysql_binlog.txt").exists())
        self.assertIn("No se pudo", (self.base / "originales" / "estado_binlog.txt").read_text())
        self.assertEqual(self.run_script("verificar_integridad.sh").returncode, 0)

    def test_binlog_disponible_se_preserva(self):
        self.env["LOG_BIN"] = "1"
        self.acquire()
        self.assertTrue((self.base / "originales" / "mysql_binlog.txt").exists())
        self.assertEqual(self.run_script("verificar_integridad.sh").returncode, 0)

    def test_rechaza_caso_fuera_del_directorio(self):
        for script in ("adquirir_evidencias.sh", "verificar_integridad.sh"):
            self.assertNotEqual(self.run_script(script, case="../otro").returncode, 0)
        self.assertFalse((self.cwd / "evidencias").exists())

    def test_rechaza_responsable_de_varias_lineas(self):
        for script in ("adquirir_evidencias.sh", "verificar_integridad.sh"):
            self.assertNotEqual(self.run_script(script, responsible="Ana\nLuis").returncode, 0)

    def test_rechaza_manifiesto_vacio(self):
        self.base.mkdir(parents=True)
        (self.base / "manifiesto_sha256.txt").touch()
        self.assertNotEqual(self.run_script("verificar_integridad.sh").returncode, 0)
