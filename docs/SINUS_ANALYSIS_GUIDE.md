# Sinus Analysis - Quick Reference Guide

## Overview
This guide shows you how to best view and use the **sinus analysis** side of the repository.

---

## Core Sinus Module

### Location: `src/sinus/`

```python
from sinus import (
    # Anatomical measurements
    measure_omc_patency_coronal,     # OMC drainage pathway analysis
    build_sinus_wall_shell,          # Generate wall shell for bone analysis
    estimate_reference_bone_stats,   # Reference bone HU statistics
    
    # Pathology detection
    compute_sclerosis_zscore,        # Bone sclerosis quantification
    detect_retention_cysts_strict,   # Fluid-filled lesion detection
)
```

### Files:
- **`anatomical.py`** (349 lines) - OMC patency, wall shell, reference bone
- **`pathology.py`** (165 lines) - Sclerosis detection, retention cysts

---

## Running Sinus Analysis

### 1. Basic Pipeline (DICOM → NIfTI with Calibration)
```bash
python src/pipeline.py \
  --dicom-dir data/raw/my_scan \
  --output-nifti data/processed/sinus_ct.nii.gz \
  --view-step 20
```

**Output:**
- `data/processed/sinus_ct.nii.gz` - Calibrated volume
- `docs/last_run_meta.json` - Scan metadata (spacing, patient ID, etc.)

---

### 2. Full Clinical Investigation
```bash
python src/clinical_investigation.py \
  --nifti data/processed/sinus_ct.nii.gz \
  --output docs/metrics/clinical_analysis_report.json
```

**Measures:**
- ✓ OMC patency (left/right)
- ✓ Sclerotic bone fraction
- ✓ Retention cyst count and locations
- ✓ Lund-Mackay staging scores
- ✓ Volumetric analysis (air vs tissue)

**Output:** JSON file with all metrics

---

### 3. Generate Comprehensive PDF Report
```bash
python src/generate_report.py \
    --clinical docs/metrics/clinical_analysis_report.json \
    --meta docs/last_run_meta.json \
    --output docs/report/comprehensive_report.pdf
```

**Features:**
- ✓ Objective data presentation (no clinical bias)
- ✓ Reference ranges from literature
- ✓ Technical parameters documented
- ✓ Methodology section included
- ✓ Clean, professional formatting

**Output:** `docs/report/comprehensive_report.pdf`

---

### 4. 3D Visualization
```bash
python src/visualization/visualize_3d.py \
  --nifti data/processed/sinus_ct.nii.gz \
  --iso -300 \
  --downsample 2
```

**Output:** Interactive HTML with 3D mesh (air cavities at -300 HU threshold)

---

## Validation Test

### Ground Truth Validation (Orlando Normal Scan)
```bash
python tests/test_orlando_normal.py
```

**Expected:**
```
[PASS]: HU Calibration
[PASS]: OMC Patency (Patent bilaterally: L=14.6%, R=18.9%)
[PASS]: Sclerotic Fraction (3.2% - within normal <5%)
[PASS]: Cyst Count (0 - matches "clear" report)
SUCCESS: ALL TESTS PASSED
```

---

## Key Sinus Metrics Explained

### 1. OMC Patency
**What it measures:** Air fraction in ostiomeatal complex drainage corridors

**Method:**
- Standardized ROI boxes at mid-facial level
- Multi-candidate optimization (selects best of 5 positions)
- Air threshold: < -400 HU

**Classification:**
- **Patent:** > 12% air fraction
- **Indeterminate:** 8-12% air fraction  
- **Obstructed:** < 8% air fraction

**Clinical significance:** OMC obstruction → impaired drainage → recurrent sinusitis

---

### 2. Sclerotic Bone Fraction
**What it measures:** Percentage of sinus wall bone with elevated density (chronic inflammation marker)

**Method:**
- Build 3-7mm thick shell around sinus cavities
- Compare wall HU to reference bone (hard palate)
- Compute z-score for each voxel
- Count voxels with z > 2.0

**Reference ranges:**
- **Normal:** < 5%
- **Mild:** 5-15%
- **Moderate:** 15-30%
- **Severe:** > 30%

**Clinical significance:** Elevated sclerosis indicates chronic osteitis (bone remodeling from prolonged inflammation)

---

### 3. Retention Cysts
**What it measures:** Fluid-filled benign lesions in maxillary sinuses

**Detection criteria:**
- HU range: 0-60 (fluid density)
- Location: Maxillary sinus boundaries only
- Position: Inferior 40% (gravity-dependent)
- Size: ≥ 50 voxels

**Reference range:** 0-2 cysts (normal)

**Clinical significance:** Asymptomatic but indicates mucus stasis

---

### 4. Lund-Mackay Staging
**What it measures:** Semi-quantitative staging of chronic rhinosinusitis

**Scoring:**
- Each sinus (L/R): 0 (clear), 1 (partial), 2 (complete opacification)
- Regions: Maxillary, Anterior Ethmoid, Posterior Ethmoid, Sphenoid, Frontal
- OMC: 0 (patent) or 2 (obstructed)

**Total scores:**
- **LM-20:** 10 sinuses × 2 points = 0-20 range
- **LM-24:** 10 sinuses + 2 OMCs × 2 points = 0-24 range

