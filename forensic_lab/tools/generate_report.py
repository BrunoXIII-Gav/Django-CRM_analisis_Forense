import argparse
import csv
import json
from pathlib import Path
from datetime import datetime
from case_io import case_path, checked_derived, derived, now, sha256, verify


def complete(row):
    if not (row["outcome"] == "success" and row["committed"] is True and row["actor_id"] and
            row["actor_username"] and row["time_utc"] and row["channel"] and row["record_id"]):
        return False
    required = {"id", "first_name", "last_name", "email", "phone", "address", "city", "state", "zipcode", "created_at", "updated_at"}
    for state in (row["before"], row["after"]):
        if state is not None and (not isinstance(state, dict) or not required.issubset(state) or str(state["id"]) != str(row["record_id"])):
            return False
    return ((row["action"] == "CREATE" and row["before"] is None and isinstance(row["after"], dict)) or
            (row["action"] == "DELETE" and isinstance(row["before"], dict) and row["after"] is None) or
            (row["action"] == "UPDATE" and isinstance(row["before"], dict) and isinstance(row["after"], dict)))


def evaluate(rows, truth):
    expected = [op for op in truth["operations"] if op["classification"] == "change"]
    used, matrix = set(), []
    for op in expected:
        matches = []
        for row in rows:
            if row["event_id"] in used or not complete(row):
                continue
            if (row["action"], row["channel"], str(row["record_id"]), row["actor_username"]) != (
                    op["action"], op["channel"], str(op["record_id"]), op["actor_username"]):
                continue
            stamp = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
            if not (stamp(op["started_at_utc"]) <= stamp(row["time_utc"]) <= stamp(op["finished_at_utc"])):
                continue
            if any((row["after"] or {}).get(key) != value for key, value in op.get("expected_after", {}).items()):
                continue
            if any((row["before"] or {}).get(key) != value for key, value in op.get("expected_before", {}).items()):
                continue
            matches.append(row)
        match = matches[0] if len(matches) == 1 else None
        if match:
            used.add(match["event_id"])
        matrix.append({"operation_id": op["operation_id"], "reconstructed": bool(match),
                       "event_id": match["event_id"] if match else None,
                       "evidence_id": match["evidence_id"] if match else None,
                       "assessment": "supported" if match else "indeterminate",
                       "scenario_rule": op["rule"], "scenario_legitimate": op["legitimate"]})
    count = sum(item["reconstructed"] for item in matrix)
    return {"expected_changes": len(expected), "reconstructed": count,
            "reconstruction_pct": 100 * count / len(expected) if expected else None,
            "audit_coverage_pct": 100 * count / len(expected) if expected else None,
            "excluded_noops_and_failures": len(truth["operations"]) - len(expected), "matrix": matrix}


