# Sinus CT Analysis - Quick Start

## 📋 Complete Workflow

### Step 1: Convert DICOM to NIfTI
```bash
python src/pipeline.py \
  --dicom-dir data/raw/my_scan \
  --output-nifti data/processed/sinus_ct.nii.gz
```
**Output:** Calibrated NIfTI volume + metadata JSON

### Step 2: Run Sinus Analysis
```bash
python src/clinical_investigation.py \
  --nifti data/processed/sinus_ct.nii.gz \
  --output docs/metrics/clinical_analysis_report.json
```
**Measures:**
- ✓ OMC patency (left/right drainage corridors)
- ✓ Sclerotic bone fraction (chronic inflammation marker)
- ✓ Retention cysts (count + locations)
- ✓ Lund-Mackay staging scores
- ✓ Volumetric analysis (air vs tissue)

### Step 3: Generate PDF Report
```bash
python src/generate_report.py
```
**Output:** `docs/report/comprehensive_report.pdf` - Comprehensive, data-driven report with reference ranges

### Step 4: 3D Visualization (Optional)
```bash
python src/visualization/visualize_3d.py \
  --nifti data/processed/sinus_ct.nii.gz \
  --iso -300 \
  --downsample 2
```
**Output:** Interactive HTML with 3D mesh

---

## 🧪 Validation

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

## 📊 Key Metrics

| Metric | What It Measures | Normal Range |
|--------|------------------|--------------|
| **OMC Patency** | Air fraction in drainage corridors | > 12% (Patent) |
| **Sclerotic Fraction** | Bone density elevation (chronic inflammation) | < 5% |
| **Retention Cysts** | Fluid-filled lesions | 0-2 cysts |
| **Lund-Mackay** | Semi-quantitative staging | 0-4 (mild) |

---

## 🐍 Python API

```python
from calibration import calibrate_volume
from sinus import measure_omc_patency_coronal, compute_sclerosis_zscore

# Load and calibrate
img = nib.load('data/processed/sinus_ct.nii.gz')
volume = img.get_fdata()
spacing = img.header.get_zooms()[:3]
vol_calibrated, metadata = calibrate_volume(volume, spacing)

# Measure OMC patency
omc = measure_omc_patency_coronal(vol_calibrated, spacing, z_slice=120)
print(f"Left: {omc['left']['status']} ({omc['left']['patency_pct']:.1f}%)")

# Compute sclerosis
sclerosis_pct = compute_sclerosis_zscore(vol_calibrated, spacing)
print(f"Sclerosis: {sclerosis_pct:.1f}%")
```

---

## 📁 File Structure

```
src/sinus/                    # Core sinus analysis module
├── anatomical.py            # OMC patency, wall shell, reference bone
└── pathology.py             # Sclerosis, retention cysts

src/
├── pipeline.py              # DICOM → NIfTI conversion
├── clinical_investigation.py # Full sinus analysis
└── generate_report.py      # Unified PDF report generator

tests/
└── test_orlando_normal.py   # Ground truth validation

docs/
├── report/comprehensive_report.pdf       # Generated report
├── metrics/clinical_analysis_report.json # Analysis results
├── SINUS_ANALYSIS_GUIDE.md              # Detailed guide
└── METHODS.md                            # Technical documentation
```

---

## 🔍 What Makes This Analysis Objective?

### Unified Report (`generate_report.py`)
✅ **Data-driven:** Presents measurements as-is  
✅ **Reference ranges:** From published literature  
✅ **No bias:** No clinical recommendations or interpretations  
✅ **Methodology:** Complete technical transparency  
✅ **Validation:** Ground truth testing documented  

### vs. Old ENT Report (`generate_ent_report_pdf.py`)
❌ Included clinical interpretations  
❌ Made treatment recommendations  
❌ Biased language ("severe", "surgical indication")  

---

## 📖 Documentation

- **[SINUS_ANALYSIS_GUIDE.md](docs/SINUS_ANALYSIS_GUIDE.md)** - Complete usage guide
- **[METHODS.md](METHODS.md)** - Technical methodology and algorithms
- **[REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md)** - Architecture overview

---

## ⚡ One-Liner for Quick Analysis

```bash
# Process scan → Analyze → Generate report
python src/pipeline.py --dicom-dir data/raw/scan ; \
python src/clinical_investigation.py ; \
python src/generate_report.py
```

**Result:** Professional PDF report in `docs/report/comprehensive_report.pdf`

---

## 🎯 Next Steps

1. **Run validation test** to verify your setup:
   ```bash
   python tests/test_orlando_normal.py
   ```

2. **Process your own scan:**
   ```bash
  python src/pipeline.py --dicom-dir data/raw/your_scan
  python src/clinical_investigation.py
  python src/generate_report.py
   ```

3. **View the guide** for detailed API usage:
   ```bash
   cat docs/SINUS_ANALYSIS_GUIDE.md
   ```

---

**Bottom Line:** Use `generate_report.py` for a single comprehensive Head CT analysis report. All measurements validated against ground truth with reference ranges from literature.
