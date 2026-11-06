"""Read-only presentation of existing case files. No acquisition or custody writes.

Only known artifacts are read. SQL, raw logs, sources.json, credentials and the
scenario's ground truth are never opened by this module. Files and intermediate
directories must not be symlinks. A derived artifact is displayed only when its
bytes match its provenance record; this is distinct from a recorded verification
of the original evidence and from independent review.
"""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re

from django.conf import settings

from .snapshots import SNAPSHOT_FIELDS

CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\Z")
SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
REPORT = re.compile(r"report(?:-v([1-9][0-9]*))?\.md\Z")
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 10000
MARKERS = ("custodia/manifest.json", "custodia/manifest.partial.json", "custodia/acquisition_failed.json")
METRICS = (
    ("reconstruction_pct", "Reconstrucción completa", "%"),
    ("audit_coverage_pct", "Cobertura de auditoría", "%"),
    ("integrity_pct", "Integridad registrada", "%"),
    ("custody_transfer_pct", "Transferencias documentadas", "%"),
    ("acquisition_seconds", "Tiempo de adquisición", "s"),
)
FIELD_LABELS = {
    "id": "ID", "first_name": "Nombre", "last_name": "Apellido", "email": "Correo",
    "phone": "Teléfono", "address": "Dirección", "city": "Ciudad", "state": "Estado",
    "zipcode": "Código postal", "created_at": "Creación", "updated_at": "Actualización",
}


def short(value, limit=500):
    return str(value)[:limit] if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


