"""
Analyze NLM Case 72m k-Wave quick run results.
"""
import json
import numpy as np
from pathlib import Path

OUT = Path("outputs/kwave_3d_focus")

s = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
pmax = np.load(str(OUT / "pressure_max_mpa.npz"))["pressure_max_mpa"]

print("=" * 55)
print("NLM Case 72m — k-Wave Quick Run Results")
print("=" * 55)

print(f"\nGrid shape:       {s['model_shape']}")
print(f"Runtime:          {s['runtime']['runtime_s']/60:.1f} min")
print(f"Voxels:           {s['simulation_quality']['voxel_count']}")
print(f"Source points:    {s['source']['source_points']}")
print(f"Skull crossing:   {s['entry_plan']['skull_path_length_mm']:.1f} mm")

p = s["pressure"]
print(f"\n--- Pressure Metrics ---")
print(f"Global peak:         {p['global_peak_mpa']:.3f} MPa  at {p['global_peak_index_ijk']}")
print(f"  → distance to target: {p['global_peak_to_target_distance_mm']:.1f} mm")
print(f"Target-window peak:  {p['target_window_peak_mpa']:.3f} MPa  at {p['target_window_peak_index_ijk']}")
print(f"Target/Global ratio: {p['target_to_global_peak_ratio']:.4f}")
print(f"Post-entry peak:     {p['post_entry_peak_mpa']:.3f} MPa")
print(f"  → axial from source:  {p['post_entry_peak_axial_from_source_mm']:.1f} mm")
print(f"  → shortfall to target: {p['post_entry_peak_axial_shortfall_to_target_mm']:.1f} mm")

print(f"\n--- Skull Entry Region (crop coords) ---")
entry_slice = pmax[38:48, :, :]
print(f"Max pressure near x=38-48: {float(np.max(entry_slice)):.3f} MPa")
print(f"Mean pressure near x=38-48: {float(np.mean(entry_slice)):.3f} MPa")

print(f"\n--- Target Zone (crop coords) ---")
target_slice = pmax[130:145, :, :]
print(f"Max pressure near target: {float(np.max(target_slice)):.3f} MPa")
print(f"Mean pressure near target: {float(np.mean(target_slice)):.3f} MPa")

# Source label composition
sc = s["source"]["source_label_counts"]
print(f"\n--- Source Label Composition ---")
print(f"Label 0 (bkg):   {sc.get('0', 0)}")
print(f"Label 1 (tissue): {sc.get('1', 0)}")
print(f"Label 2 (skull):  {sc.get('2', 0)}")

print(f"\n--- Comparison: Case 079 (+5,0) vs NLM 72m ---")
print(f"{'Metric':<30} {'Case 079':>12} {'NLM 72m':>12}")
print(f"{'-'*30} {'-'*12} {'-'*12}")
print(f"{'Global peak (MPa)':<30} {9.698:>12.3f} {p['global_peak_mpa']:>12.3f}")
print(f"{'Target-window (MPa)':<30} {0.596:>12.3f} {p['target_window_peak_mpa']:>12.3f}")
print(f"{'T/G ratio':<30} {0.055:>12.4f} {p['target_to_global_peak_ratio']:>12.4f}")
print(f"{'Skull path (mm)':<30} {'unknown':>12} {s['entry_plan']['skull_path_length_mm']:>12.1f}")

print(f"\n--- Conclusion ---")
tw = p['target_window_peak_mpa']
gp = p['global_peak_mpa']
print(f"Target-window pressure: {tw:.3f} MPa — insufficient for BBB opening")
print(f"Global skull hotspot: {gp:.3f} MPa — energy trapped at skull entry")
print(f"This is consistent with Case 079 pattern: skull dominates the pressure field")
print(f"NLM 72m material properties differ but same physical limitation applies.")