# Methods Documentation

## Head CT Analysis Pipeline - Technical Methods

### Overview

This pipeline provides physics-based CT image analysis focused on **sinus and brain pathology**. The modular architecture cleanly separates sinus (current) and brain (future) modules while sharing core calibration infrastructure.

---

## Module Architecture

```
src/
├── calibration/          # HU correction and adaptive thresholding
│   ├── hu_calibration.py       # Air/bone anchor detection
│   └── adaptive_thresholds.py  # Histogram-based segmentation
├── sinus/                # Sinus-specific analysis (CURRENT)
│   ├── anatomical.py           # OMC patency, wall shell
│   └── pathology.py            # Sclerosis, cysts
├── brain/                # Brain-specific analysis (FUTURE)
│   ├── hemorrhage.py           # Acute blood detection
│   ├── midline.py              # Mass effect measurement
│   ├── stroke.py               # Hypodense region segmentation
│   ├── ventricles.py           # CSF space sizing
│   └── skull.py                # Fracture, pneumocephalus
├── reporting/            # Clinical report generation
├── visualization/        # 3D rendering and plots
└── core/                 # DICOM I/O, preprocessing utilities
```

---

## 1. HU Calibration (`src/calibration/`)

### Problem
CT scanners drift over time; HU values may deviate from expected physical anchors (air ≈ -1000 HU, cortical bone ≈ 1200 HU). Uncalibrated scans lead to incorrect tissue segmentation.

### Solution: Two-Point Linear Correction

#### Air Anchor Detection
- **Location**: Peripheral FOV (margins) or nasopharynx
- **Criterion**: Median HU of voxels < -800 HU
- **Expected**: -1000 ± 50 HU
- **Tolerance**: Pass if |measured - expected| ≤ 50 HU

#### Bone Anchor Detection
- **Location**: Hard palate / inferior skull base
- **ROI**: Inferior 60-80% z, central 40% x/y
- **Criterion**: Median HU of voxels > 900 HU
- **Expected**: 1200 ± 200 HU
- **Tolerance**: Pass if |measured - expected| ≤ 200 HU

#### Linear Correction Formula
```
HU_corrected = slope × HU_raw + intercept

where:
  slope = (HU_bone_expected - HU_air_expected) / (HU_bone_measured - HU_air_measured)
  intercept = HU_air_expected - slope × HU_air_measured
```

#### Validation
- Air anchor: -1000 ± 50 HU post-correction
- Bone anchor: 1200 ± 200 HU post-correction
- Metadata saved to `docs/last_run_meta.json`

---

## 2. Adaptive Tissue Thresholding (`src/calibration/`)

### Histogram-Based Air-Tissue Boundary

#### Algorithm
1. Clip to relevant range: [-1000, 100] HU
2. Compute histogram with 256 bins
3. Identify air peak: HU < -300
4. Identify tissue peak: HU > -300
5. Find threshold at 10% valley height between peaks

#### Typical Values (Sinus CT)
- Air peak: -950 to -900 HU
- Tissue peak: -50 to 50 HU
- Threshold: -400 to -300 HU (varies by scan)

#### Usage
```python
from calibration import adaptive_threshold_air_tissue
threshold = adaptive_threshold_air_tissue(volume_calibrated)
air_mask = volume_calibrated < threshold
```

---

## 3. Sinus Analysis (`src/sinus/`)

### 3.1 OMC Patency Measurement (`anatomical.py`)

#### Rationale
Ostiomeatal complex (OMC) is the drainage pathway for maxillary, frontal, and anterior ethmoid sinuses. Obstruction → mucus retention → sinusitis. Quantitative measurement enables tracking over time.

#### Multi-Candidate Corridor Method

##### ROI Definition (Coronal Plane)
```
Left OMC:  x ∈ [42%, 49%], y ∈ [40%, 60%]
Right OMC: x ∈ [51%, 58%], y ∈ [40%, 60%]
```
- Origin: Lower-left corner of scan
- x: Left-right axis (0 = left, 100% = right)
- y: Inferior-superior axis (0 = inferior, 100% = superior)