class CaseReader:
    def __init__(self, root, case_id):
        root = Path(root).resolve()
        if not CASE_ID.fullmatch(case_id):
            raise FileNotFoundError
        self.path = root / case_id
        if self.path.is_symlink() or not self.path.is_dir():
            raise FileNotFoundError
        self.case_id = case_id
        self.issues = []
        self.artifact_dates = {}

    def issue(self, message):
        if message not in self.issues and len(self.issues) < 30:
            self.issues.append(message)

    def safe_path(self, relative):
        parts = Path(relative).parts
        if not parts or Path(relative).is_absolute() or any(p in ("..", ".") for p in parts):
            raise ValueError
        path = self.path
        for part in parts:
            path = path / part
            if path.is_symlink():
                raise ValueError
        if not path.resolve().is_relative_to(self.path):
            raise ValueError
        return path

    def read(self, relative):
        try:
            path = self.safe_path(relative)
            if not path.exists():
                return None
            if not path.is_file():
                raise ValueError
            with path.open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                self.issue(f"{relative}: supera el tamaño admitido por el visor.")
                return None
            return data
        except (OSError, ValueError):
            self.issue(f"{relative}: archivo inaccesible o ruta no permitida.")
            return None

    def decode_json(self, data, relative, kind=dict):
        if data is None:
            return None
        try:
            value = json.loads(data)
            if not isinstance(value, kind):
                raise ValueError
            return value
        except (ValueError, UnicodeError, RecursionError):
            self.issue(f"{relative}: formato JSON no válido.")
            return None

    def json(self, relative, kind=dict):
        return self.decode_json(self.read(relative), relative, kind)

    def derived(self, relative, kind=dict):
        data = self.read(relative)
        if data is None:
            return None
        meta = self.json(relative + ".provenance.json")
        if not meta or meta.get("sha256") != hashlib.sha256(data).hexdigest():
            self.issue(f"{relative}: procedencia ausente o hash discrepante; contenido no mostrado.")
            return None
        self.artifact_dates[relative] = short(meta.get("created_at_utc"))
        if kind is str:
            try:
                text = data.decode("utf-8")
                if not text.strip():
                    self.issue(f"{relative}: archivo de texto vacío.")
                    return None
                return text
            except UnicodeError:
                self.issue(f"{relative}: texto UTF-8 no válido.")
                return None
        return self.decode_json(data, relative, kind)

    def manifest(self):
        manifest = self.json("custodia/manifest.json")
        if manifest is None:
            return []
        files = manifest.get("files")
        if not isinstance(files, list) or not files or len(files) > MAX_ROWS:
            self.issue("El manifiesto no contiene un inventario válido.")
            return []
        entries, names, ids = [], set(), set()
        for item in files:
            if not isinstance(item, dict):
                self.issue("El manifiesto contiene entradas no válidas.")
                continue
            name, digest, eid = item.get("name"), item.get("sha256"), item.get("evidence_id")
            size = item.get("size")
            if (not isinstance(name, str) or not name or name in (".", "..") or
                    "/" in name or "\\" in name or name in names or
                    not isinstance(eid, str) or not eid or eid in ids or
                    not isinstance(digest, str) or not SHA256.fullmatch(digest) or
                    type(size) is not int or size < 0):
                self.issue("El manifiesto contiene rutas, identificadores o hashes no válidos.")
                continue
            names.add(name)
            ids.add(eid)
            entries.append({"name": name, "evidence_id": short(eid), "sha256": digest.lower(),
                            "size": size, "source": short(item.get("source")),
                            "acquired_at": short(item.get("acquired_at_utc")), "anchor": len(entries) + 1})
        return entries

    def custody(self):
        data = self.read("custodia/chain_of_custody.csv")
        if data is None:
            return []
        try:
            reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
            if not {"evidence_id", "action", "time_utc", "result"}.issubset(reader.fieldnames or []):
                raise ValueError
            rows = []
            for i, row in enumerate(reader):
                if i >= MAX_ROWS:
                    self.issue("Custodia: el visor muestra los primeros 10000 registros.")
                    break
                rows.append({key: short(row.get(key)) for key in
                             ("evidence_id", "action", "time_utc", "operator", "result", "sha256")})
            return rows
        except (ValueError, UnicodeError, csv.Error):
            self.issue("custodia/chain_of_custody.csv: formato no válido.")
            return []

    def acquisition(self, entries):
        data = self.read("trabajo/acquisition.json")
        if data is None:
            return {}
        entry = next((e for e in entries if e["name"] == "acquisition.json"), None)
        if not entry or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            self.issue("acquisition.json: no coincide con el manifiesto; metadatos no mostrados.")
            return {}
        meta = self.decode_json(data, "trabajo/acquisition.json") or {}
        if meta.get("case_id") != self.case_id:
            self.issue("acquisition.json: el identificador no corresponde al expediente.")
            return {}
        return {key: short(meta.get(key), 2000) for key in (
            "environment", "scope", "operator", "authorization", "interval_start", "interval_end",
            "started_at_utc", "finished_at_utc", "application_commit", "docker_version", "compose_version")}

    def latest_report(self):
        try:
            directory = self.safe_path("reporte")
            candidates = []
            if directory.is_dir():
                for path in directory.iterdir():
                    match = REPORT.fullmatch(path.name)
                    if match:
                        candidates.append((int(match[1] or 1), path.name))
            return max(candidates)[1] if candidates else None
        except (OSError, ValueError):
            self.issue("reporte: directorio inaccesible o ruta no permitida.")
            return None

    def load(self, detail=True):
        entries = self.manifest()
        meta = self.acquisition(entries)
        partial = self.read("custodia/manifest.partial.json") is not None
        failed = self.read("custodia/acquisition_failed.json") is not None
        case = {"id": self.case_id, "metadata": meta, "evidence": entries, "issues": self.issues,
                "acquisition_available": bool(entries and meta), "acquisition_failed": failed or partial}
        if not detail:
            return case
        custody = self.custody()
        for entry in entries:
            entry["checks"] = []
            for directory, label in (("original", "Original"), ("trabajo", "Copia de trabajo")):
                records = [r for r in custody if r["evidence_id"] == entry["evidence_id"] and
                           r["action"] == "VERIFY_" + directory]
                last = records[-1] if records else {}
                state = "none"
                if last:
                    state = "match" if last["result"] == "OK" and last["sha256"].lower() == entry["sha256"] else "mismatch"
                entry["checks"].append({"label": label, "state": state, "date": last.get("time_utc"),
                                        "operator": last.get("operator")})
        rows = self.derived("analisis/events_normalized.json", list)
        changes = self.derived("analisis/changes_by_record.json", list)
        timeline = self.derived("analisis/timeline.md", str)
        inconsistencies = self.derived("analisis/inconsistencies.txt", str)
        restore = self.derived("analisis/restore_validation.json")
        report_name = self.latest_report()
        report = self.derived("reporte/" + report_name, str) if report_name else None
        suffix = report_name[len("report"):-len(".md")] if report_name else ""
        metrics = self.derived(f"reporte/metrics{suffix}.json") if report_name else None
        metric_cards = []
        for key, label, unit in METRICS:
            value = (metrics or {}).get(key)
            try:
                valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
            except OverflowError:
                valid = False
            if unit == "%":
                valid = valid and value <= 100
            metric_cards.append({"label": label, "value": f"{value:.2f}" if valid else None, "unit": unit})
        events = []
        if rows is not None:
            if len(rows) > MAX_ROWS:
                self.issue("Reconstrucción: el visor muestra los primeros 10000 eventos.")
            for row in rows[:MAX_ROWS]:
                if isinstance(row, dict):
                    events.append(present_event(row, entries))
                else:
                    self.issue("La reconstrucción contiene eventos no válidos.")
        events.sort(key=lambda r: (r["time_utc"], r["event_id"]))
        case.update({"custody": custody[-100:], "events": events, "event_count": len(events),
                     "metric_cards": metric_cards, "report": report, "report_name": report_name,
                     "inconsistencies": inconsistencies, "restore_ok": (restore or {}).get("result") == "OK",
                     "stages": [
                         {"name": "Recolección", "number": "01", "available": bool(entries and meta),
                          "incident": failed or partial,
                          "recorded_at": meta.get("finished_at_utc"),
                          "description": "Fuentes adquiridas, inventario y metadatos del caso.",
                          "artifacts": "acquisition.json · manifest.json · chain_of_custody.csv", "tab": "evidencias"},
                         {"name": "Examen", "number": "02", "available": rows is not None and changes is not None,
                          "recorded_at": self.artifact_dates.get("analisis/events_normalized.json"),
                          "description": "Datos normalizados y comparación de campos en las copias.",
                          "artifacts": "events_normalized.json · changes_by_record.json", "tab": "reconstruccion"},
                         {"name": "Análisis", "number": "03", "available": timeline is not None,
                          "recorded_at": self.artifact_dates.get("analisis/timeline.md"),
                          "description": "Cronología y referencias para interpretar los hechos.",
                          "artifacts": "timeline.md · inconsistencies.txt", "tab": "reconstruccion"},
                         {"name": "Reporte", "number": "04", "available": report is not None,
                          "recorded_at": self.artifact_dates.get("reporte/" + report_name) if report_name else None,
                          "description": "Informe registrado. La revisión independiente se documenta aparte.",
                          "artifacts": report_name or "Sin informe disponible", "tab": "informe"},
                     ]})
        return case


