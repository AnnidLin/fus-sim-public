from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from estimate_temperature_rise import PROJECT_ROOT
from simulate_pennes_bioheat import run as run_pennes_case


def parse_float_list(value: str) -> list[float]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected a comma-separated list of numbers.")
    try:
        return [float(item) for item in items]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid numeric list: {value}") from exc


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def case_namespace(args: argparse.Namespace, output_dir: Path, soft_perfusion_s: float, skull_conductivity: float) -> argparse.Namespace:
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
        trains=int(args.trains),
        dt_s=float(args.dt_s),
        initial_temp_c=float(args.initial_temp_c),
        blood_temp_c=float(args.blood_temp_c),
        target_window_radius=int(args.target_window_radius),
        soft_perfusion_s=float(soft_perfusion_s),
        skull_conductivity=float(skull_conductivity),
        soft_conductivity=float(args.soft_conductivity),
        skull_specific_heat=float(args.skull_specific_heat),
    )


def load_case_summary(case_dir: Path) -> dict[str, object]:
    summary_path = case_dir / "pennes_summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pressure_dir = Path(args.pressure_dir)
    soft_perfusion_values = parse_float_list(args.soft_perfusion_s)
    skull_conductivity_values = parse_float_list(args.skull_conductivity)
    total_cases = len(soft_perfusion_values) * len(skull_conductivity_values)
    start_time = time.perf_counter()
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    print(f"Running {total_cases} {args.pulse_mode} Pennes sensitivity cases.")
    case_index = 0
    for soft_perfusion_s in soft_perfusion_values:
        for skull_conductivity in skull_conductivity_values:
            case_index += 1
            case_name = f"case_{case_index:03d}_perf_{soft_perfusion_s:g}_kskull_{skull_conductivity:g}"
            safe_case_name = case_name.replace(".", "p").replace("-", "m")
            case_dir = output_dir / safe_case_name
            case_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"[{case_index}/{total_cases}] soft_perfusion_s={soft_perfusion_s:g}, "
                f"skull_conductivity={skull_conductivity:g}"
            )
            case_start = time.perf_counter()
            try:
                run_pennes_case(case_namespace(args, case_dir, soft_perfusion_s, skull_conductivity))
                summary = load_case_summary(case_dir)
                elapsed_s = time.perf_counter() - case_start
                rows.append(
                    {
                        "case": safe_case_name,
                        "status": "ok",
                        "soft_perfusion_s": float(soft_perfusion_s),
                        "skull_conductivity_w_m_k": float(skull_conductivity),
                        "soft_conductivity_w_m_k": float(args.soft_conductivity),
                        "skull_specific_heat_j_kg_k": float(args.skull_specific_heat),
                        "duration_s": float(summary["duration_s"]),
                        "duty_cycle": float(summary["duty_cycle"]),
                        "pulse_mode": str(summary["pulse_mode"]),
                        "protocol_total_duration_s": float(summary.get("protocol_total_duration_s", 0.0)),
                        "total_pulse_on_time_s": float(summary.get("total_pulse_on_time_s", 0.0)),
                        "protocol_effective_duty_cycle": float(summary.get("protocol_effective_duty_cycle", 0.0)),
                        "dt_s": float(summary["actual_dt_s"]),
                        "time_steps": int(summary["time_steps"]),
                        "max_temperature_rise_c": float(summary["max_temperature_rise_c"]),
                        "target_temperature_rise_c": float(summary["target_temperature_rise_c"]),
                        "target_window_peak_temperature_rise_c": float(summary["target_window_peak_temperature_rise_c"]),
                        "max_temperature_c": float(summary["max_temperature_c"]),
                        "temperature_margin_to_42c": float(42.0 - float(summary["max_temperature_c"])),
                        "target_temperature_c": float(summary["target_temperature_c"]),
                        "target_window_peak_temperature_index_ijk": json.dumps(
                            summary["target_window_peak_temperature_index_ijk"]
                        ),
                        "case_runtime_s": round(elapsed_s, 3),
                        "output_dir": str(case_dir),
                    }
                )
            except Exception as exc:
                elapsed_s = time.perf_counter() - case_start
                failures.append(
                    {
                        "case": safe_case_name,
                        "soft_perfusion_s": float(soft_perfusion_s),
                        "skull_conductivity_w_m_k": float(skull_conductivity),
                        "error": str(exc),
                        "case_runtime_s": round(elapsed_s, 3),
                    }
                )
                rows.append(
                    {
                        "case": safe_case_name,
                        "status": "failed",
                        "soft_perfusion_s": float(soft_perfusion_s),
                        "skull_conductivity_w_m_k": float(skull_conductivity),
                        "soft_conductivity_w_m_k": float(args.soft_conductivity),
                        "skull_specific_heat_j_kg_k": float(args.skull_specific_heat),
                        "duration_s": float(args.duration_s),
                        "duty_cycle": float(args.duty_cycle),
                        "pulse_mode": str(args.pulse_mode),
                        "protocol_total_duration_s": "",
                        "total_pulse_on_time_s": "",
                        "protocol_effective_duty_cycle": "",
                        "dt_s": "",
                        "time_steps": "",
                        "max_temperature_rise_c": "",
                        "target_temperature_rise_c": "",
                        "target_window_peak_temperature_rise_c": "",
                        "max_temperature_c": "",
                        "temperature_margin_to_42c": "",
                        "target_temperature_c": "",
                        "target_window_peak_temperature_index_ijk": "",
                        "case_runtime_s": round(elapsed_s, 3),
                        "output_dir": str(case_dir),
                    }
                )

    ok_rows = [row for row in rows if row["status"] == "ok"]
    ranked_rows = sorted(ok_rows, key=lambda row: float(row["max_temperature_c"]), reverse=True)
    write_csv(output_dir / "sensitivity_results.csv", rows)
    write_csv(output_dir / "sensitivity_results_ranked.csv", ranked_rows)
    if failures:
        write_csv(output_dir / "sensitivity_failures.csv", failures)

    worst_case = ranked_rows[0] if ranked_rows else None
    risk_threshold_c = float(args.risk_threshold_c)
    summary = {
        "description": "Pennes thermal parameter sensitivity scan using the current best quick 3D pressure field.",
        "pressure_dir": str(pressure_dir),
        "output_dir": str(output_dir),
        "pulse_mode": str(args.pulse_mode),
        "duration_s": float(args.duration_s),
        "duty_cycle": float(args.duty_cycle),
        "requested_constant_duty_cycle": float(args.duty_cycle),
        "dt_s": float(args.dt_s),
        "soft_perfusion_values_s": soft_perfusion_values,
        "skull_conductivity_values_w_m_k": skull_conductivity_values,
        "soft_conductivity_w_m_k": float(args.soft_conductivity),
        "skull_specific_heat_j_kg_k": float(args.skull_specific_heat),
        "total_cases": total_cases,
        "completed_cases": len(ok_rows),
        "failed_cases": len(failures),
        "runtime_s": round(time.perf_counter() - start_time, 3),
        "risk_threshold_c": risk_threshold_c,
        "worst_case": worst_case,
        "protocol_effective_duty_cycle": (
            float(worst_case["protocol_effective_duty_cycle"]) if worst_case else None
        ),
        "temperature_margin_to_threshold_c": (
            float(risk_threshold_c - float(worst_case["max_temperature_c"])) if worst_case else None
        ),
        "near_threshold_flag": bool(
            worst_case and 0.0 <= float(risk_threshold_c - float(worst_case["max_temperature_c"])) < 1.0
        ),
        "risk_flag": bool(worst_case and float(worst_case["max_temperature_c"]) >= risk_threshold_c),
        "interpretation": (
            "Worst-case scan result remains below the configured risk threshold."
            if worst_case and float(worst_case["max_temperature_c"]) < risk_threshold_c
            else "At least one case reaches or exceeds the configured risk threshold, or no case completed."
        ),
        "averaging_note": (
            "protocol-averaged uses the protocol effective duty cycle over the true protocol duration; "
            "averaged uses duration_s with a constant user-specified duty cycle."
        ),
        "limitations": (
            "Uses a cropped quick pressure field and approximate material maps; this is a robustness check, "
            "not a clinical safety claim."
        ),
    }
    (output_dir / "sensitivity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "sensitivity_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Pennes sensitivity scan\n")
        handle.write(f"pressure_dir={pressure_dir}\n")
        handle.write(f"total_cases={total_cases}\n")
        handle.write(f"completed_cases={len(ok_rows)}\n")
        handle.write(f"failed_cases={len(failures)}\n")
        handle.write(f"pulse_mode={args.pulse_mode}\n")
        if worst_case:
            handle.write(f"worst_case={worst_case['case']}\n")
            handle.write(f"worst_max_temperature_c={float(worst_case['max_temperature_c']):.6f}\n")
            handle.write(f"worst_max_temperature_rise_c={float(worst_case['max_temperature_rise_c']):.6f}\n")
            handle.write(f"worst_target_temperature_rise_c={float(worst_case['target_temperature_rise_c']):.6f}\n")
            handle.write(
                "worst_target_window_peak_temperature_rise_c="
                f"{float(worst_case['target_window_peak_temperature_rise_c']):.6f}\n"
            )
        handle.write(f"risk_threshold_c={risk_threshold_c:.3f}\n")
        handle.write(f"protocol_effective_duty_cycle={summary['protocol_effective_duty_cycle']}\n")
        handle.write(f"temperature_margin_to_threshold_c={summary['temperature_margin_to_threshold_c']}\n")
        handle.write(f"near_threshold_flag={summary['near_threshold_flag']}\n")
        handle.write(f"risk_flag={summary['risk_flag']}\n")

    if worst_case:
        print(
            f"Completed {len(ok_rows)}/{total_cases} cases. "
            f"worst_max_temp_C={float(worst_case['max_temperature_c']):.6f} "
            f"worst_case={worst_case['case']} output_dir={output_dir}"
        )
    else:
        print(f"No successful cases. output_dir={output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan Pennes material and perfusion sensitivity cases.")
    parser.add_argument(
        "--pressure-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_transducer_stability_target_020" / "ap30_r35_c8_t55"),
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "pennes_sensitivity_target_020_best"))
    parser.add_argument("--soft-perfusion-s", default="0,0.0015,0.003,0.006")
    parser.add_argument("--skull-conductivity", default="0.20,0.32,0.50")
    parser.add_argument("--soft-conductivity", type=float, default=0.50)
    parser.add_argument("--skull-specific-heat", type=float, default=1300.0)
    parser.add_argument("--duration-s", type=float, default=5.201)
    parser.add_argument("--duty-cycle", type=float, default=0.06)
    parser.add_argument("--pulse-mode", choices=["averaged", "protocol-averaged", "explicit"], default="protocol-averaged")
    parser.add_argument("--dt-s", type=float, default=0.005)
    parser.add_argument("--prf-hz", type=float, default=300.0)
    parser.add_argument("--pulse-duty-cycle", type=float, default=0.06)
    parser.add_argument("--train-duration-s", type=float, default=0.067)
    parser.add_argument("--inter-train-s", type=float, default=2.5)
    parser.add_argument("--trains", type=int, default=3)
    parser.add_argument("--initial-temp-c", type=float, default=37.0)
    parser.add_argument("--blood-temp-c", type=float, default=37.0)
    parser.add_argument("--target-window-radius", type=int, default=3)
    parser.add_argument("--risk-threshold-c", type=float, default=42.0)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