##### Algorithm
1. **For each side (left/right):**
   - Define 5 candidate ROI boxes (slightly offset in x/y)
   - For each candidate, compute air fraction:
     ```
     air_fraction = (voxels < air_threshold) / total_voxels
     ```
   - Select ROI with **maximum air fraction** as "best corridor"
   
2. **Clinical Classification:**
   - **Patent**: air_fraction > 12%
   - **Indeterminate**: 8% ≤ air_fraction ≤ 12%
   - **Obstructed**: air_fraction < 8%

##### Validation
- Orlando normal scan: Left 14.6% (Patent), Right 18.9% (Patent)
- Matches radiologist assessment: "essentially clear"

---

### 3.2 Sclerosis Detection (`pathology.py`)

#### Rationale
Chronic sinusitis → osteitis → bone thickening (sclerosis). Appears as higher HU in sinus walls compared to reference bone.

#### Method
1. **Build sinus wall shell** (3-7 mm thick) surrounding sinus cavities
2. **Estimate reference bone stats** from hard palate (median HU, std dev)
3. **Compute z-score** for each wall voxel:
   ```
   z = (HU_wall - HU_reference_median) / HU_reference_std
   ```
4. **Sclerotic fraction**: % of wall voxels with z > 2.0

#### Clinical Thresholds
- Normal: < 5% sclerotic
- Mild: 5-15%
- Moderate: 15-30%
- Severe: > 30%

#### Validation
- Orlando normal: 3.2% sclerotic (within normal range)

---

### 3.3 Retention Cyst Detection (`pathology.py`)

#### Rationale
Benign fluid-filled lesions in sinus cavities. Asymptomatic but important to track size/growth.

#### Strict Anatomical Rules
1. **Location**: Must be within maxillary sinus boundaries
2. **HU Range**: 0 to 60 HU (fluid density)
3. **Morphology**: Connected component ≥ 50 voxels
4. **Floor Proximity**: Within inferior 40% of sinus (gravity-dependent)

#### Output
- Cyst count
- Volume (mL) per cyst
- Centroid coordinates (x, y, z)

#### Validation
- Orlando normal: 0 cysts detected (agrees with "clear" report)

---

## 4. Brain Analysis (`src/brain/`) - Future Modules

### 4.1 Hemorrhage Detection (`hemorrhage.py`)

#### Hemorrhage Types
1. **Epidural**: Between skull and dura (lens-shaped, arterial)
2. **Subdural**: Between dura and arachnoid (crescent, venous)
3. **Subarachnoid (SAH)**: CSF spaces (sulci, cisterns)
4. **Intraparenchymal (IPH)**: Within brain tissue
5. **Intraventricular (IVH)**: Within ventricles

#### Detection Strategy
- **Acute blood**: 50-80 HU (high attenuation)
- **Subacute**: 30-50 HU (isodense to brain)
- **Chronic**: 0-30 HU (hypodense)

#### Algorithm (Acute)
1. Threshold: HU > 50 in brain region
2. Connected components
3. Classify by location (epidural vs subdural vs SAH vs IPH vs IVH)
4. Measure volume (mL)
5. Expansion risk: serial scans with volume change

#### Clinical Output
```python
{
    "type": "epidural",
    "volume_ml": 15.3,
    "location": "left frontal",
    "hu_mean": 65,
    "expansion_risk": "moderate"  # if serial available
}
```

---

### 4.2 Midline Shift (`midline.py`)

#### Rationale
Mass effect from hemorrhage, tumor, or edema pushes brain structures across midline → herniation risk.

#### Measurement
1. **Identify falx cerebri** (dural fold, ~70 HU)
2. **Find septum pellucidum** (between lateral ventricles)
3. **Measure deviation** from expected midline
4. **Report shift** in mm (positive = right shift, negative = left shift)

