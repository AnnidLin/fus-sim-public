import json
from pathlib import Path
import numpy as np

# Import functions from plan_transducer_sweep
import sys
sys.path.append(str(Path("d:/AIprogram/fus-sim")))
from plan_transducer_sweep import generate_spherical_candidates, load_model

def main():
    model_path = Path("d:/AIprogram/fus-sim/outputs/ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2/acoustic_model_3d.npz")
    labels, dx_m, target = load_model(model_path)
    
    # We will search with default parameters and match theta_deg=35.0, phi_deg=-15.0
    radius_mm = 30.0 # default radius
    aperture_mm = 25.0 # default aperture
    source_standoff_mm = 8.0 # default standoff
    
    # Let's test different radius/aperture combinations to match candidates_valid.csv values
    # candidates_valid.csv for sweep_020:
    # theta=35.0, phi=-15.0
    # source_points=334
    # skull_path_length_mm=2.236068
    # incidence_angle_deg=10.506303
    # source_to_target_distance_mm=134.896263
    # source_to_entry_distance_mm=8.124039
    # heuristic_transmission_proxy=0.786224
    
    # Grid units
    # Note: radius_gp is round(radius_mm * 1e-3 / dx_m)
    # Let's test combinations of radius_mm = [30.0, 35.0, 130.0, 135.0]
    # Wait, source_to_target_distance is 134.896 mm.
    # The source_to_target_distance is equal to np.linalg.norm(target - source) * dx_m * 1000
    # Let's check how the sweep was generated. Let's run a test loop to find the matching combination.
    
    found = None
    # Let's try different radius/aperture parameters
    for r in [30.0, 35.0, 134.896, 135.0]:
        for ap in [25.0, 30.0, 40.0]:
            for standoff in [8.0, 8.124]:
                radius_gp = int(round(r * 1e-3 / dx_m))
                from plan_transducer_sweep import odd_grid_points
                diameter_gp = odd_grid_points(ap * 1e-3, dx_m)
                source_standoff_gp = max(1, int(round(standoff * 1e-3 / dx_m)))
                
                candidates = generate_spherical_candidates(
                    labels=labels,
                    dx_m=dx_m,
                    target=target,
                    radius_gp=radius_gp,
                    diameter_gp=diameter_gp,
                    source_standoff_gp=source_standoff_gp,
                    theta_step=5.0,
                    theta_max=40.0,
                    phi_step=15.0,
                    phi_range=(-30.0, 30.0),
                    axis="+x"
                )
                
                for c in candidates:
                    if c["status"] == "valid" and abs(c["theta_deg"] - 35.0) < 1e-3 and abs(c["phi_deg"] - (-15.0)) < 1e-3:
                        # Check matching metrics
                        if abs(c["skull_path_length_mm"] - 2.236068) < 1e-2 and abs(c["source_to_target_distance_mm"] - 134.896) < 1e-1:
                            found = c
                            print(f"Matched candidate parameters: radius={r}, aperture={ap}, standoff={standoff}")
                            break
                if found:
                    break
            if found:
                break
        if found:
            break
            
    if not found:
        print("Error: Could not match sweep_020 candidate with search parameters!")
        # Let's run a wider search or print the candidate list for debugging
        sys.exit(1)
        
    entry_plan = {
        "description": "CT target and entry plan for sweep_020 candidate",
        "entry_direction": "custom_sweep_020",
        "beam_axis": found["beam_unit_vector"],
        "target_index_ijk": found["target_index_ijk"],
        "entry_index_ijk": found["entry_index_ijk"],
        "source_center_index_ijk": found["source_center_index_ijk"],
        "source_center_label": 0,
        "entry_label": 2,
        "target_label": 1,
        "has_skull_crossing": found["has_skull_crossing"],
        "source_standoff_mm": found["source_to_entry_distance_mm"],
        "source_to_entry_distance_mm": found["source_to_entry_distance_mm"],
        "source_to_target_distance_mm": found["source_to_target_distance_mm"],
        "skull_path_length_mm": found["skull_path_length_mm"],
        "dx_m": dx_m,
        "model_shape": list(labels.shape)
    }
    
    output_path = Path("d:/AIprogram/fus-sim/outputs/ct_sweep_scan_079_fit_alpha_2/sweep_020_entry_plan.json")
    output_path.write_text(json.dumps(entry_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Successfully wrote sweep_020 entry plan to {output_path}")

if __name__ == "__main__":
    main()
