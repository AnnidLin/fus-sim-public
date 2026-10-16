"""Generate a manuscript-ready H115 held-out endpoint table from audited JSON."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


METRICS = [
    ("Axial peak-position error", "axial_held_out", "peak_position_difference_mm", "mm", "<= 1.0", "axial_peak_position"),
    ("Axial normalized L2", "axial_held_out", "normalized_relative_l2_percent", "%", "<= 10.0", "axial_normalized_l2"),
    ("Transverse peak-pressure error", "transverse_held_out", "peak_pressure_error_percent", "%", "|x| <= 10.0", "transverse_peak_pressure"),
    ("Transverse peak-position error", "transverse_held_out", "peak_position_difference_mm", "mm", "<= 1.5", "transverse_peak_position"),
    ("Transverse normalized correlation", "transverse_held_out", "normalized_correlation", "", ">= 0.95", "transverse_correlation"),
    ("Transverse normalized L2", "transverse_held_out", "normalized_relative_l2_percent", "%", "<= 10.0", "transverse_normalized_l2"),
    ("Transverse x -6 dB width error", "transverse_held_out", "x_width_error_percent", "%", "|x| <= 10.0", "transverse_x_width"),
    ("Transverse y -6 dB width error", "transverse_held_out", "y_width_error_percent", "%", "|x| <= 10.0", "transverse_y_width"),
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_rows(cases: list[tuple[str, dict]]) -> list[dict]:
    rows = []
    for label, data in cases:
        for metric, section, field, unit, gate, check in METRICS:
            rows.append(
                {
                    "case": label,
                    "endpoint": metric,
                    "value": float(data[section][field]),
                    "unit": unit,
                    "frozen_gate": gate,
                    "status": "pass" if data["checks"][check] else "fail",
                }
            )
    return rows


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Supplementary table — UCL H115 held-out validation endpoints",
        "",
        "| Model | Held-out endpoint | Value | Frozen gate | Status |",
        "|---|---|---:|---:|:---:|",
    ]
    for row in rows:
        value = f'{row["value"]:.6f}' if row["unit"] == "" else f'{row["value"]:.3f} {row["unit"]}'
        lines.append(f'| {row["case"]} | {row["endpoint"]} | {value} | {row["frozen_gate"]} | {row["status"].upper()} |')
    lines.extend(
        [
            "",
            "The dx0.50 and dx0.30 effective-bowl rows use the dated coordinate audit. The nominal source is a frozen source-factor sensitivity. Passing package-integrity checks do not imply successful external validation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--effective-dx0p5", type=Path, required=True)
    parser.add_argument("--effective-dx0p3", type=Path, required=True)
    parser.add_argument("--nominal-dx0p5", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    cases = [
        ("Effective bowl, dx0.50 mm", read_json(args.effective_dx0p5)),
        ("Effective bowl, dx0.30 mm", read_json(args.effective_dx0p3)),
        ("Nominal 64/64-mm bowl, dx0.50 mm", read_json(args.nominal_dx0p5)),
    ]
    rows = build_rows(cases)
    counts = {
        label: {
            "pass": sum(row["status"] == "pass" for row in rows if row["case"] == label),
            "fail": sum(row["status"] == "fail" for row in rows if row["case"] == label),
        }
        for label, _ in cases
    }
    expected = {
        "Effective bowl, dx0.50 mm": {"pass": 6, "fail": 2},
        "Effective bowl, dx0.30 mm": {"pass": 6, "fail": 2},
        "Nominal 64/64-mm bowl, dx0.50 mm": {"pass": 0, "fail": 8},
    }
    status = "passed" if len(rows) == 24 and counts == expected else "failed"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "h115_validation_endpoints.md").write_text(markdown(rows), encoding="utf-8")
    with (args.output_dir / "h115_validation_endpoints.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "row_count": len(rows),
        "counts": counts,
        "rows": rows,
        "claim_boundary": "Held-out engineering comparison only; external validation remains nonpassing.",
    }
    (args.output_dir / "h115_validation_endpoints.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "row_count": len(rows), "counts": counts}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
