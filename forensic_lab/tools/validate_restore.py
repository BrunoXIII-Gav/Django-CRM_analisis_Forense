"""Restore only a verified working dump into a disposable, network-isolated MySQL."""
import argparse
import json
import os
import secrets
import subprocess
import time
from case_io import case_path, derived, now, verify


def validate(case, operator):
    entries = verify(case, operator)
    name = "crm-restore-" + secrets.token_hex(6)
    environment = {**os.environ, "MYSQL_ROOT_PASSWORD": secrets.token_hex(32)}
    started = now()
    def run(argv, **kwargs):
        return subprocess.run(argv, capture_output=True, **kwargs)
    started_container = False
    try:
        result = run(["docker", "run", "-d", "--name", name, "--network", "none", "--tmpfs", "/var/lib/mysql:rw,size=512m",
                      "-e", "MYSQL_ROOT_PASSWORD", "-e", "MYSQL_DATABASE=restored", "mysql:8.0"], env=environment)
        if result.returncode:
            raise RuntimeError("Could not create isolated restoration container")
        started_container = True
        sql = ['docker', 'exec', name, 'sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=tcp -h127.0.0.1 -uroot -N restored -e "SELECT 1"']
        for attempt in range(45):
            if run(sql).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Restoration MySQL did not become ready")
        imported = run(["docker", "exec", "-i", name, "sh", "-c", 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot restored'],
                       input=(case / "trabajo/mysql_dump.sql").read_bytes())
        if imported.returncode:
            raise RuntimeError("Isolated dump restore failed: " + imported.stderr.decode(errors="replace"))
        query = 'SELECT COUNT(*) FROM website_record'
        expected = json.loads((case / "trabajo/sources.json").read_text(encoding="utf-8"))
        if expected["audit_available"]:
            query += '; SELECT COUNT(*) FROM website_auditevent'
        result = run(["docker", "exec", name, "sh", "-c", 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N restored -e "' + query + '"'])
        if result.returncode:
            raise RuntimeError("Restored tables cannot be queried")
        counts = [int(value) for value in result.stdout.split()]
        expected_counts = [len(expected["records"])] + ([len(expected["events"])] if expected["audit_available"] else [])
        if counts != expected_counts:
            raise ValueError("Restored counts differ from separate export; investigate consistency")
        evidence = next(entry for entry in entries if entry["name"] == "mysql_dump.sql")
        derived(case, "analisis/restore_validation.json", json.dumps({"started_at_utc": started, "finished_at_utc": now(),
            "result": "OK", "network": "none", "image": "mysql:8.0", "row_counts": counts,
            "limitation": "Restorability and row-count equivalence; not independent validation of historical truth"}, indent=2), operator, [evidence])
    finally:
        if started_container:
            # Only this invocation's random, disposable restore container, never a case volume.
            subprocess.run(["docker", "rm", "-f", name], check=True, capture_output=True)
    verify(case, operator)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("root", "case", "operator"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    validate(case_path(args.root, args.case), args.operator)
