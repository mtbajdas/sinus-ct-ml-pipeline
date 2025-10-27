"""
Quick validator to dummy-test clinical findings on synthetic scenarios.
Generates 3 cases and runs the clinical investigation:
- normal
- mucosal_severe (6mm)
- opacified_maxillary_left
Outputs a summary JSON at docs/metrics/validation_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import nibabel as nib
import numpy as np

# Local imports
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from clinical_investigation import run_clinical_investigation  # type: ignore
from synthetic_generator import SyntheticSinusGenerator  # type: ignore


def _save_nifti(volume: np.ndarray, spacing, path: Path) -> None:
    affine = np.diag(list(spacing) + [1.0])
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(volume.astype(np.float32), affine), str(path))


def _write_meta(path: Path, patient_id: str, study_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"patient_id": patient_id, "study_date": study_date}))


def main() -> None:
    out_summary = Path('docs/metrics/validation_summary.json')
    out_summary.parent.mkdir(parents=True, exist_ok=True)

    gen = SyntheticSinusGenerator(seed=7)

    scenarios = []

    # Scenario 1: Normal
    base = gen.generate_base_anatomy()
    scenarios.append(("normal", base))

    # Scenario 2: Mucosal severe (6mm)
    mucosal, _ = gen.add_mucosal_thickening(base, thickness_mm=6.0)
    scenarios.append(("mucosal_severe", mucosal))

    # Scenario 3: Opacified left maxillary
    opacified, _ = gen.add_complete_opacification(base, sinus_name='maxillary_left')
    scenarios.append(("opacified_left_maxillary", opacified))

    results = []

    for name, vol in scenarios:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            nifti = td / 'data' / 'processed' / f'{name}.nii.gz'
            meta = td / 'docs' / 'last_run_meta.json'
            out_png = ROOT / 'docs' / 'validation' / f'{name}.png'
            out_json = ROOT / 'docs' / 'metrics' / f'{name}_report.json'

            _save_nifti(vol, gen.spacing, nifti)
            _write_meta(meta, patient_id=f'DUMMY_{name}', study_date='20251026')

            report = run_clinical_investigation(
                nifti_path=nifti,
                meta_path=meta,
                out_png=out_png,
                out_json=out_json,
                quiet=True,
            )

            m = report['metrics']
            results.append({
                'scenario': name,
                'retention_cysts': m['retention_cysts'],
                'omc_left': m['omc_patency']['left_score'],
                'omc_right': m['omc_patency']['right_score'],
                'sclerotic_pct': m['bony_changes']['sclerotic_fraction_pct'],
                'np_airway_pct': m['nasopharynx']['airway_fraction_pct'],
                'mucosa2_soft_frac': m['mucosal_thickening']['2']['soft_tissue_fraction'],
                'mucosa6_soft_frac': m['mucosal_thickening']['6']['soft_tissue_fraction'],
            })

    out_summary.write_text(json.dumps(results, indent=2))
    print("Validation complete. Summary:")
    for r in results:
        print(f"- {r['scenario']}: cysts={r['retention_cysts']}, OMC(L/R)={r['omc_left']:.1f}/{r['omc_right']:.1f}, "
              f"sclerosis={r['sclerotic_pct']:.1f}%")
    print(f"\nSaved: {out_summary}")


if __name__ == '__main__':
    main()
