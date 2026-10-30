import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from case_io import ROOT, case_path, custody, now, one_line, sha256, verify, write_json


def sanitized_config(config):
    # A positive allowlist; environment, command, labels and secret values never leave memory.
    return {"name": config.get("name"), "services": {
        name: {key: value for key, value in service.items() if key in ("image", "ports", "networks", "logging")}
        for name, service in config.get("services", {}).items()},
        "volumes": sorted(config.get("volumes", {})), "networks": sorted(config.get("networks", {}))}


def validate_dump(path, instrumented):
    # Necessary completion checks. Only a successful isolated restore proves restorability.
    text = path.read_text(encoding="utf-8", errors="strict")
    required = ["CREATE TABLE `website_record`", "-- Dump completed on"]
    if instrumented:
        required.append("CREATE TABLE `website_auditevent`")
    if not all(marker in text for marker in required):
        raise ValueError("Incomplete SQL dump: schema/completion marker missing")


def acquire(args):
    one_line(args.operator)
    if not args.writes_stopped:
        raise ValueError("Stop scenario writes and pass --writes-stopped before acquisition")
    case = case_path(args.root, args.case)
    case.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(case.parent).free < args.min_free_mb * 1024 * 1024:
        raise ValueError("Insufficient free storage")
    case.mkdir(mode=0o700)  # never reuse or overwrite a case
    for sub in ("original", "trabajo", "custodia", "analisis", "reporte"):
        (case / sub).mkdir()
    compose = ["docker", "compose", "--env-file", str(Path(args.env_file).resolve()), "-f", str(Path(args.compose).resolve())]
    if args.project:
        compose += ["-p", args.project]
    metadata = {"case_id": args.case, "operator": args.operator, "environment": args.environment,
                "scope": args.scope, "authorization": args.authorization, "started_at_utc": now(),
                "interval_start": args.interval_start, "interval_end": args.interval_end,
                "clock_offset_seconds": args.clock_offset_seconds, "writes_stopped": True,
                "consistency": "Sequential sources; InnoDB logical dump; no cross-source atomic snapshot",
                "host": platform.platform(), "python": platform.python_version(), "commands": []}

    def run(argv, name=None, input=None, optional=False):
        start = now()
        result = subprocess.run(argv, input=input, capture_output=True)
        metadata["commands"].append({"argv": argv, "start_utc": start, "end_utc": now(), "returncode": result.returncode})
        if name:
            (case / "original" / name).write_bytes(result.stdout)
            if result.stderr:
                (case / "original" / (name + ".stderr.txt")).write_bytes(result.stderr)
        if result.returncode and not optional:
            raise RuntimeError("Acquisition command failed: " + " ".join(argv[:4]))
        return result

    try:
        config = json.loads(run(compose + ["config", "--format", "json"]).stdout)
        write_json(case / "original" / "compose_sanitized.json", sanitized_config(config))
        for service in ("web", "db"):
            run(compose + ["logs", "--no-color", "--timestamps", service], f"docker_{service}.log")
        metadata["docker_version"] = run(["docker", "version", "--format", "{{.Server.Version}} {{.Client.Version}}" ]).stdout.decode().strip()
        metadata["compose_version"] = run(["docker", "compose", "version", "--short"]).stdout.decode().strip()
        metadata["containers"] = run(compose + ["ps", "--format", "json"]).stdout.decode().strip()
        image_info = run(compose + ["exec", "-T", "web", "python", "-c",
            "import pathlib,hashlib,json; print(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for root in ('website','dcrm') for p in pathlib.Path(root).rglob('*.py')}))"])
        metadata["running_python_sources"] = json.loads(image_info.stdout)
        metadata["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        metadata["baseline_commit"] = "5f80cd103e32825f4504fa5e96103d56cfbd968e"
        metadata["application_commit"] = metadata["baseline_commit"] if args.environment == "A" else metadata["git_head"]
        files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
        metadata["working_tree_files_sha256"] = {name: sha256(ROOT / name) for name in files if name and (ROOT / name).is_file()}
        run(compose + ["exec", "-T", "web", "python", "-"], "sources.json",
            input=(ROOT / "forensic_lab/tools/export_sources.py").read_bytes())
        sources = json.loads((case / "original/sources.json").read_text(encoding="utf-8"))
        if sources["database_vendor"] != "mysql" or sources["audit_available"] != (args.environment == "B"):
            raise ValueError("Unexpected database engine or instrumentation")
        dump_command = '''set -eu
cfg=$(mktemp)
trap 'rm -f "$cfg"' EXIT
cat /run/secrets/reader.cnf > "$cfg"
chmod 600 "$cfg"
mysqldump --defaults-extra-file="$cfg" --single-transaction --quick --routines --triggers --no-tablespaces --set-gtid-purged=OFF crm_lab'''
        run(compose + ["exec", "-T", "db", "sh", "-c", dump_command], "mysql_dump.sql")
        validate_dump(case / "original/mysql_dump.sql", args.environment == "B")
        binlog = run(compose + ["exec", "-T", "db", "sh", "-c", "mysqlbinlog /var/lib/mysql/binlog.[0-9]*"], optional=True)
        if binlog.returncode == 0 and binlog.stdout:
            (case / "original/mysql_binlog.txt").write_bytes(binlog.stdout)
            metadata["binlog"] = "Acquired conditionally; may include active file; interval must be examined"
        else:
            metadata["binlog"] = "Unavailable; no conclusions based on binlog"
            metadata["binlog_error"] = binlog.stderr.decode(errors="replace")
        metadata["finished_at_utc"] = now()
        metadata["dump_restore_validation"] = "pending isolated restore"
        write_json(case / "original/acquisition.json", metadata)
        entries = []
        for i, original in enumerate(sorted((case / "original").iterdir()), 1):
            entry = {"case_id": args.case, "evidence_id": f"{args.case}/E-{i:03}", "name": original.name,
                     "description": original.name, "original_path": str(original), "custodian": args.operator,
                     "source": "Docker/MySQL " + args.environment, "format": original.suffix,
                     "size": original.stat().st_size, "sha256": sha256(original), "acquired_at_utc": now(), "acquirer": args.operator}
            entries.append(entry)
            custody(case, entry["evidence_id"], "ACQUIRE", args.operator, original, entry["sha256"])
            target = case / "trabajo" / original.name
            shutil.copyfile(original, target)
            if sha256(target) != entry["sha256"]:
                raise ValueError("Working copy hash mismatch")
            custody(case, entry["evidence_id"], "COPY", args.operator, target, entry["sha256"], reason="Verified working copy")
            original.chmod(0o400)
            target.chmod(0o400)
        temporary = case / "custodia/manifest.partial.json"
        write_json(temporary, {"schema": 1, "case_id": args.case, "files": entries})
        with (case / "custodia/evidence_inventory.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(entries[0]))
            writer.writeheader()
            writer.writerows(entries)
        verify(case, args.operator, manifest_name="manifest.partial.json")
        temporary.rename(case / "custodia/manifest.json")
        (case / "custodia/manifest.json").chmod(0o400)
        print(str(case))
    except Exception as error:
        write_json(case / "custodia/acquisition_failed.json", {"error": str(error), "metadata": metadata})
        raise


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="Acquire a new external laboratory evidence case")
    for arg in ("root", "case", "operator", "compose", "env-file", "scope", "authorization", "interval-start", "interval-end"):
        parser.add_argument("--" + arg, required=True)
    parser.add_argument("--environment", choices=["A", "B"], required=True)
    parser.add_argument("--project")
    parser.add_argument("--writes-stopped", action="store_true")
    parser.add_argument("--clock-offset-seconds", type=float)
    parser.add_argument("--min-free-mb", type=int, default=100)
    args = parser.parse_args()
    try:
        acquire(args)
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"Acquisition incomplete; partial sources preserved: {error}\n")


if __name__ == "__main__":
    main()