**Interpretation:**
- 0: Normal
- 1-4: Mild
- 5-10: Moderate
- 11-20: Severe

---

## Python API Examples

### Basic Usage
```python
import nibabel as nib
from calibration import calibrate_volume
from sinus import measure_omc_patency_coronal, compute_sclerosis_zscore

# Load CT scan
img = nib.load('data/processed/sinus_ct.nii.gz')
volume = img.get_fdata()
spacing = img.header.get_zooms()[:3]

# Calibrate HU values
vol_calibrated, metadata = calibrate_volume(volume, spacing)

# Measure OMC patency
omc_result = measure_omc_patency_coronal(
    vol_calibrated, 
    spacing, 
    z_slice=120,  # mid-facial slice
    threshold_patent=0.12,
    threshold_obstructed=0.08
)

print(f"Left OMC: {omc_result['left']['status']} ({omc_result['left']['patency_pct']:.1f}%)")
print(f"Right OMC: {omc_result['right']['status']} ({omc_result['right']['patency_pct']:.1f}%)")

# Compute sclerosis
sclerosis_pct = compute_sclerosis_zscore(vol_calibrated, spacing)
print(f"Sclerotic fraction: {sclerosis_pct:.1f}%")
```

### Advanced: Custom Analysis
```python
from sinus import (
    build_sinus_wall_shell,
    estimate_reference_bone_stats,
    detect_retention_cysts_strict
)

# Build wall shell for custom analysis
wall_shell_mask = build_sinus_wall_shell(
    vol_calibrated, 
    spacing,
    inner_margin_mm=3.0,
    outer_margin_mm=7.0
)

# Get reference bone statistics
ref_stats = estimate_reference_bone_stats(vol_calibrated, spacing)
print(f"Reference bone: {ref_stats['median']:.0f} ± {ref_stats['std']:.0f} HU")

# Detect cysts
cysts = detect_retention_cysts_strict(vol_calibrated, spacing)
print(f"Found {len(cysts)} retention cysts")
for i, cyst in enumerate(cysts, 1):
    print(f"  Cyst {i}: {cyst['volume_ml']:.1f} mL at {cyst['centroid']}")
```

---

## File Organization

### Input Data
```
data/
├── raw/                    # Raw DICOM files
│   └── <study_name>/
│       └── <series_uid>/
│           └── *.dcm
└── processed/              # Converted NIfTI volumes
    └── sinus_ct.nii.gz
```

### Output Files
```
docs/
├── last_run_meta.json                    # Scan metadata
├── sinus-report.pdf                      # Unbiased analysis report
├── metrics/
│   └── clinical_analysis_report.json     # All measurements
└── validation/
    └── orlando_normal_results.json       # Ground truth test results
```

---

## Notebooks

### Calibration Validation Notebook
```bash
# Open in Jupyter
jupyter notebook notebooks/05_calibration_validation.ipynb
```

**Contents:**
- HU calibration verification
- OMC ROI visualization
- Sclerosis z-score distribution
- Interactive slice viewing

---

## Documentation

### Technical Details
- **`METHODS.md`** - Complete methodology for all sinus measurements
  - HU calibration formulas
  - OMC patency algorithm
  - Sclerosis detection method
  - Validation framework

### Architecture
- **`REORGANIZATION_SUMMARY.md`** - Module structure and migration guide
- **`README.md`** - Project overview and quick start

---

## Quick Commands Cheat Sheet

```bash
# 1. Convert DICOM to NIfTI with calibration
python src/pipeline.py --dicom-dir data/raw/scan123 --output-nifti data/processed/sinus_ct.nii.gz

# 2. Run full sinus analysis
python src/clinical_investigation.py --nifti data/processed/sinus_ct.nii.gz

# 3. Generate PDF report
python src/generate_report.py

# 4. Create 3D visualization
python src/visualization/visualize_3d.py --nifti data/processed/sinus_ct.nii.gz --iso -300

# 5. Run validation test
python tests/test_orlando_normal.py

# 6. Open validation notebook
jupyter notebook notebooks/05_calibration_validation.ipynb
```

---

## Workflow Diagram

```
DICOM Series
    ↓
[pipeline.py] → NIfTI + HU Calibration
    ↓
[clinical_investigation.py] → Sinus Metrics (JSON)
    ↓
[generate_report.py] → Comprehensive PDF Report
    ↓
Review + Clinical Context
```

---

## Reference Ranges Summary

| Metric | Normal Range | Method |
|--------|--------------|--------|
| OMC Patency | > 12% | Multi-candidate corridor |
| Sclerotic Fraction | < 5% | Z-score > 2.0 |
| Retention Cysts | 0-2 | Strict anatomical rules |
| Lund-Mackay Total | 0-4 (mild) | Semi-quantitative staging |
| Air Fraction | > 95% | Threshold < -400 HU |

---

## Support

For questions or issues:
- See `METHODS.md` for technical details
- Check `tests/test_orlando_normal.py` for validation examples
- Review `src/sinus/anatomical.py` and `src/sinus/pathology.py` for implementation

---

**Bottom Line:** The sinus analysis is fully validated and ready for quantitative assessment. Use `generate_report.py` for a single comprehensive PDF that includes sinus, skull, ear, and brain sections.