#### Clinical Thresholds
- < 5 mm: Mild
- 5-10 mm: Moderate (urgent evaluation)
- > 10 mm: Severe (neurosurgical emergency)

#### Algorithm
```python
def measure_midline_shift(volume, spacing):
    # Find septum pellucidum (CSF density ~10 HU)
    septum_mask = (volume > 5) & (volume < 20)
    septum_center_x = compute_centroid_x(septum_mask)
    
    # Expected midline at volume center
    expected_x = volume.shape[0] / 2
    
    # Shift in mm
    shift_mm = (septum_center_x - expected_x) * spacing[0]
    return shift_mm
```

---

### 4.3 Stroke Segmentation (`stroke.py`)

#### Rationale
Early ischemic stroke → cytotoxic edema → hypodense regions (20-35 HU). ASPECTS scoring guides thrombolysis decisions.

#### Detection
1. **Threshold**: 20-35 HU (edema range)
2. **Location**: MCA territory (middle cerebral artery)
3. **Exclude**: Normal CSF (ventricles, sulci)
4. **Connected components** → hypodense lesions

#### ASPECTS Scoring (10 regions)
- M1-M6: MCA cortical regions
- C, IC, L, I: Deep structures (caudate, internal capsule, lentiform, insula)
- **Score**: 10 - (number of affected regions)
- **Thrombolysis**: Usually considered if ASPECTS ≥ 6

#### Output
```python
{
    "lesion_volume_ml": 45.2,
    "aspects_score": 7,
    "affected_regions": ["M4", "M5", "insula"],
    "thrombolysis_candidate": True
}
```

---

### 4.4 Ventricular Sizing (`ventricles.py`)

#### Rationale
Hydrocephalus → enlarged ventricles → increased ICP. Evans' index quantifies ventricular enlargement.

#### Evans' Index
```
Evans_index = max_frontal_horn_width / max_internal_skull_width
```
- Normal: < 0.30
- Borderline: 0.30-0.35
- Hydrocephalus: > 0.35

#### Algorithm
1. **Segment ventricles** (0-20 HU, CSF density)
2. **Axial slice** at level of frontal horns
3. **Measure widths** (mm)
4. **Compute ratio**

#### Clinical Output
```python
{
    "evans_index": 0.38,
    "interpretation": "hydrocephalus",
    "ventricular_volume_ml": 65.2,
    "normal_range_ml": [20, 40]
}
```

---

### 4.5 Skull Fractures (`skull.py`)

#### Detection Strategy
1. **Bone windows**: HU > 400
2. **Edge detection**: Discontinuities in skull contour
3. **Pneumocephalus**: Air (< -500 HU) inside cranial vault

#### Fracture Types
- **Linear**: Simple crack, no displacement
- **Depressed**: Bone fragment pushed inward
- **Basilar**: Skull base (high clinical significance)
- **Comminuted**: Multiple fragments

#### Output
```python
{
    "fracture_detected": True,
    "type": "linear",
    "location": "left parietal",
    "pneumocephalus": False,
    "displacement_mm": 0
}
```

---

## 5. Integration: Sinus + Brain Combined Reports

### Rationale
Many head CTs scan entire head → both sinus and brain pathology visible. Unified report saves time.

### Report Structure
```python
{
    "patient_id": "12345",
    "scan_date": "2025-04-15",
    "sinus": {
        "omc_patency": {"left": "patent", "right": "patent"},
        "sclerosis": "normal (3.2%)",
        "cysts": 0,
        "mucosal_volume_ml": 2.1
    },
    "brain": {
        "hemorrhage": None,
        "midline_shift_mm": 0.3,
        "ventricles": "normal (Evans 0.28)",
        "acute_findings": None
    },
    "skull": {
        "fractures": None,
        "pneumocephalus": False
    }
}
```

