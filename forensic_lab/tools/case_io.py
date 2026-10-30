"""Evidence file invariants shared by acquisition, examination and reporting."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUSTODY_FIELDS = ["case_id", "evidence_id", "time_utc", "action", "operator", "sender", "recipient",
                  "reason", "location", "sha256", "result", "receipt"]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def one_line(value):
    if not value.strip() or "\n" in value or "\r" in value:
        raise ValueError("Custody fields must be nonempty single-line values")
    return value


def case_path(root, case_id):
    import re
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", case_id):
        raise ValueError("Invalid case identifier")
    path = Path(root).resolve() / case_id
    if path.is_symlink() or path.resolve().is_relative_to(ROOT):
        raise ValueError("Evidence must be outside the repository")
    return path


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def custody(case, evidence_id, action, operator, location, digest="", result="OK",
            sender=None, recipient=None, reason="Evidence handling", receipt=None):
    operator = one_line(operator)
    row = dict(zip(CUSTODY_FIELDS, [case.name, evidence_id, now(), action, operator,
        one_line(sender or operator), one_line(recipient or operator), one_line(reason),
        str(location), digest, result, one_line(receipt) if receipt else "Recorded by tool; physical receipt/signature pending if transferred"]))
    path = case / "custodia" / "chain_of_custody.csv"
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CUSTODY_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def verify(case, operator, *, record=True, manifest_name="manifest.json"):
    if case.is_symlink() or any((case / name).is_symlink() for name in ("original", "trabajo", "custodia")):
        raise ValueError("Evidence directories must not be symbolic links")
    manifest = json.loads((case / "custodia" / manifest_name).read_text(encoding="utf-8"))
    entries = manifest["files"]
    if not entries or len({e["name"] for e in entries}) != len(entries):
        raise ValueError("Empty or duplicate manifest entries")
    failures = []
    for directory in ("original", "trabajo"):
        base = case / directory
        expected = {entry["name"] for entry in entries}
        if {p.name for p in base.iterdir()} != expected:
            failures.append(directory + ": unexpected or missing files")
        for entry in entries:
            name = entry["name"]
            if Path(name).name != name or "/" in name or "\\" in name:
                raise ValueError("Unsafe manifest path")
            path = base / name
            good = (path.is_file() and not path.is_symlink() and
                    path.stat().st_size == entry["size"] and sha256(path) == entry["sha256"])
            if not good:
                failures.append(f"{directory}/{name}")
            if record:
                custody(case, entry["evidence_id"], "VERIFY_" + directory, operator, path,
                        entry["sha256"], "OK" if good else "MISMATCH")
    if failures:
        raise ValueError("Integrity failure; isolate discrepant copies: " + ", ".join(failures))
    return entries


def derived(case, relative, text, operator, sources):
    path = case / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    digest = sha256(path)
    write_json(path.with_name(path.name + ".provenance.json"), {
        "derived_id": f"{case.name}/D-{path.stem}", "sha256": digest, "sources": sources, "created_at_utc": now(),
    })
    custody(case, f"{case.name}/D-{path.stem}", "DERIVE", operator, path, digest)
    return path


def checked_derived(case, relative):
    path = case / relative
    meta = json.loads(path.with_name(path.name + ".provenance.json").read_text(encoding="utf-8"))
    if sha256(path) != meta["sha256"]:
        raise ValueError("Derived file was altered: " + str(path))
    return path, meta
