"""Compare frozen PUB.2 CFL0.2 and recovered CFL0.1 baseline fields."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "outputs/pub2_250khz_reference_pair_throttled_20260807/baseline"
CANDIDATE = ROOT / "outputs/pub2_250khz_cfl0p1_baseline_recovery1_20260812"
OUTPUT = ROOT / "outputs/pub2_250khz_cfl0p1_baseline_analysis_20260812"
CONTRACT = ROOT / "paper/PUB2_VERIFICATION_CONTRACT_20260812.json"
CONFIG_KEYS = ("model_path","entry_plan_path","frequency_hz","source_pressure_pa","transducer_radius_m","aperture_diameter_m","tone_burst_cycles","simulation_time_s","pml_size","preset","backend","device","quick_mode","quick_lateral_half_width_m","quick_post_target_margin_m","alpha_power","nearfield_exclusion_m","record_target_waveform","allow_entry_plan_resolution_mismatch")
METRICS = ("global_peak_mpa","target_pressure_mpa","target_window_peak_mpa","target_to_global_peak_ratio","global_peak_to_target_distance_mm","effective_peak_mpa","effective_peak_to_target_distance_mm","target_to_effective_peak_ratio")

def load(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def field(path: Path) -> dict[str, Any]:
    with np.load(path,allow_pickle=False) as a:
        return {"p":np.asarray(a["pressure_max_mpa"],dtype=np.float64),"origin":np.asarray(a["crop_origin_ijk"],dtype=int),"target":np.asarray(a["target_index_ijk"],dtype=int),"dx":float(np.asarray(a["dx_m"])),"source_points":int(np.asarray(a["source_mask"]).sum())}

def build() -> dict[str, Any]:
    rs,cs=load(REFERENCE/"summary.json"),load(CANDIDATE/"summary.json")
    rm,cm=load(REFERENCE/"focus_metrics.json"),load(CANDIDATE/"focus_metrics.json")
    rf,cf=field(REFERENCE/"pressure_max_mpa.npz"),field(CANDIDATE/"pressure_max_mpa.npz")
    mismatches=[k for k in CONFIG_KEYS if rs["config"].get(k)!=cs["config"].get(k)]
    diff=cf["p"]-rf["p"]; refnorm=float(np.linalg.norm(rf["p"].ravel())); refmax=float(np.max(np.abs(rf["p"])))
    l2=100*float(np.linalg.norm(diff.ravel()))/refnorm; linf=100*float(np.max(np.abs(diff)))/refmax
    scalar={}
    for k in METRICS:
        left,right=float(rm[k]),float(cm[k]); scalar[k]={"cfl0p2":left,"cfl0p1":right,"difference":right-left,"relative_difference_percent":None if left==0 else 100*(right-left)/abs(left)}
    limits=load(CONTRACT)["acceptance_criteria"]["time_step_sensitivity"]["limits"]
    checks={
      "execution_completed":load(CANDIDATE/"execution_status.json").get("status")=="completed",
      "monitor_completed":load(CANDIDATE/"monitor_status.json").get("status")=="completed",
      "only_cfl_changed":mismatches==[] and rs["config"].get("cfl")==0.2 and cs["config"].get("cfl")==0.1,
      "same_shape_origin_target_dx":rf["p"].shape==cf["p"].shape and np.array_equal(rf["origin"],cf["origin"]) and np.array_equal(rf["target"],cf["target"]) and rf["dx"]==cf["dx"],
      "source_points_equal_4971":rf["source_points"]==cf["source_points"]==4971,
      "dt_halved_nt_doubled":np.isclose(cs["simulation_quality"]["dt_s"],rs["simulation_quality"]["dt_s"]/2) and cs["simulation_quality"]["nt"]==2*rs["simulation_quality"]["nt"],
      "fields_finite_nonzero":bool(np.isfinite(rf["p"]).all() and np.isfinite(cf["p"]).all() and cf["p"].max()>0),
      "relative_l2_within_contract":l2<=limits["relative_l2_percent_max"],
      "relative_linf_within_contract":linf<=limits["relative_linf_percent_max"],
      "target_pressure_within_contract":abs(scalar["target_pressure_mpa"]["relative_difference_percent"])<=limits["target_pressure_relative_change_percent_max"],
      "peak_distance_within_contract":abs(scalar["global_peak_to_target_distance_mm"]["difference"])<=limits["peak_to_target_distance_change_mm_max"],
      "ratio_within_contract":abs(scalar["target_to_global_peak_ratio"]["difference"])<=limits["target_to_global_ratio_absolute_change_max"]}
    return {"schema_version":"1.0","report_id":"pub2_250khz_cfl0p1_baseline_analysis_20260812","generated_at_utc":datetime.now(timezone.utc).isoformat(),"status":"passed" if all(checks.values()) else "failed","claim_level":"single_case_baseline_time_step_sensitivity_observation","checks":checks,"config_mismatches_excluding_cfl":mismatches,"field_difference":{"relative_l2_percent":l2,"relative_linf_percent":linf,"max_absolute_difference_mpa":float(np.max(np.abs(diff))),"mean_absolute_difference_mpa":float(np.mean(np.abs(diff)))},"scalar_metrics":scalar,"runtime_s":{"cfl0p2":float(rs["runtime"]["runtime_s"]),"cfl0p1":float(cs["runtime"]["runtime_s"])},"artifacts":{"reference_sha256":sha(REFERENCE/"pressure_max_mpa.npz"),"candidate_sha256":sha(CANDIDATE/"pressure_max_mpa.npz")},"decision":{"baseline_time_step_contract_passed":all(checks.values()),"formal_convergence_established":False,"tr_time_step_sensitivity_established":False,"automatic_additional_cells_authorized":False},"claim_boundary":"One baseline CFL0.2-to-0.1 perturbation; it does not establish TR time-step robustness, formal convergence, absolute-pressure accuracy, efficacy or safety."}

def main() -> int:
    r=build(); OUTPUT.mkdir(parents=True,exist_ok=True); (OUTPUT/"cfl0p1_baseline_analysis.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    f=r["field_difference"]; s=r["scalar_metrics"]
    (OUTPUT/"cfl0p1_baseline_analysis.md").write_text(f"# PUB.2 CFL0.1 baseline sensitivity\n\n- Status: **{r['status']}**\n- Field L2/L∞: `{f['relative_l2_percent']:.6g}%` / `{f['relative_linf_percent']:.6g}%`\n- Target pressure change: `{s['target_pressure_mpa']['relative_difference_percent']:+.6g}%`\n- Peak-distance change: `{s['global_peak_to_target_distance_mm']['difference']:+.6g} mm`\n- Target/global ratio change: `{s['target_to_global_peak_ratio']['difference']:+.6g}`\n\n{r['claim_boundary']}\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"output":str(OUTPUT)})); return 0 if r["status"]=="passed" else 1
if __name__=="__main__": raise SystemExit(main())