def generate(case, operator, truth_path=None, revision=1):
    if revision < 1:
        raise ValueError("Report revision must be positive")
    suffix = "" if revision == 1 else f"-v{revision}"
    started = now()
    entries = verify(case, operator)
    path, provenance = checked_derived(case, "analisis/events_normalized.json")
    _, timeline_provenance = checked_derived(case, "analisis/timeline.md")
    references = [provenance, timeline_provenance]
    rows = json.loads(path.read_text(encoding="utf-8"))
    metadata = json.loads((case / "trabajo/acquisition.json").read_text(encoding="utf-8"))
    restore_path = case / "analisis/restore_validation.json"
    if restore_path.exists():
        checked, restore_provenance = checked_derived(case, "analisis/restore_validation.json")
        references.append(restore_provenance)
        restore_status = json.loads(checked.read_text(encoding="utf-8"))["result"]
    else:
        restore_status = "pending isolated restore"
    metrics = evaluate(rows, json.loads(truth_path.read_text(encoding="utf-8"))) if truth_path else None
    if metrics is not None:
        metrics["truth_sha256"] = sha256(truth_path)
        metrics["integrity_pct"] = 100  # only reached after full verification
        with (case / "custodia/chain_of_custody.csv").open(encoding="utf-8", newline="") as stream:
            transfers = [row for row in csv.DictReader(stream) if row["action"] == "TRANSFER"]
        documented = sum(row["result"] == "OK" and bool(row["receipt"]) and "pending" not in row["receipt"] for row in transfers)
        metrics["custody_transfer_pct"] = 100 * documented / len(transfers) if transfers else None
        metrics["dump_restore_validation"] = restore_status
        metrics["acquisition_seconds"] = (datetime.fromisoformat(metadata["finished_at_utc"]) - datetime.fromisoformat(metadata["started_at_utc"])).total_seconds()
        derived(case, f"reporte/metrics{suffix}.json", json.dumps(metrics, ensure_ascii=False, indent=2), operator, references)
    lines = [f"# Informe {case.name}", "", f"Entorno: {metadata['environment']}. Analista: {operator}. Generado: {started}.", "",
        f"Alcance: {metadata['scope']}. Autorización declarada: {metadata['authorization']}.", "",
        "## Método y fuentes", "", "Se verificaron originales y copias antes de examinar las copias. Se normalizaron tiempos con offset a UTC y se conservaron las ubicaciones de origen. " + ("La tabla de verdad se incorporó sólo después del examen para evaluar la reconstrucción." if truth_path else "No se utilizó una tabla de verdad; este informe describe la actividad adquirida sin métricas comparativas del guion."), "",
        "| ID | Archivo | Bytes | SHA-256 |", "| --- | --- | --- | --- |"]
    for item in entries:
        lines.append(f"| {item['evidence_id']} | {item['name']} | {item['size']} | {item['sha256']} |")
    lines += ["", "## Hallazgos observados", ""]
    for row in rows:
        if row["outcome"] in ("success", "noop"):
            lines.append(f"- {row['time_utc']}: cuenta {row['actor_username']}, {row['action']} de Record {row['record_id']} por {row['channel']}; resultado {row['outcome']}. Fuente {row['evidence_id']}:{row['source_locator']}. Respaldo: {row['support']}; contraste: {row['corroboration']}.")
    if not any(row["outcome"] == "success" for row in rows):
        lines.append("Las fuentes nativas disponibles no permiten reconstruir estados anterior/posterior completos. Las observaciones parciales figuran en la línea de tiempo.")
    if metrics is not None:
        lines += ["", "## Evaluación contra el guion independiente", "",
                  f"Cambios reconstruidos: {metrics['reconstructed']}/{metrics['expected_changes']}; porcentaje: {metrics['reconstruction_pct']}. No-op e intentos rechazados excluidos: {metrics['excluded_noops_and_failures']}.",
                  f"La matriz por operación y el hash del guion están en metrics{suffix}.json. La calificación de indebida proviene de las reglas del guion, no del tipo de operación."]
    lines += ["", "## Inferencias, alternativas y límites", "",
        "La cuenta registrada no identifica por sí sola a una persona. Se deben considerar sesión compartida, error operativo, cambio legítimo, automatización API y desfase de reloj. Los hashes verifican conservación desde la adquisición. Los valores de los campos se sustentan en la auditoría; el log de solicitud sólo contrasta canal, solicitud y resultado HTTP. SQL directo, RAM, imágenes físicas y redo logs quedan fuera del alcance.", "",
        f"Offset del reloj declarado: {metadata['clock_offset_seconds']}; ausencia de medición limita la correlación temporal. Restauración del dump: {restore_status}. Binlog: {metadata['binlog']}.", "",
        "## Revisión y cierre", "", "Pendiente: revisión independiente por otro integrante, constancias de cualquier transferencia física y decisión de retención. G5 no se cierra automáticamente. Conservar originales, manifiesto y custodia con acceso restringido y respaldo independiente.", ""]
    derived(case, f"reporte/report{suffix}.md", "\n".join(lines), operator, references)
    derived(case, f"reporte/report_execution{suffix}.json", json.dumps({"started_at_utc": started, "finished_at_utc": now(), "review": "pending independent reviewer"}, indent=2), operator, references)
    verify(case, operator)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("root", "case", "operator"):
        parser.add_argument("--" + arg, required=True)
    parser.add_argument("--truth", type=Path)
    parser.add_argument("--revision", type=int, default=1)
    args = parser.parse_args()
    generate(case_path(args.root, args.case), args.operator, args.truth, args.revision)
