import subprocess
import sys
from pathlib import Path

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(f"Error executing command: {res.stderr}")
        sys.exit(1)
    else:
        print(res.stdout)

def main():
    python_path = "D:/AIprogram/python-envs/kwave312/Scripts/python.exe"
    
    # 1. Run generate_entry_path_property_profile.py
    generate_script = "generate_entry_path_property_profile.py"
    entry_plan = "outputs/ct_sweep_scan_079_fit_alpha_2/sweep_020_entry_plan.json"
    output_dir = "outputs/entry_path_property_profiles/threshold_sensitivity_sweep_020"
    
    args = [
        python_path,
        generate_script,
        "--entry-plan", entry_plan,
        "--model", "bone_250=outputs/ct_acoustic_model_3d_bone_250",
        "--model", "bone_300=outputs/ct_acoustic_model_3d_bone_300",
        "--model", "bone_400=outputs/ct_acoustic_model_3d_bone_400",
        "--output-dir", output_dir,
        "--include-entry-neighborhood"
    ]
    run_cmd(args)
    
    # 2. Run plot_entry_path_property_profile.py
    plot_script = "plot_entry_path_property_profile.py"
    plot_args = [
        python_path,
        plot_script,
        "--input-dir", output_dir,
        "--path-name", "source_to_target"
    ]
    run_cmd(plot_args)
    
    print("Profiling and plotting completed successfully!")

if __name__ == "__main__":
    main()
