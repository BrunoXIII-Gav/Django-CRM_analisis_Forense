import argparse
import json
from case_io import case_path, checked_derived, derived, verify


def build(case, operator):
    verify(case, operator)
    path, provenance = checked_derived(case, "analisis/events_normalized.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows.sort(key=lambda item: (item["time_utc"], item["event_id"]))
    lines = ["# Línea de tiempo", "", "Los tiempos conservan su offset en events_normalized.json. El orden temporal no demuestra causalidad.", "",
             "| UTC | Cuenta | Canal | Acción | Registro | Respaldo | Evidencia y ubicación |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        values = [row[key] for key in ("time_utc", "actor_username", "channel", "action", "record_id", "support")]
        values.append(f"{row['evidence_id']}:{row['source_locator']}")
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    derived(case, "analisis/timeline.md", "\n".join(lines) + "\n", operator, [provenance])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("root", "case", "operator"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    build(case_path(args.root, args.case), args.operator)
