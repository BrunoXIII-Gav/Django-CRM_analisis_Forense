"""Persistent, single-worker queue for the local Linux laboratory.

The web process submits metadata and fixed phase names, never commands or paths.
Case evidence and this operational journal live in separate directories/volumes.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

STEPS = (("acquire", "Recolección"), ("examine", "Examen"),
         ("timeline", "Reconstrucción"), ("report", "Informe"))
CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\Z")


class QueueError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_spec(spec):
    if not isinstance(spec, dict) or not CASE_ID.fullmatch(str(spec.get("case_id", ""))):
        raise QueueError("El identificador solo admite letras, números, guiones y guiones bajos.")
    for name, limit in (("operator", 150), ("scope", 1000), ("authorization", 1000), ("requested_by", 150)):
        value = spec.get(name)
        if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
            raise QueueError("Responsable, alcance y autorización deben contener texto válido en una línea.")
    if spec.get("writes_stopped") is not True:
        raise QueueError("Confirma que detuviste nuevas modificaciones de clientes.")
    try:
        start, end = (datetime.fromisoformat(spec[k].replace("Z", "+00:00"))
                      for k in ("interval_start", "interval_end"))
        if start.tzinfo is None or end.tzinfo is None or start > end:
            raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError):
        raise QueueError("El intervalo debe incluir zona horaria y tener inicio anterior o igual al fin.")
    return {key: spec[key] for key in ("case_id", "operator", "scope", "authorization", "requested_by",
                                      "writes_stopped", "interval_start", "interval_end")}


class JobQueue:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, case_id):
        if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
            raise QueueError("Identificador de caso no válido.")
        path = self.root / (case_id + ".json")
        if path.is_symlink():
            raise QueueError("La ruta de la corrida no está permitida.")
        return path

    def _read(self, path):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
                raise QueueError("Registro de ejecución no válido.")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError
            return data
        except FileNotFoundError:
            raise QueueError("Corrida no encontrada.")
        except (OSError, ValueError, UnicodeError, RecursionError):
            raise QueueError("No se pudo leer el registro de ejecución.")

    def _write(self, path, data):
        # Replacing a complete file prevents readers from seeing partial JSON.
        handle, temporary = tempfile.mkstemp(prefix=".state-", dir=self.root)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @contextmanager
    def locked(self, worker=False):
        # The runner is deployed in Linux containers, including on Docker Desktop.
        import fcntl
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.root / (".worker.lock" if worker else ".queue.lock")
        if path.is_symlink():
            raise QueueError("La ruta de bloqueo no está permitida.")
        with path.open("a") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | (fcntl.LOCK_NB if worker else 0))
            except BlockingIOError:
                raise QueueError("Ya existe un ejecutor activo para esta cola.")
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def get(self, case_id):
        job = self._read(self._path(case_id))
        steps = job.get("steps")
        if (job.get("schema") != 1 or job.get("case_id") != case_id or
                not isinstance(steps, list) or len(steps) != len(STEPS) or
                any(not isinstance(step, dict) or step.get("key") != key or
                    step.get("state") not in ("pending", "queued", "running", "succeeded", "failed")
                    for step, (key, _) in zip(steps, STEPS))):
            raise QueueError("Registro de corrida no válido.")
        spec = validate_spec(job.get("spec"))
        if spec["case_id"] != case_id:
            raise QueueError("La solicitud no corresponde a este caso.")
        return job

    def list(self):
        jobs = []
        if self.root.is_dir():
            for path in self.root.glob("*.json"):
                if path.name == "heartbeat.json":
                    continue
                try:
                    job = self.get(path.stem)
                    if job.get("schema") == 1 and job.get("case_id") == path.stem:
                        jobs.append(job)
                except QueueError:
                    continue
        return sorted(jobs, key=lambda j: j.get("created_at", ""), reverse=True)

    def create(self, spec, cases_root):
        spec = validate_spec(spec)
        with self.locked():
            path = self._path(spec["case_id"])
            case = Path(cases_root) / spec["case_id"]
            if path.exists() or case.exists() or case.is_symlink():
                raise QueueError("Ese identificador ya existe. Usa uno nuevo; los expedientes se conservan.")
            job = {"schema": 1, "case_id": spec["case_id"], "spec": spec, "created_at": now(),
                   "steps": [{"key": key, "label": label, "state": "pending", "outputs": []}
                             for key, label in STEPS]}
            job["steps"][0].update(state="queued", requested_at=now(), requested_by=spec["requested_by"])
            self._write(path, job)
            return job

    def enqueue(self, case_id, step_key, requested_by):
        with self.locked():
            job = self.get(case_id)
            keys = [key for key, _ in STEPS]
            if step_key not in keys:
                raise QueueError("Fase no permitida.")
            index = keys.index(step_key)
            if any(s["state"] in ("queued", "running") for s in job["steps"]):
                raise QueueError("La corrida ya tiene una fase en cola o en ejecución.")
            if job["steps"][index]["state"] != "pending":
                raise QueueError("Esa fase ya fue solicitada. No se sobrescriben sus productos.")
            if not all(s["state"] == "succeeded" for s in job["steps"][:index]):
                raise QueueError("Completa las fases anteriores antes de continuar.")
            job["steps"][index].update(state="queued", requested_at=now(), requested_by=requested_by)
            self._write(self._path(case_id), job)
            return job

    def claim(self):
        with self.locked():
            for job in reversed(self.list()):
                for index, step in enumerate(job["steps"]):
                    if step["state"] == "queued":
                        if not all(s["state"] == "succeeded" for s in job["steps"][:index]):
                            continue
                        step.update(state="running", started_at=now(), token=str(uuid.uuid4()))
                        self._write(self._path(job["case_id"]), job)
                        return job, step["key"], step["token"]
        return None

    def finish(self, case_id, step_key, token, *, error=None, outputs=None, returncode=None):
        with self.locked():
            job = self.get(case_id)
            step = next(s for s in job["steps"] if s["key"] == step_key)
            if step["state"] != "running" or step.get("token") != token:
                raise QueueError("La fase ya no pertenece a este ejecutor.")
            step.update(state="failed" if error else "succeeded", finished_at=now(),
                        message=error or "Ejecución terminada y productos comprobados.",
                        outputs=outputs or [], returncode=returncode)
            self._write(self._path(case_id), job)
            return job

    def recover_interrupted(self):
        # Called only after acquiring the exclusive lifetime worker lock.
        with self.locked():
            for job in self.list():
                changed = False
                for step in job["steps"]:
                    if step["state"] == "running":
                        step.update(state="failed", finished_at=now(), message="El ejecutor se interrumpió. Se conservaron los archivos parciales; crea un caso nuevo para repetir.")
                        changed = True
                if changed:
                    self._write(self._path(job["case_id"]), job)

    def heartbeat(self, available=True, message="Ejecutor disponible"):
        self._write(self.root / "heartbeat.json", {"at": now(), "available": available, "message": message})

    def health(self):
        try:
            data = self._read(self.root / "heartbeat.json")
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(data["at"])).total_seconds()
            return bool(data.get("available") is True and 0 <= age < 30)
        except (QueueError, ValueError, TypeError, KeyError):
            return False