def present_event(row, entries):
    fields = ("event_id", "time_utc", "time_original", "actor_username", "record_id", "action", "channel",
              "request_id", "session_correlation_id", "evidence_id", "source_file", "source_locator")
    event = {key: short(row.get(key)) for key in fields}
    event["action_label"] = {"CREATE": "Creación", "UPDATE": "Modificación", "DELETE": "Eliminación"}.get(event["action"], "Observación")
    event["outcome"] = {"success": "Cambio confirmado", "noop": "Sin cambios efectivos",
                        "native_observation": "Observación parcial", "legacy_unknown": "Histórico sin confirmar"}.get(short(row.get("outcome")), "No determinado")
    event["support"] = {"confirmed_with_request_contrast": "Con contraste de solicitud",
                        "single_source": "Sustentado en una fuente"}.get(short(row.get("support")), "Sin clasificación registrada")
    entry = next((e for e in entries if e["evidence_id"] == event["evidence_id"]), None)
    event["evidence_anchor"] = entry["anchor"] if entry else None
    refs = row.get("corroboration")
    event["corroboration"] = [short(ref) for ref in refs[:20]] if isinstance(refs, list) else []
    before = row.get("before") if isinstance(row.get("before"), dict) else {}
    after = row.get("after") if isinstance(row.get("after"), dict) else {}
    event["snapshots"] = []
    for field in SNAPSHOT_FIELDS:
        if field in before or field in after:
            event["snapshots"].append({"field": FIELD_LABELS[field],
                                       "before": short(before[field], 2000) if field in before else "No disponible / no aplica",
                                       "after": short(after[field], 2000) if field in after else "No disponible / no aplica",
                                       "changed": before.get(field) != after.get(field)})
    return event


def list_cases():
    root = Path(settings.FORENSIC_CASES_ROOT)
    try:
        directories = sorted(root.iterdir(), key=lambda p: p.name, reverse=True)
    except OSError:
        return [], False
    cases = []
    for directory in directories:
        if not CASE_ID.fullmatch(directory.name) or directory.is_symlink() or not directory.is_dir():
            continue
        try:
            reader = CaseReader(root, directory.name)
            recognized = any(reader.safe_path(marker).exists() for marker in MARKERS)
            if recognized:
                cases.append(reader.load(detail=False))
        except (OSError, ValueError):
            continue
    return cases, True
