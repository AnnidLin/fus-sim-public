from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from estimate_temperature_rise import PROJECT_ROOT
from simulate_pennes_bioheat import run as run_pennes_case


def parse_int_list(value: str) -> list[int]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected a comma-separated list of integers.")
    try:
        values = [int(item) for item in items]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid integer list: {value}") from exc
    if any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("Train counts must be positive integers.")
    return values


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def case_namespace(args: argparse.Namespace, output_dir: Path, trains: int) -> argparse.Namespace:
    return argparse.Namespace(
        pressure_dir=str(args.pressure_dir),
        model=args.model,
        output_dir=str(output_dir),
        duration_s=float(args.duration_s),
        duty_cycle=float(args.duty_cycle),
        pulse_mode=str(args.pulse_mode),
        prf_hz=float(args.prf_hz),
        pulse_duty_cycle=float(args.pulse_duty_cycle),
        train_duration_s=float(args.train_duration_s),
        inter_train_s=float(args.inter_train_s),
        trains=int(trains),
        dt_s=float(args.dt_s),
        initial_temp_c=float(args.initial_temp_c),
        blood_temp_c=float(args.blood_temp_c),
        target_window_radius=int(args.target_window_radius),
        soft_perfusion_s=float(args.soft_perfusion_s),
        skull_conductivity=float(args.skull_conductivity),
        soft_conductivity=float(args.soft_conductivity),
        skull_specific_heat=float(args.skull_specific_heat),
    )


def load_case_summary(case_dir: Path) -> dict[str, object]:
    return json.loads((case_dir / "pennes_summary.json").read_text(encoding="utf-8"))


