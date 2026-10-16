"""Independently validate recovered PUB.2 CFL0.1 baseline package."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent; RUN=ROOT/"outputs/pub2_250khz_cfl0p1_baseline_recovery1_20260812"; ANALYSIS=ROOT/"outputs/pub2_250khz_cfl0p1_baseline_analysis_20260812/cfl0p1_baseline_analysis.json"; OUTPUT=ROOT/"outputs/pub2_250khz_cfl0p1_baseline_validation_20260812"
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def nums(rows,k): return [float(r[k]) for r in rows if isinstance(r.get(k),(int,float)) and np.isfinite(r[k])]
def main():
    stage,exe,mon,analysis=map(load,[RUN/"stage_result.json",RUN/"execution_status.json",RUN/"monitor_status.json",ANALYSIS])
    with np.load(RUN/"pressure_max_mpa.npz",allow_pickle=False) as a: p=np.asarray(a["pressure_max_mpa"]); field_ok=p.shape==(133,98,101) and np.isfinite(p).all() and p.max()>0
    rows=[json.loads(x) for x in (RUN/"device_history.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    ext={"max_equivalent_cores":max(nums(rows,"equivalent_cores")),"max_working_set_gib":max(nums(rows,"working_set_gib")),"min_system_free_memory_gib":min(nums(rows,"system_free_memory_gib")),"samples":len(rows)}
    checks={"execution_completed":exe.get("status")=="completed","stage_outputs_passed":stage.get("status")=="completed" and stage["output_validation"]["status"]=="passed","monitor_completed":mon.get("status")=="completed" and mon.get("return_code")==0,"field_expected_finite_nonzero":bool(field_ok),"summary_cfl0p1":load(RUN/"summary.json")["config"]["cfl"]==0.1,"focus_numeric":isinstance(load(RUN/"focus_metrics.json").get("global_peak_mpa"),(int,float)),"analysis_passed":analysis.get("status")=="passed","cpu_gate":ext["max_equivalent_cores"]<=6.5,"working_set_gate":ext["max_working_set_gib"]<=16,"free_memory_gate":ext["min_system_free_memory_gib"]>=4,"no_extra_cells":analysis["decision"]["automatic_additional_cells_authorized"] is False}
    r={"schema_version":"1.0","generated_at_utc":datetime.now(timezone.utc).isoformat(),"status":"passed" if all(checks.values()) else "failed","checks":checks,"device_extrema":ext,"claim_boundary":"Package integrity plus one baseline time-step sensitivity; not formal convergence or experimental validation."}
    OUTPUT.mkdir(parents=True,exist_ok=True); (OUTPUT/"package_validation.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (OUTPUT/"package_validation.md").write_text(f"# CFL0.1 baseline package validation\n\n- Status: **{r['status']}**\n- Checks: {sum(checks.values())}/{len(checks)}\n- Device extrema: `{ext}`\n\n{r['claim_boundary']}\n",encoding="utf-8"); print(json.dumps({"status":r["status"],"checks":checks})); return 0 if r["status"]=="passed" else 1
if __name__=="__main__": raise SystemExit(main())