### Clinical Workflow
1. Run `calibrate_volume()` once (shared)
2. Run sinus analysis: `measure_omc_patency()`, `compute_sclerosis_zscore()`, etc.
3. Run brain analysis: `detect_hemorrhage()`, `measure_midline_shift()`, etc.
4. Generate unified PDF report

---

## 6. Validation Framework

### Ground Truth Sources
- **Sinus**: Radiologist reports (Orlando Health normal scan)
- **Brain** (future): RSNA ICH dataset, ASPECTS annotated cases

### Test Harness (`tests/`)
- `test_orlando_normal.py`: Sinus validation (current)
- `test_hemorrhage_detection.py`: Brain bleed cases (future)
- `test_midline_shift.py`: Mass effect cases (future)

### Validation Criteria
- ✅ **HU Calibration**: Anchors within tolerance
- ✅ **OMC Patency**: Classification matches radiologist
- ✅ **Sclerosis**: Fraction within expected range
- ✅ **Cysts**: Count matches manual segmentation
- 🔜 **Hemorrhage**: Volume ±10% of ground truth
- 🔜 **Midline Shift**: ±2 mm of manual measurement

---

## 7. Usage Examples

### Sinus Analysis (Current)
```python
from calibration import calibrate_volume
from sinus import measure_omc_patency_coronal, compute_sclerosis_zscore

# Load and calibrate
vol_calibrated, metadata = calibrate_volume(volume_raw, spacing)

# OMC patency
omc_result = measure_omc_patency_coronal(
    vol_calibrated, spacing, z_slice=120,
    threshold_patent=0.12, threshold_obstructed=0.08
)
print(f"Left: {omc_result['left']['status']} ({omc_result['left']['patency_pct']:.1f}%)")

# Sclerosis
sclerosis_pct = compute_sclerosis_zscore(vol_calibrated, spacing)
print(f"Sclerotic fraction: {sclerosis_pct:.1f}%")
```

### Brain Analysis (Future)
```python
from calibration import calibrate_volume
from brain import detect_hemorrhage, measure_midline_shift

# Calibrate once
vol_calibrated, _ = calibrate_volume(volume_raw, spacing)

# Hemorrhage detection
bleeds = detect_hemorrhage(vol_calibrated, spacing, threshold=50)
for bleed in bleeds:
    print(f"{bleed['type']}: {bleed['volume_ml']:.1f} mL at {bleed['location']}")

# Midline shift
shift_mm = measure_midline_shift(vol_calibrated, spacing)
if abs(shift_mm) > 5:
    print(f"WARNING: Midline shift {shift_mm:.1f} mm - urgent evaluation")
```

---

## 8. Future Enhancements

### Sinus Module
- [ ] MONAI 3D U-Net segmentation for automatic sinus boundary detection
- [ ] Longitudinal tracking: Compare multiple scans over time
- [ ] Polyp detection: Distinguish from retention cysts

### Brain Module
- [ ] Implement all 5 submodules (hemorrhage, midline, stroke, ventricles, skull)
- [ ] Machine learning: ResNet for hemorrhage classification
- [ ] Integration with neuronavigation systems

### Integration
- [ ] Unified PDF report generator (sinus + brain)
- [ ] Interactive web viewer (Plotly Dash)
- [ ] PACS integration (DICOM send/receive)

---

## 9. References

### Sinus Methods
- Lund-Mackay scoring: *Rhinology* 1997
- OMC anatomy: Stammberger *Functional Endoscopic Sinus Surgery* (1991)
- Osteitis/sclerosis: Kennedy 2004, *Laryngoscope*

### Brain Methods
- ASPECTS scoring: Barber et al., *Lancet* 2000
- ICH detection: Chilamkurthy et al., *Lancet* 2018
- Evans' index: Evans 1942, *Archives of Neurology*

### HU Calibration
- Air/bone anchors: Standardized in ACR CT accreditation
- Linear correction: Brooks & Di Chiro, *Radiology* 1976

---

## Contact

For technical questions: [GitHub Issues](https://github.com/mtbajdas/sinus-ct-ml-pipeline/issues)
