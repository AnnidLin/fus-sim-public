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
    script_path = "build_ct_acoustic_model.py"
    
    thresholds = [250, 300, 400]
    for threshold in thresholds:
        print(f"=== Rebuilding CT acoustic model for bone threshold HU = {threshold} ===")
        args = [
            python_path,
            script_path,
            "--nifti-file", "data/raw_ct/079.nii",
            "--mapping-profile", "acoustic_mapping_profiles/prestus_fit_alpha_power_2.json",
            "--bone-threshold-hu", str(threshold),
            "--output-dir", f"outputs/ct_acoustic_model_3d_bone_{threshold}"
        ]
        run_cmd(args)
    print("All model builds completed successfully!")

if __name__ == "__main__":
    main()
