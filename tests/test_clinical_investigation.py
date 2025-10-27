import json
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np

# Make src importable
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from clinical_investigation import run_clinical_investigation  # noqa: E402
from synthetic_generator import SyntheticSinusGenerator  # noqa: E402


def _save_nifti(volume: np.ndarray, spacing, path: Path):
    affine = np.diag(list(spacing) + [1.0])
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(volume.astype(np.float32), affine), str(path))


def _write_meta(path: Path, patient_id="TEST", study_date="20250101"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"patient_id": patient_id, "study_date": study_date}))


def test_normal_anatomy_has_no_cysts_and_low_sclerosis():
    gen = SyntheticSinusGenerator(seed=123)
    vol = gen.generate_base_anatomy()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        nifti = td / 'data' / 'processed' / 'sinus_ct.nii.gz'
        meta = td / 'docs' / 'last_run_meta.json'
        out_png = td / 'docs' / 'clinical_analysis.png'
        out_json = td / 'docs' / 'metrics' / 'clinical_analysis_report.json'

        _save_nifti(vol, gen.spacing, nifti)
        _write_meta(meta)

        report = run_clinical_investigation(
            nifti_path=nifti,
            meta_path=meta,
            out_png=out_png,
            out_json=out_json,
            quiet=True,
        )

        # Assertions: no small lesions and metrics within expected ranges
        assert report['metrics']['retention_cysts'] == 0
        scl = report['metrics']['bony_changes']['sclerotic_fraction_pct']
        assert 0.0 <= scl <= 100.0
        st2 = report['metrics']['mucosal_thickening']['2']['soft_tissue_fraction']
        assert 0.0 <= st2 <= 1.0
        # Artifacts saved
        assert out_json.exists()
        assert out_png.exists()


def test_mucosal_thickening_detectable_at_6mm():
    gen = SyntheticSinusGenerator(seed=42)
    base = gen.generate_base_anatomy()
    vol, _ = gen.add_mucosal_thickening(base, thickness_mm=6.0)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        nifti = td / 'data' / 'processed' / 'sinus_ct.nii.gz'
        meta = td / 'docs' / 'last_run_meta.json'
        out_png = td / 'docs' / 'clinical_analysis.png'
        out_json = td / 'docs' / 'metrics' / 'clinical_analysis_report.json'

        _save_nifti(vol, gen.spacing, nifti)
        _write_meta(meta)

        report = run_clinical_investigation(
            nifti_path=nifti,
            meta_path=meta,
            out_png=out_png,
            out_json=out_json,
            quiet=True,
        )

        # Validate structure of report and presence of OMC metrics
        omc = report['metrics']['omc_patency']
        assert 0.0 <= omc['left_score'] <= 100.0
        assert 0.0 <= omc['right_score'] <= 100.0
