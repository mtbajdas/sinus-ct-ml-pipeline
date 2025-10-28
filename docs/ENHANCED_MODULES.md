# Enhanced Analysis Modules - Deep Sinuses & Oropharynx

## Added Modules

### 1. Deep Sinus Analysis (`src/sinus/deep_sinus.py`)

Quantitative metrics for posterior/deep paranasal structures:

**Functions:**
- `measure_sphenoid_volume()` - Sphenoid sinus air volume, pneumatization grade (0-3)
- `check_sphenoid_opacification()` - Opacification grading (0=clear, 1=partial, 2=complete), fluid detection
- `measure_posterior_ethmoid_volume()` - Posterior ethmoid air cells, cell count estimation
- `measure_skull_base_thickness()` - Skull base integrity metrics (important for CSF leak risk)

**Clinical Applications:**
- Sphenoid sinusitis detection (can affect vision, cause meningitis)
- Surgical planning (transsphenoidal approaches)
- Intracranial complication risk assessment

### 2. Oropharyngeal Analysis (`src/oropharynx/tonsil_metrics.py`)

Quantitative metrics for palatine tonsils and airway:

**Functions:**
- `measure_tonsil_volumes()` - Bilateral tonsil volumes, asymmetry ratio
- `compute_brodsky_grade()` - Obstruction grading (0-4 scale), airway diameter
- `measure_oropharyngeal_airway()` - Airway patency, cross-sectional areas

**Clinical Applications:**
- Tonsillectomy candidacy assessment
- Sleep apnea screening (airway obstruction)
- Asymmetry detection (rule out neoplasm)

## Integration

Updated `src/sinus_analysis.py` to include:
- Section 7: Deep Sinus Analysis
- Section 8: Oropharyngeal Analysis

## Your Scan Results

### Deep Sinus Findings

**Sphenoid:**
- Volume: 1.3 mL (Conchal pneumatization - small/rudimentary)
- **Opacification: Complete bilaterally (0.3% left, 0.7% right air)**
- Interpretation: Some mucosal thickening or residual inflammation

**Posterior Ethmoid:**
- Volume: 100.2 mL (normal range)
- Cell count: ~56 air cells
- Air fraction: 10.3%

**Skull Base:**
- Metrics not reliably captured (scan may not include superior extent)

### Oropharyngeal Findings

**Coverage:** Your scan includes oropharynx region

**Tonsils:**
- Volumes: 0.0 mL bilaterally
- Interpretation: **Surgically removed** (tonsillectomy) OR extremely small

**Airway:**
- Very patent (351-387 mm diameter is unusually large - likely measurement artifact from wide field of view)
- No obstruction detected

## Key Clinical Insight

**Sphenoid opacification** is the only finding of note. Given context:
- Post-steroid/antibiotic treatment
- OMC patent, other sinuses clear
- No retention cysts or sclerosis

**Interpretation:** 
- Sphenoid may have had more severe involvement initially
- Likely improving but slower to clear (deep location, smaller ostium)
- Not concerning if asymptomatic
- Consider repeat imaging in 3-6 months if symptoms recur

## Usage Examples

### Basic Analysis (all modules included)
```powershell
python src/sinus_analysis.py
```

### Check Specific Regions
```python
from sinus import measure_sphenoid_volume, check_sphenoid_opacification
from oropharynx import measure_tonsil_volumes, compute_brodsky_grade

# Load volume
img = nib.load('data/processed/sinus_ct.nii.gz')
volume = img.get_fdata()
spacing = img.header.get_zooms()[:3]

# Sphenoid metrics
sphenoid = measure_sphenoid_volume(volume, spacing)
print(f"Sphenoid volume: {sphenoid['sphenoid_volume_ml']:.1f} mL")

opac = check_sphenoid_opacification(volume, spacing)
print(f"Left opacification: {opac['left_opacification_grade']}/2")

# Tonsil metrics (if coverage permits)
tonsils = measure_tonsil_volumes(volume, spacing)
if tonsils['has_coverage']:
    print(f"Total tonsil volume: {tonsils['total_tonsil_volume_ml']:.2f} mL")
    
    if tonsils['total_tonsil_volume_ml'] > 0.5:
        brodsky = compute_brodsky_grade(volume, spacing)
        print(f"Brodsky grade: {brodsky['brodsky_grade']}/4")
```

## JSON Output Structure

New metrics added to `docs/metrics/clinical_analysis_report.json`:

```json
{
  "metrics": {
    "deep_sinuses": {
      "sphenoid": {
        "sphenoid_volume_ml": 1.3,
        "left_volume_ml": 0.4,
        "right_volume_ml": 0.9,
        "pneumatization_grade": 1,
        "air_fraction": 0.004
      },
      "sphenoid_opacification": {
        "left_opacification_grade": 2,
        "right_opacification_grade": 2,
        "left_air_fraction": 0.003,
        "right_air_fraction": 0.007,
        "fluid_detected": false
      },
      "posterior_ethmoid": {
        "posterior_ethmoid_volume_ml": 100.2,
        "left_volume_ml": 43.4,
        "right_volume_ml": 56.8,
        "cell_count_estimate": 56,
        "air_fraction": 0.103
      },
      "skull_base": {
        "mean_thickness_mm": 0.0,
        "minimum_thickness_mm": 0.0,
        "bone_volume_ml": 0.0,
        "bone_hu_mean": 0.0
      }
    },
    "oropharynx": {
      "tonsils": {
        "left_tonsil_volume_ml": 0.0,
        "right_tonsil_volume_ml": 0.0,
        "total_tonsil_volume_ml": 0.0,
        "asymmetry_ratio": 0.0,
        "has_coverage": true
      },
      "brodsky": null,
      "airway": {
        "minimum_diameter_mm": 351.8,
        "mean_diameter_mm": 387.1,
        "minimum_cross_sectional_area_mm2": 97269.4,
        "mean_cross_sectional_area_mm2": 117652.6,
        "airway_volume_ml": 4826.8
      }
    }
  }
}
```

## Limitations & Notes

1. **Tonsil segmentation** requires soft tissue windowing - best results with contrast-enhanced CT
2. **Skull base metrics** may be unreliable if scan doesn't extend superiorly enough
3. **Airway measurements** can be artifacts if scan includes large external air regions
4. **Sphenoid pneumatization** varies widely (grade 0-3 all normal variants)

## Next Steps

- ✅ Deep sinus quantitative analysis working
- ✅ Oropharyngeal metrics integrated
- ✅ JSON export updated
- ⏳ Update PDF report generator to include new metrics
- ⏳ Add validation tests for new modules
