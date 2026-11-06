"""Run fixed forensic phases outside Django. No shell or user-selected commands."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from .job_queue import JobQueue, QueueError, validate_spec

OUTPUTS = {
    "acquire": ["custodia/manifest.json", "custodia/evidence_inventory.csv", "trabajo/acquisition.json"],
    "examine": ["analisis/events_normalized.json", "analisis/changes_by_record.json", "analisis/inconsistencies.txt"],
    "timeline": ["analisis/timeline.md"],
    "report": ["reporte/report.md", "reporte/report_execution.json"],
}


class WorkerStopped(Exception):
    pass


def commands(project_root, cases_root, project_name, spec, step):
    spec = validate_spec(spec)
    tools = Path(project_root) / "forensic_lab/tools"
    common = ["--root", str(cases_root), "--case", spec["case_id"], "--operator=" + spec["operator"]]
    if step == "acquire":
        command = [sys.executable, str(tools / "acquire_case.py"), *common,
                   "--compose", str(Path(project_root) / "docker-compose.yml"),
                   "--env-file", str(Path(project_root) / ".lab/lab.env"), "--environment", "B",
                   "--scope=" + spec["scope"], "--authorization=" + spec["authorization"],
                   "--interval-start", spec["interval_start"], "--interval-end", spec["interval_end"],
                   "--writes-stopped"]
        if project_name:
            command += ["--project", project_name]
        return [command]
    scripts = {"examine": ("verify_evidence.py", "examine_evidence.py"),
               "timeline": ("build_timeline.py",), "report": ("generate_report.py",)}
    if step not in scripts:
        raise QueueError("Fase no permitida.")
    return [[sys.executable, str(tools / name), *common] for name in scripts[step]]


def validate_outputs(project_root, cases_root, case_id, step):
    # Reuse the same integrity rules as the CLI, without importing Django.
    tools = Path(project_root) / "forensic_lab/tools"
    module_spec = importlib.util.spec_from_file_location("worker_case_io", tools / "case_io.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    case = module.case_path(cases_root, case_id)
    module.verify(case, "Ejecutor", record=False)
    for relative in OUTPUTS[step]:
        path = case / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise QueueError("No se encontraron todos los productos de la fase.")
        if relative.startswith(("analisis/", "reporte/")):
            module.checked_derived(case, relative)
    return OUTPUTS[step]


def run_command(argv, *, queue, cwd, timeout):
    environment = dict(os.environ)
    # Trust this one configured, read-only source checkout even if the host UID differs.
    environment.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="safe.directory", GIT_CONFIG_VALUE_0=str(cwd))
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(argv, cwd=cwd, env=environment, shell=False,
                                   stdout=subprocess.DEVNULL, stderr=errors, start_new_session=True)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                queue.heartbeat()
                if time.monotonic() >= deadline:
                    raise TimeoutError
                time.sleep(1)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        # Raw stderr may contain authentication material; it is never sent to the UI.
        errors.seek(0)
        text = errors.read(65536).decode(errors="replace")
        message = "La herramienta terminó con error. Revisa la configuración del ejecutor; se conservaron los productos parciales."
        for fragment, safe in (
            ("Integrity failure", "La verificación detectó una discrepancia de integridad. Se detuvo el procedimiento."),
            ("Incomplete SQL dump", "El respaldo SQL está incompleto. La adquisición no se declaró terminada."),
            ("permission denied", "El ejecutor no tiene acceso a Docker o a los archivos necesarios."),
            ("Cannot connect to the Docker", "El ejecutor no puede conectarse a Docker."),
            ("No space left", "No hay espacio suficiente para completar la fase."),
        ):
            if fragment.casefold() in text.casefold():
                message = safe
                break
        return process.returncode, message


def process_one(queue, project_root, cases_root, project_name="", timeout=600, runner=run_command):
    claim = queue.claim()
    if not claim:
        return False
    job, step, token = claim
    error, outputs, returncode = None, [], None
    try:
        if job["spec"].get("case_id") != job["case_id"]:
            raise QueueError("La solicitud no corresponde a este caso.")
        if Path(cases_root).resolve().is_relative_to(Path(project_root).resolve()):
            raise QueueError("Los expedientes deben conservarse fuera del repositorio.")
        for argv in commands(project_root, cases_root, project_name, job["spec"], step):
            returncode, message = runner(argv, queue=queue, cwd=project_root, timeout=timeout)
            if returncode != 0:
                error = message
                break
        if not error:
            outputs = validate_outputs(project_root, cases_root, job["case_id"], step)
    except TimeoutError:
        error = "La fase superó el tiempo máximo. Se detuvo el proceso y se conservaron los archivos parciales."
    except (KeyboardInterrupt, WorkerStopped):
        error = "El ejecutor se detuvo. Se conservaron los archivos parciales; crea un caso nuevo para repetir."
        raise
    except Exception:
        error = "No se pudo completar o verificar la fase. Se conservaron los archivos parciales; revisa la configuración antes de abrir otro caso."
    finally:
        result = queue.finish(job["case_id"], step, token, error=error, outputs=outputs, returncode=returncode)
        # Operational execution record, separate from acquired original evidence.
        case = Path(cases_root) / job["case_id"]
        custody = case / "custodia"
        if not case.is_symlink() and not custody.is_symlink() and custody.is_dir():
            record = custody / f"procedure-{step}-{token}.json"
            try:
                with record.open("x", encoding="utf-8") as stream:
                    json.dump({"case_id": job["case_id"], "requested_by": job["spec"]["requested_by"],
                               "phase": next(s for s in result["steps"] if s["key"] == step)}, stream, ensure_ascii=False, indent=2)
            except OSError:
                # The queue remains the durable journal even if this additional copy fails.
                print(json.dumps({"case": job["case_id"], "execution_record": "copy_failed"}), flush=True)
        print(json.dumps({"case": job["case_id"], "phase": step, "state": "failed" if error else "succeeded"}), flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Ejecutor local de procedimientos forenses")
    parser.add_argument("--once", action="store_true")
    options = parser.parse_args()
    project_root = Path(os.environ.get("FORENSIC_PROJECT_ROOT", Path(__file__).resolve().parents[1])).resolve()
    cases_root = Path(os.environ.get("FORENSIC_CASES_ROOT", project_root.parent / "forensic_cases"))
    queue = JobQueue(os.environ.get("FORENSIC_JOBS_ROOT", project_root / ".lab/jobs"))
    project_name = os.environ.get("FORENSIC_COMPOSE_PROJECT", "")
    def stop(*_):
        raise WorkerStopped
    signal.signal(signal.SIGTERM, stop)
    os.umask(0o077)
    owns_worker_lock = False
    try:
        with queue.locked(worker=True):
            owns_worker_lock = True
            queue.recover_interrupted()
            cases_root.mkdir(parents=True, exist_ok=True)
            while True:
                queue.heartbeat()
                worked = process_one(queue, project_root, cases_root, project_name)
                if options.once:
                    break
                if not worked:
                    time.sleep(2)
    except (WorkerStopped, KeyboardInterrupt):
        pass
    finally:
        if owns_worker_lock:
            queue.heartbeat(available=False, message="Ejecutor detenido")


if __name__ == "__main__":
    main()
