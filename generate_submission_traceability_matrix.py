"""Build a deterministic manuscript figure/table traceability matrix."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_outputs(data: dict) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for key, value in data["outputs"].items():
        if isinstance(value, str):
            outputs[key] = value
        else:
            outputs[value["path"]] = value["sha256"]
    return outputs


def manifest_item(root: Path, artifact: str, manifest_rel: str) -> dict:
    data = read_json(root / manifest_rel)
    inputs = list(data.get("sources", data.get("inputs", [])))
    input_records = []
    for rel in inputs:
        path = root / rel
        expected = data.get("sources", {}).get(rel)
        actual = sha256(path) if path.is_file() else None
        input_records.append({"path": rel, "exists": path.is_file(), "sha256": actual, "expected_sha256": expected, "hash_matches": expected is None or actual == expected})
    output_records = []
    for rel, expected in normalize_outputs(data).items():
        path = root / rel
        actual = sha256(path) if path.is_file() else None
        output_records.append({"path": rel, "exists": path.is_file(), "sha256": actual, "expected_sha256": expected, "hash_matches": actual == expected})
    return {"artifact": artifact, "kind": "figure", "manifest": manifest_rel, "claim_boundary": data["claim_boundary"], "inputs": input_records, "outputs": output_records}


def table_item(root: Path, artifact: str, table_rel: str, source_rels: list[str], expected_rows: int) -> dict:
    table_path = root / table_rel
    table = read_json(table_path)
    sources = []
    for rel in source_rels:
        path = root / rel
        sources.append({"path": rel, "exists": path.is_file(), "sha256": sha256(path) if path.is_file() else None})
    outputs = []
    for suffix in (".json", ".csv", ".md"):
        path = table_path.with_suffix(suffix)
        outputs.append({"path": path.relative_to(root).as_posix(), "exists": path.is_file(), "sha256": sha256(path) if path.is_file() else None})
    return {"artifact": artifact, "kind": "table", "manifest": table_rel, "claim_boundary": table["claim_boundary"], "expected_rows": expected_rows, "observed_rows": table.get("row_count", len(table.get("rows", []))), "table_status": table["status"], "inputs": sources, "outputs": outputs}


def build(root: Path) -> dict:
    items = [
        manifest_item(root, "Case079 Figures 2-4", "paper/figures/pub2_20260812/figure_manifest.json"),
        manifest_item(root, "Supplementary Figure 1: H115 grid sensitivity", "paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_manifest.json"),
        manifest_item(root, "Supplementary Figure 2: H115 source/registration", "paper/figures/ucl_h115_source_registration_20260825/figure_manifest.json"),
        table_item(root, "Supplementary Table 1: H115 endpoints", "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json", ["outputs/ucl_h115_source_registration_audit_20260825/effective_dx0p5_coordinate_audit.json", "outputs/ucl_h115_source_registration_audit_20260825/effective_dx0p3_coordinate_audit.json", "outputs/ucl_h115_water_nominal64_dx0p5_20260825/comparison.json"], 24),
        table_item(root, "Supplementary Table 2: H115 methods", "paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.json", ["outputs/ucl_h115_water_validation_20260818/summary.json", "outputs/ucl_h115_water_validation_20260818/package_validation.json", "outputs/ucl_h115_water_dx0p3_grid_sensitivity_full_20260823/summary.json", "outputs/ucl_h115_water_dx0p3_grid_sensitivity_full_20260823/package_validation.json", "outputs/ucl_h115_water_nominal64_dx0p5_20260825/summary.json", "outputs/ucl_h115_source_registration_audit_20260825/package_validation.json"], 3),
    ]
    checks = {
        "all_inputs_present": all(record["exists"] for item in items for record in item["inputs"]),
        "all_outputs_present": all(record["exists"] for item in items for record in item["outputs"]),
        "all_declared_hashes_match": all(record.get("hash_matches", True) for item in items for record in item["inputs"] + item["outputs"]),
        "table_rows_match": all(item.get("observed_rows") == item.get("expected_rows") for item in items if item["kind"] == "table"),
        "table_generation_passed": all(item.get("table_status") == "passed" for item in items if item["kind"] == "table"),
        "claim_boundaries_present": all(bool(item["claim_boundary"].strip()) for item in items),
    }
    return {"schema_version": "1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "status": "passed" if all(checks.values()) else "failed", "checks": checks, "items": items, "claim_boundary": "Traceability and package integrity only; H115 external validation remains nonpassing and Case079 remains single-case engineering evidence."}


def write_outputs(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "traceability_matrix.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = []
    for item in report["items"]:
        for role in ("inputs", "outputs"):
            for record in item[role]:
                rows.append({"artifact": item["artifact"], "kind": item["kind"], "role": role[:-1], "path": record["path"], "sha256": record.get("sha256"), "exists": record["exists"], "hash_matches": record.get("hash_matches", "not_declared")})
    with (output_dir / "traceability_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Submission figure/table traceability matrix", "", f"Status: **{report['status']}**", "", "| Artifact | Inputs | Outputs | Boundary |", "|---|---:|---:|---|"]
    for item in report["items"]:
        lines.append(f"| {item['artifact']} | {len(item['inputs'])} | {len(item['outputs'])} | {item['claim_boundary']} |")
    lines += ["", "## Deterministic checks", ""] + [f"- {key}: `{str(value).lower()}`" for key, value in report["checks"].items()] + ["", report["claim_boundary"], ""]
    (output_dir / "traceability_matrix.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    write_outputs(report, args.output_dir)
    print(json.dumps({"status": report["status"], "checks": report["checks"], "artifact_count": len(report["items"])}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
