import argparse
import csv
from datetime import datetime, timezone
import io
import json
import re

from case_io import case_path, custody, derived, now, verify

FIELDS = ["event_id", "time_original", "time_utc", "actor_id", "actor_username", "record_id", "action",
          "channel", "request_id", "session_correlation_id", "before", "after", "changed_fields",
          "outcome", "committed", "evidence_id", "source_file", "source_locator", "support", "corroboration"]


def utc(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Naive timestamp: offset unavailable")
    return stamp.astimezone(timezone.utc).isoformat()


def examine(case, operator):
    entries = verify(case, operator)
    ids = {entry["name"]: entry["evidence_id"] for entry in entries}
    sources = json.loads((case / "trabajo/sources.json").read_text(encoding="utf-8"))
    logs = (case / "trabajo/docker_web.log").read_text(encoding="utf-8", errors="replace").splitlines()
    http = {}
    for line_number, line in enumerate(logs, 1):
        start = line.find('{"kind": "http"')
        if start >= 0:
            try:
                item = json.loads(line[start:])
                http.setdefault(item["request_id"], []).append((line_number, item))
            except (ValueError, KeyError):
                pass
    normalized, issues, seen = [], [], set()
    for i, event in enumerate(sources["events"]):
        locator = f"events[{i}]"
        try:
            if event["event_id"] in seen:
                issues.append(f"Duplicate event_id at {locator}")
                continue
            seen.add(event["event_id"])
            timestamp = utc(event["timestamp"])
            before, after = event.get("before"), event.get("after")
            if event["action"] == "CREATE" and (before is not None or after is None):
                issues.append("Invalid CREATE snapshots at " + locator)
            if event["action"] == "DELETE" and (before is None or after is not None):
                issues.append("Invalid DELETE snapshots at " + locator)
            if event["action"] == "UPDATE" and (before is None or after is None):
                issues.append("Missing UPDATE snapshots at " + locator)
            corroboration = [f"{ids['docker_web.log']}:line {line}" for line, item in http.get(event.get("request_id"), [])
                             if item.get("channel") == event.get("source") and 200 <= item.get("status", 0) < 400]
            normalized.append(dict(zip(FIELDS, [event["event_id"], event["timestamp"], timestamp, event.get("user_id"),
                event.get("username"), event["object_id"], event["action"], event.get("source"), event.get("request_id"),
                event.get("correlation_id"), before, after, event.get("changed_fields"), event.get("outcome"), event.get("committed"),
                ids["sources.json"], "sources.json", locator,
                "confirmed_with_request_contrast" if corroboration else "single_source", corroboration])))
        except (ValueError, KeyError, TypeError) as error:
            issues.append(f"{locator}: {error}")
    # Preserve native admin observations in A and B; never invent old/new values.
    names = {account["id"]: account["username"] for account in sources.get("accounts", [])}
    for i, item in enumerate(sources["admin_log"]):
        try:
            normalized.append({**dict.fromkeys(FIELDS, ""), "event_id": f"admin-{item['id']}",
                "time_original": item["action_time"], "time_utc": utc(item["action_time"]),
                "actor_id": item["user_id"], "actor_username": names.get(item["user_id"], ""),
                "record_id": item["object_id"], "action": {1: "CREATE", 2: "UPDATE", 3: "DELETE"}[item["action_flag"]],
                "channel": "admin", "before": None, "after": None, "outcome": "native_observation", "committed": None,
                "evidence_id": ids["sources.json"], "source_file": "sources.json", "source_locator": f"admin_log[{i}]",
                "support": "single_source", "corroboration": []})
        except (ValueError, KeyError) as error:
            issues.append(f"admin_log[{i}]: {error}")
    # Original web INFO records give account, action and object, but no snapshots.
    pattern = re.compile(r"Record #(\d+) (created|updated|deleted) by user '([^']+)'")
    for line_number, line in enumerate(logs, 1):
        match = pattern.search(line)
        timestamp = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)", line)
        if match and timestamp:
            normalized.append({**dict.fromkeys(FIELDS, ""), "event_id": f"web-log-{line_number}",
                "time_original": timestamp[0], "time_utc": utc(timestamp[0]), "actor_username": match[3],
                "record_id": match[1], "action": {"created": "CREATE", "updated": "UPDATE", "deleted": "DELETE"}[match[2]],
                "channel": "web", "before": None, "after": None, "outcome": "native_observation", "committed": None,
                "evidence_id": ids["docker_web.log"], "source_file": "docker_web.log", "source_locator": f"line {line_number}",
                "support": "single_source", "corroboration": []})
    normalized.sort(key=lambda row: (row["time_utc"], row["event_id"]))
    references = [{"evidence_id": entry["evidence_id"], "sha256": entry["sha256"]} for entry in entries]
    derived(case, "analisis/events_normalized.json", json.dumps(normalized, ensure_ascii=False, indent=2), operator, references)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    for row in normalized:
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) or value is None else value for key, value in row.items()})
    derived(case, "analisis/events_normalized.csv", output.getvalue(), operator, references)
    changes = [dict(event_id=row["event_id"], record_id=row["record_id"], evidence_id=row["evidence_id"],
                    source_locator=row["source_locator"], field=field, before=(row["before"] or {}).get(field),
                    after=(row["after"] or {}).get(field))
               for row in normalized if row["outcome"] in ("success", "noop") for field in row["changed_fields"]]
    derived(case, "analisis/changes_by_record.json", json.dumps(changes, ensure_ascii=False, indent=2), operator, references)
    if not sources["audit_available"]:
        issues.append("AuditEvent absent in original baseline; native sources do not preserve before/after")
    issues.append("Request contrast confirms the HTTP result; field values remain supported by the audit source")
    derived(case, "analisis/inconsistencies.txt", "\n".join(issues) + "\n", operator, references)


def main():
    parser = argparse.ArgumentParser()
    for arg in ("root", "case", "operator"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    examine(case_path(args.root, args.case), args.operator)


if __name__ == "__main__":
    main()
