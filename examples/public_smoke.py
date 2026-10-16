"""Synthetic geometry/configuration smoke check. Does not run a wave solver."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bbb_roi import sphere_mask, summarize_roi
from simulation_quality import get_preset


def main():
    spacing = (0.001, 0.001, 0.001)
    mask = sphere_mask((21, 21, 21), (10, 10, 10), spacing, 0.003)
    summary = summarize_roi(mask, spacing)
    assert summary['voxel_count'] > 0
    assert summary['centroid_ijk'] == [10.0, 10.0, 10.0]
    preset = get_preset('quick')
    print(json.dumps({
        'status': 'passed', 'input': 'synthetic_geometry_only',
        'voxel_count': summary['voxel_count'], 'preset_loaded': preset['preset'],
        'solver_started': False, 'medical_data_used': False,
        'claim_boundary': 'Software smoke check only; no acoustic or safety validation.'
    }, indent=2))


if __name__ == '__main__':
    main()
