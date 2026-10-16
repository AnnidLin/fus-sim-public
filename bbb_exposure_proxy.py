from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "bbb_exposure_proxy" / "evidence_brief.json"
HELDOUT = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "heldout_tr_report.json"
OUTPUT = ROOT / "outputs" / "bbb_exposure_proxy_case079_20260721"


class ExposureProxyError(ValueError):
    pass


def mechanical_index(pnp_pa: float, frequency_hz: float, pressure_semantics: str) -> float:
    if pressure_semantics != "waveform_derived_insitu_pnp":
        raise ExposureProxyError("MI requires waveform_derived_insitu_pnp pressure semantics")
    if not math.isfinite(pnp_pa) or pnp_pa <= 0 or not math.isfinite(frequency_hz) or frequency_hz <= 0:
        raise ExposureProxyError("PNP and frequency must be finite and positive")
    return (pnp_pa / 1e6) / math.sqrt(frequency_hz / 1e6)


def pulse_timing(
    frequency_hz: float,
    burst_cycles: int,
    prf_hz: float,
    total_sonication_time_s: float,
) -> dict[str, float | int]:
    if frequency_hz <= 0 or burst_cycles <= 0 or prf_hz <= 0 or total_sonication_time_s <= 0:
        raise ExposureProxyError("pulse timing inputs must be positive")
    burst_duration_s = burst_cycles / frequency_hz
    duty_cycle_fraction = burst_duration_s * prf_hz
    if duty_cycle_fraction > 1.0 + 1e-12:
        raise ExposureProxyError("pulse timing implies duty cycle above one")
    pulse_count = int(math.floor(prf_hz * total_sonication_time_s + 1e-12))
    if pulse_count < 1:
        raise ExposureProxyError("protocol contains no complete pulse")
    return {
        "burst_duration_s": burst_duration_s,
        "prf_hz": prf_hz,
        "duty_cycle_fraction": duty_cycle_fraction,
        "pulse_count": pulse_count,
        "total_on_time_s": pulse_count * burst_duration_s,
    }


def validate_microbubble(protocol: dict[str, Any]) -> None:
    status = protocol.get("status")
    details = [protocol.get("product"), protocol.get("dose"), protocol.get("timing")]
    if status == "not_specified" and any(value is not None for value in details):
        raise ExposureProxyError("unspecified microbubble protocol must have null details")
    if status == "protocol_input" and any(not isinstance(value, str) or not value.strip() for value in details):
        raise ExposureProxyError("microbubble protocol_input requires product, dose, and timing")
    if status not in {"not_specified", "protocol_input"}:
        raise ExposureProxyError("unknown microbubble protocol status")


def sensitivity_levels(nominal_pnp_pa: float, frequency_hz: float, scales: list[float]) -> list[dict[str, float]]:
    if nominal_pnp_pa <= 0 or frequency_hz <= 0:
        raise ExposureProxyError("nominal PNP and frequency must be positive")
    rows = []
    for scale in scales:
        if not math.isfinite(scale) or scale <= 0:
            raise ExposureProxyError("sensitivity scales must be finite and positive")
        pnp = nominal_pnp_pa * scale
        rows.append({
            "scale": float(scale),
            "pnp_pa": float(pnp),
            "mechanical_index": mechanical_index(pnp, frequency_hz, "waveform_derived_insitu_pnp"),
            "relative_intensity_proxy": float(scale**2),
            "relative_heating_source_proxy": float(scale**2),
        })
    return rows


def build_proxy(
    frequency_hz: float,
    pressure_pa: float,
    pressure_semantics: str,
    microbubble: dict[str, Any],
    burst_cycles: int | None = None,
    prf_hz: float | None = None,
    total_sonication_time_s: float | None = None,
    sensitivity_scales_values: list[float] | None = None,
) -> dict[str, Any]:
    validate_microbubble(microbubble)
    waveform_pnp = pressure_semantics == "waveform_derived_insitu_pnp"
    result: dict[str, Any] = {
        "frequency_hz": float(frequency_hz),
        "pressure_pa": float(pressure_pa),
        "pressure_semantics": pressure_semantics,
        "mechanical_index": mechanical_index(pressure_pa, frequency_hz, pressure_semantics) if waveform_pnp else None,
        "mi_status": "computed_from_waveform_pnp" if waveform_pnp else "blocked_no_waveform_pnp",
        "microbubble": microbubble,
        "pulse_timing": None,
        "sensitivity_levels": None,
        "clinical_dose_recommendation": False,
    }
    timing_values = (burst_cycles, prf_hz, total_sonication_time_s)
    if any(value is not None for value in timing_values):
        if any(value is None for value in timing_values):
            raise ExposureProxyError("burst_cycles, PRF, and total time must be provided together")
        result["pulse_timing"] = pulse_timing(frequency_hz, int(burst_cycles), float(prf_hz), float(total_sonication_time_s))
    if sensitivity_scales_values is not None:
        if not waveform_pnp:
            raise ExposureProxyError("pressure sensitivity levels require waveform-derived PNP")
        result["sensitivity_levels"] = sensitivity_levels(pressure_pa, frequency_hz, sensitivity_scales_values)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the current Case 079 BBB exposure-proxy boundary report.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    heldout = json.loads(HELDOUT.read_text(encoding="utf-8"))
    h1 = next(row for row in heldout["trajectories"] if row["trajectory"] == "offset_y-10p0_z-02p5")
    pressure_pa = float(h1["pressure"]["target_window_peak_mpa"]) * 1e6
    proxy = build_proxy(
        frequency_hz=500000.0,
        pressure_pa=pressure_pa,
        pressure_semantics="absolute_peak_magnitude_not_waveform_pnp",
        microbubble={"status": "not_specified", "product": None, "dose": None, "timing": None},
    )
    report = {
        "status": "blocked_for_bbb_dose_metrics",
        "trajectory": "offset_y-10p0_z-02p5",
        "input_pressure_source": "heldout target-window absolute peak magnitude",
        "proxy": proxy,
        "blockers": [
            "waveform_derived_insitu_pnp_unavailable",
            "bbb_pulse_train_not_specified",
            "microbubble_protocol_not_specified",
            "pcd_ae_signal_not_available",
        ],
        "configured_future_sensitivity_scales": evidence["sensitivity_scales"],
        "pressure_executed": False,
        "clinical_safety_claim": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "exposure_proxy_boundary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