def row_from_summary(
    case_name: str,
    trains: int,
    summary: dict[str, object],
    elapsed_s: float,
    risk_threshold_c: float,
    near_threshold_margin_c: float,
) -> dict[str, object]:
    max_temperature_c = float(summary["max_temperature_c"])
    margin_c = float(risk_threshold_c - max_temperature_c)
    return {
        "case": case_name,
        "status": "ok",
        "trains": int(trains),
        "pulse_mode": str(summary["pulse_mode"]),
        "protocol_total_duration_s": float(summary["protocol_total_duration_s"]),
        "total_pulse_on_time_s": float(summary["total_pulse_on_time_s"]),
        "protocol_effective_duty_cycle": float(summary["protocol_effective_duty_cycle"]),
        "dt_s": float(summary["actual_dt_s"]),
        "time_steps": int(summary["time_steps"]),
        "max_temperature_c": max_temperature_c,
        "max_temperature_rise_c": float(summary["max_temperature_rise_c"]),
        "target_temperature_rise_c": float(summary["target_temperature_rise_c"]),
        "target_window_peak_temperature_rise_c": float(summary["target_window_peak_temperature_rise_c"]),
        "temperature_margin_to_42c": float(42.0 - max_temperature_c),
        "temperature_margin_to_threshold_c": margin_c,
        "near_threshold": bool(0.0 <= margin_c < float(near_threshold_margin_c)),
        "risk_flag": bool(max_temperature_c >= risk_threshold_c),
        "case_runtime_s": round(elapsed_s, 3),
        "output_dir": str(summary.get("output_dir", "")),
    }


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_counts = parse_int_list(args.trains_list)
    risk_threshold_c = float(args.risk_threshold_c)
    start_time = time.perf_counter()
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    print(
        f"Running {len(train_counts)} protocol dose cases with "
        f"soft_perfusion_s={args.soft_perfusion_s:g}, skull_conductivity={args.skull_conductivity:g}."
    )
    for index, trains in enumerate(train_counts, start=1):
        case_name = f"case_trains_{trains:03d}"
        case_dir = output_dir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(train_counts)}] trains={trains}")
        case_start = time.perf_counter()
        try:
            run_pennes_case(case_namespace(args, case_dir, trains))
            summary = load_case_summary(case_dir)
            elapsed_s = time.perf_counter() - case_start
            row = row_from_summary(case_name, trains, summary, elapsed_s, risk_threshold_c, float(args.near_threshold_margin_c))
            row["output_dir"] = str(case_dir)
            row["runtime_warning"] = bool(elapsed_s > float(args.case_runtime_warning_s))
            rows.append(row)
            if row["runtime_warning"]:
                print(f"WARNING: {case_name} runtime {elapsed_s:.1f}s exceeded warning threshold.")
        except Exception as exc:
            elapsed_s = time.perf_counter() - case_start
            failures.append({"case": case_name, "trains": trains, "error": str(exc), "case_runtime_s": round(elapsed_s, 3)})
            rows.append(
                {
                    "case": case_name,
                    "status": "failed",
                    "trains": int(trains),
                    "pulse_mode": str(args.pulse_mode),
                    "protocol_total_duration_s": "",
                    "total_pulse_on_time_s": "",
                    "protocol_effective_duty_cycle": "",
                    "dt_s": "",
                    "time_steps": "",
                    "max_temperature_c": "",
                    "max_temperature_rise_c": "",
                    "target_temperature_rise_c": "",
                    "target_window_peak_temperature_rise_c": "",
                    "temperature_margin_to_42c": "",
                    "temperature_margin_to_threshold_c": "",
                    "near_threshold": "",
                    "risk_flag": "",
                    "case_runtime_s": round(elapsed_s, 3),
                    "output_dir": str(case_dir),
                    "runtime_warning": bool(elapsed_s > float(args.case_runtime_warning_s)),
                }
            )

    ok_rows = [row for row in rows if row["status"] == "ok"]
    write_csv(output_dir / "dose_results.csv", rows)
    write_csv(output_dir / "dose_results_by_temperature.csv", sorted(ok_rows, key=lambda row: float(row["max_temperature_c"]), reverse=True))
    if failures:
        write_csv(output_dir / "dose_failures.csv", failures)

    first_near = next((row for row in ok_rows if bool(row["near_threshold"])), None)
    first_risk = next((row for row in ok_rows if bool(row["risk_flag"])), None)
    hottest = max(ok_rows, key=lambda row: float(row["max_temperature_c"])) if ok_rows else None
    max_train_row = max(ok_rows, key=lambda row: int(row["trains"])) if ok_rows else None
    summary = {
        "description": "Protocol dose scan over train count using the current best quick 3D pressure field.",
        "pressure_dir": str(args.pressure_dir),
        "output_dir": str(output_dir),
        "pulse_mode": str(args.pulse_mode),
        "train_counts": train_counts,
        "material_parameters": {
            "soft_perfusion_s": float(args.soft_perfusion_s),
            "skull_conductivity_w_m_k": float(args.skull_conductivity),
            "soft_conductivity_w_m_k": float(args.soft_conductivity),
            "skull_specific_heat_j_kg_k": float(args.skull_specific_heat),
        },
        "protocol_parameters": {
            "prf_hz": float(args.prf_hz),
            "pulse_duty_cycle": float(args.pulse_duty_cycle),
            "train_duration_s": float(args.train_duration_s),
            "inter_train_s": float(args.inter_train_s),
            "dt_s": float(args.dt_s),
        },
        "risk_threshold_c": risk_threshold_c,
        "near_threshold_margin_c": float(args.near_threshold_margin_c),
        "completed_cases": len(ok_rows),
        "failed_cases": len(failures),
        "runtime_s": round(time.perf_counter() - start_time, 3),
        "first_near_threshold_case": first_near,
        "first_risk_case": first_risk,
        "hottest_case": hottest,
        "max_train_case": max_train_row,
        "interpretation": (
            "At least one protocol dose case reaches or exceeds the configured temperature threshold."
            if first_risk
            else "No scanned train count reaches the configured temperature threshold in this quick-model estimate."
        ),
        "limitations": "Quick cropped pressure field and approximate thermal materials; this estimates dose trend, not clinical safety.",
    }
    (output_dir / "dose_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "dose_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Pennes protocol dose scan\n")
        handle.write(f"pressure_dir={args.pressure_dir}\n")
        handle.write(f"train_counts={','.join(str(value) for value in train_counts)}\n")
        handle.write(f"completed_cases={len(ok_rows)}\n")
        handle.write(f"failed_cases={len(failures)}\n")
        handle.write(f"risk_threshold_c={risk_threshold_c:.3f}\n")
        if hottest:
            handle.write(f"hottest_case={hottest['case']}\n")
            handle.write(f"hottest_max_temperature_c={float(hottest['max_temperature_c']):.6f}\n")
            handle.write(f"hottest_max_temperature_rise_c={float(hottest['max_temperature_rise_c']):.6f}\n")
        if max_train_row:
            handle.write(f"max_train_case={max_train_row['case']}\n")
            handle.write(f"max_train_temperature_margin_to_threshold_c={float(max_train_row['temperature_margin_to_threshold_c']):.6f}\n")
        handle.write(f"first_near_threshold_case={first_near['case'] if first_near else 'None'}\n")
        handle.write(f"first_risk_case={first_risk['case'] if first_risk else 'None'}\n")

    if hottest:
        print(
            f"Completed {len(ok_rows)}/{len(train_counts)} cases. "
            f"hottest={hottest['case']} max_temp_C={float(hottest['max_temperature_c']):.6f} "
            f"output_dir={output_dir}"
        )
    else:
        print(f"No successful cases. output_dir={output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan thermal dose over repeated tFUS train counts.")
    parser.add_argument(
        "--pressure-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_transducer_stability_target_020" / "ap30_r35_c8_t55"),
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "pennes_protocol_dose_target_020"))
    parser.add_argument("--trains-list", default="1,3,10,30,60,90,120")
    parser.add_argument("--pulse-mode", choices=["protocol-averaged", "explicit"], default="protocol-averaged")
    parser.add_argument("--prf-hz", type=float, default=300.0)
    parser.add_argument("--pulse-duty-cycle", type=float, default=0.06)
    parser.add_argument("--train-duration-s", type=float, default=0.067)
    parser.add_argument("--inter-train-s", type=float, default=2.5)
    parser.add_argument("--dt-s", type=float, default=0.005)
    parser.add_argument("--duration-s", type=float, default=0.067)
    parser.add_argument("--duty-cycle", type=float, default=0.06)
    parser.add_argument("--initial-temp-c", type=float, default=37.0)
    parser.add_argument("--blood-temp-c", type=float, default=37.0)
    parser.add_argument("--target-window-radius", type=int, default=3)
    parser.add_argument("--soft-perfusion-s", type=float, default=0.0)
    parser.add_argument("--skull-conductivity", type=float, default=0.20)
    parser.add_argument("--soft-conductivity", type=float, default=0.50)
    parser.add_argument("--skull-specific-heat", type=float, default=1300.0)
    parser.add_argument("--risk-threshold-c", type=float, default=42.0)
    parser.add_argument("--near-threshold-margin-c", type=float, default=1.0)
    parser.add_argument("--case-runtime-warning-s", type=float, default=60.0)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
