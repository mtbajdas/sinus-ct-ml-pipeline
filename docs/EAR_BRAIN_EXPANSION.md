# Ear & Brain Analysis with TotalSegmentator

## What's Immediately Available

With TotalSegmentator integration, you can analyze **104 anatomical structures** from any head CT. Here's what's ready for **ear and brain** analysis:

### 🦻 Ear/Temporal Bone Structures

**Available Segmentations:**
- `temporal_bone_left` / `temporal_bone_right` - Complete temporal bone
- `skull` - Includes petrous portion (contains inner ear)

**Potential Applications:**

#### 1. **Temporal Bone Volume & Density**
```python
from src.head_ct_analyzer import HeadCTAnalyzer

analyzer = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='totalsegmentator'
)

# Analyze temporal bones
skull_results = analyzer.analyze_skull_structures()

temporal_left = skull_results['temporal_bone_left']
temporal_right = skull_results['temporal_bone_right']

print(f"Left temporal bone: {temporal_left['volume_ml']:.1f} mL")
print(f"Right temporal bone: {temporal_right['volume_ml']:.1f} mL")
print(f"Mean HU: {temporal_left['mean_hu']:.0f}")
print(f"Asymmetry: {abs(temporal_left['volume_ml'] - temporal_right['volume_ml']):.1f} mL")
```

#### 2. **Mastoid Air Cell Analysis**
The temporal bone contains mastoid air cells - similar to sinuses!

```python
import numpy as np
from src.calibration.hu_calibration import HUCalibration

# Get temporal bone ROI
roi_provider = create_roi_provider('totalsegmentator')
temporal_mask = roi_provider.get_roi_mask(volume, spacing, 'temporal_bone_left')

# Extract temporal bone region
temporal_roi = volume[temporal_mask > 0]

# Measure air cells (similar to sinus analysis)
calibration = HUCalibration(volume, spacing)
air_threshold = calibration.get_adaptive_threshold('air')

air_fraction = (temporal_roi < air_threshold).sum() / temporal_roi.size
bone_hu = np.median(temporal_roi[temporal_roi > 200])  # Bone only

print(f"Mastoid pneumatization: {air_fraction * 100:.1f}%")
print(f"Temporal bone density: {bone_hu:.0f} HU")
```

**Clinical Use Cases:**
- **Mastoiditis screening**: Reduced air fraction, increased soft tissue
- **Chronic otitis**: Air cell opacification patterns
- **Cholesteatoma**: Bone erosion detection (very low HU regions)
- **Asymmetry**: Compare left vs right pneumatization

#### 3. **Petrous Pyramid Evaluation**
```python
# Petrous pyramid is densest part of temporal bone
temporal_roi = volume[temporal_mask > 0]

# Petrous bone should be very dense (>800 HU)
petrous_bone = temporal_roi[temporal_roi > 800]
mean_petrous_hu = petrous_bone.mean()

print(f"Petrous bone density: {mean_petrous_hu:.0f} HU")
print(f"Dense bone volume: {len(petrous_bone) * voxel_volume_mm3 / 1000:.1f} mL")
```

---

### 🧠 Brain Structures

**Available Segmentations:**
- `brain` - Entire brain parenchyma
- `brainstem` - Medulla, pons, midbrain
- `pituitary_gland` - Sella turcica contents

**Potential Applications:**

#### 1. **Brain Volume & Atrophy Tracking**
```python
analyzer = HeadCTAnalyzer(nifti_path, roi_provider_type='totalsegmentator')

# Get brain segmentations
brain_results = analyzer.analyze_skull_structures()

brain = brain_results['brain']
brainstem = brain_results['brainstem']

print(f"Brain volume: {brain['volume_ml']:.0f} mL")
print(f"Brainstem volume: {brainstem['volume_ml']:.1f} mL")
print(f"Brain mean HU: {brain['mean_hu']:.1f}")

# Compare to reference values
# Normal adult brain: ~1200-1400 mL
# Brainstem: ~20-30 mL
```

**Clinical Applications:**
- **Hydrocephalus**: Reduced brain parenchyma volume
- **Atrophy**: Compare to age-matched norms (longitudinal tracking)
- **Mass effect**: Asymmetry or displacement

#### 2. **White Matter vs Gray Matter Density**
```python
# Brain parenchyma HU analysis
brain_mask = roi_provider.get_roi_mask(volume, spacing, 'brain')
brain_roi = volume[brain_mask > 0]

# Gray matter: ~35-45 HU
# White matter: ~25-35 HU
# CSF: ~0-15 HU

gray_matter = brain_roi[(brain_roi > 35) & (brain_roi < 45)]
white_matter = brain_roi[(brain_roi > 25) & (brain_roi < 35)]

print(f"Gray matter: {len(gray_matter) * voxel_volume_mm3 / 1000:.0f} mL ({len(gray_matter)/brain_roi.size*100:.1f}%)")
print(f"White matter: {len(white_matter) * voxel_volume_mm3 / 1000:.0f} mL ({len(white_matter)/brain_roi.size*100:.1f}%)")
```

**Clinical Applications:**
- **Leukoaraiosis**: White matter hypodensity (reduced HU)
- **Edema**: Abnormally low HU in brain parenchyma
- **Hemorrhage**: Abnormally high HU regions

#### 3. **Pituitary Gland Analysis**
```python
pituitary = brain_results['pituitary_gland']

print(f"Pituitary volume: {pituitary['volume_ml']*1000:.0f} mm³")
print(f"Pituitary HU: {pituitary['mean_hu']:.1f}")

# Normal pituitary: 400-600 mm³
# Microadenoma: focal density changes
# Macroadenoma: >10mm diameter, mass effect
```

---

## Quick Start: Comprehensive Head CT Analysis

### Installation
```bash
# Install TotalSegmentator
pip install totalsegmentator

# Optional: CUDA for GPU acceleration (5-10 seconds vs 30-60 seconds CPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Basic Analysis
```python
from src.head_ct_analyzer import HeadCTAnalyzer

# Initialize with TotalSegmentator
analyzer = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='totalsegmentator'
)

# Generate comprehensive report with ALL structures
report = analyzer.generate_comprehensive_report(
    output_path='docs/metrics/full_head_analysis.json'
)

print(f"Analyzed {len(report['structures'])} structures:")
for structure, metrics in report['structures'].items():
    print(f"  {structure}: {metrics['volume_ml']:.1f} mL, {metrics['mean_hu']:.0f} HU")
```

### Command Line
```bash
# Analyze everything in one command
python src/head_ct_analyzer.py \
    --input data/processed/sinus_ct.nii.gz \
    --provider totalsegmentator \
    --output docs/metrics/comprehensive_report.json
```

---

## Advanced Ear Analysis Module

Let's create a dedicated ear analysis module similar to your sinus modules:

```python
# src/ear/temporal_bone_metrics.py

"""
Temporal bone and ear analysis using TotalSegmentator.

Analyzes:
1. Mastoid pneumatization (air cell volume)
2. Temporal bone density
3. Left-right asymmetry
4. Potential pathology detection
"""
from pathlib import Path
from typing import Tuple, Dict

import numpy as np
from src.core.roi_provider import create_roi_provider
from src.calibration.hu_calibration import HUCalibration


def analyze_temporal_bones(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    roi_provider=None,
) -> Dict:
    """
    Comprehensive temporal bone analysis.
    
    Returns dict with:
    - left/right volumes
    - mastoid pneumatization (air fraction)
    - bone density metrics
    - asymmetry score
    """
    if roi_provider is None:
        roi_provider = create_roi_provider('auto')
    
    # Get segmentations
    left_mask = roi_provider.get_roi_mask(volume, spacing, 'temporal_bone_left')
    right_mask = roi_provider.get_roi_mask(volume, spacing, 'temporal_bone_right')
    
    if left_mask is None or right_mask is None:
        return {'error': 'Temporal bones not segmented'}
    
    # Calculate voxel volume
    voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    
    # Calibrate thresholds
    calibration = HUCalibration(volume, spacing)
    air_threshold = calibration.get_adaptive_threshold('air')
    bone_threshold = 200  # Standard bone threshold
    
    results = {}
    
    for side, mask in [('left', left_mask), ('right', right_mask)]:
        roi = volume[mask > 0]
        
        # Volume measurements
        total_volume_ml = roi.size * voxel_volume_mm3 / 1000
        
        # Mastoid pneumatization (air cells)
        air_voxels = (roi < air_threshold).sum()
        air_fraction = air_voxels / roi.size
        air_volume_ml = air_voxels * voxel_volume_mm3 / 1000
        
        # Bone density
        bone_voxels = roi[roi > bone_threshold]
        mean_bone_hu = bone_voxels.mean() if len(bone_voxels) > 0 else 0
        
        # Soft tissue (potential pathology)
        soft_tissue = ((roi > -100) & (roi < bone_threshold)).sum()
        soft_tissue_fraction = soft_tissue / roi.size
        
        results[side] = {
            'total_volume_ml': total_volume_ml,
            'air_volume_ml': air_volume_ml,
            'pneumatization_pct': air_fraction * 100,
            'mean_bone_hu': mean_bone_hu,
            'soft_tissue_pct': soft_tissue_fraction * 100,
            'mean_hu': roi.mean(),
            'std_hu': roi.std(),
        }
    
    # Asymmetry score
    volume_asymmetry = abs(
        results['left']['total_volume_ml'] - results['right']['total_volume_ml']
    )
    pneumatization_asymmetry = abs(
        results['left']['pneumatization_pct'] - results['right']['pneumatization_pct']
    )
    
    results['asymmetry'] = {
        'volume_difference_ml': volume_asymmetry,
        'pneumatization_difference_pct': pneumatization_asymmetry,
    }
    
    return results


def detect_mastoiditis(temporal_results: Dict) -> Dict:
    """
    Screen for potential mastoiditis based on mastoid air cell patterns.
    
    Red flags:
    - Reduced pneumatization (<20% vs normal 40-60%)
    - Increased soft tissue fraction (>20% vs normal <10%)
    - Significant asymmetry (>15% difference)
    """
    findings = {
        'left_concern': False,
        'right_concern': False,
        'asymmetry_concern': False,
        'notes': []
    }
    
    # Check left
    if temporal_results['left']['pneumatization_pct'] < 20:
        findings['left_concern'] = True
        findings['notes'].append(
            f"Left mastoid: Reduced pneumatization ({temporal_results['left']['pneumatization_pct']:.1f}%)"
        )
    
    if temporal_results['left']['soft_tissue_pct'] > 20:
        findings['left_concern'] = True
        findings['notes'].append(
            f"Left mastoid: Increased soft tissue ({temporal_results['left']['soft_tissue_pct']:.1f}%)"
        )
    
    # Check right
    if temporal_results['right']['pneumatization_pct'] < 20:
        findings['right_concern'] = True
        findings['notes'].append(
            f"Right mastoid: Reduced pneumatization ({temporal_results['right']['pneumatization_pct']:.1f}%)"
        )
    
    if temporal_results['right']['soft_tissue_pct'] > 20:
        findings['right_concern'] = True
        findings['notes'].append(
            f"Right mastoid: Increased soft tissue ({temporal_results['right']['soft_tissue_pct']:.1f}%)"
        )
    
    # Check asymmetry
    if temporal_results['asymmetry']['pneumatization_difference_pct'] > 15:
        findings['asymmetry_concern'] = True
        findings['notes'].append(
            f"Asymmetric pneumatization: {temporal_results['asymmetry']['pneumatization_difference_pct']:.1f}% difference"
        )
    
    return findings
```

---

## Advanced Brain Analysis Module

```python
# src/brain/brain_metrics.py

"""
Brain parenchyma analysis from head CT.

Analyzes:
1. Total brain volume
2. White/gray matter distribution
3. Ventricular size estimation
4. Density abnormalities
"""
from typing import Tuple, Dict
import numpy as np
from scipy import ndimage
from src.core.roi_provider import create_roi_provider


def analyze_brain(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    roi_provider=None,
) -> Dict:
    """Comprehensive brain analysis."""
    if roi_provider is None:
        roi_provider = create_roi_provider('auto')
    
    # Get segmentations
    brain_mask = roi_provider.get_roi_mask(volume, spacing, 'brain')
    brainstem_mask = roi_provider.get_roi_mask(volume, spacing, 'brainstem')
    
    if brain_mask is None:
        return {'error': 'Brain not segmented'}
    
    voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    
    # Total brain analysis
    brain_roi = volume[brain_mask > 0]
    total_volume_ml = brain_roi.size * voxel_volume_mm3 / 1000
    
    # Tissue classification by HU
    csf = ((brain_roi > 0) & (brain_roi < 15)).sum()
    white_matter = ((brain_roi > 25) & (brain_roi < 35)).sum()
    gray_matter = ((brain_roi > 35) & (brain_roi < 45)).sum()
    
    csf_volume_ml = csf * voxel_volume_mm3 / 1000
    white_volume_ml = white_matter * voxel_volume_mm3 / 1000
    gray_volume_ml = gray_matter * voxel_volume_mm3 / 1000
    
    results = {
        'brain': {
            'total_volume_ml': total_volume_ml,
            'mean_hu': brain_roi.mean(),
            'std_hu': brain_roi.std(),
            'csf_volume_ml': csf_volume_ml,
            'white_matter_volume_ml': white_volume_ml,
            'gray_matter_volume_ml': gray_volume_ml,
            'csf_fraction_pct': csf / brain_roi.size * 100,
            'white_matter_fraction_pct': white_matter / brain_roi.size * 100,
            'gray_matter_fraction_pct': gray_matter / brain_roi.size * 100,
        }
    }
    
    # Brainstem analysis
    if brainstem_mask is not None:
        brainstem_roi = volume[brainstem_mask > 0]
        results['brainstem'] = {
            'volume_ml': brainstem_roi.size * voxel_volume_mm3 / 1000,
            'mean_hu': brainstem_roi.mean(),
        }
    
    return results


def detect_brain_abnormalities(brain_results: Dict) -> Dict:
    """
    Screen for potential brain abnormalities.
    
    Reference values (adult):
    - Total brain: 1200-1400 mL
    - White matter: ~40% of brain
    - Gray matter: ~40% of brain
    - CSF: ~10-15% of brain
    - Mean HU: ~30-35
    """
    findings = {
        'atrophy_concern': False,
        'hydrocephalus_concern': False,
        'density_concern': False,
        'notes': []
    }
    
    brain = brain_results['brain']
    
    # Volume assessment
    if brain['total_volume_ml'] < 1100:
        findings['atrophy_concern'] = True
        findings['notes'].append(
            f"Reduced brain volume: {brain['total_volume_ml']:.0f} mL (normal: 1200-1400 mL)"
        )
    
    # CSF assessment (surrogate for ventricular size)
    if brain['csf_fraction_pct'] > 20:
        findings['hydrocephalus_concern'] = True
        findings['notes'].append(
            f"Increased CSF fraction: {brain['csf_fraction_pct']:.1f}% (normal: 10-15%)"
        )
    
    # Density assessment
    if brain['mean_hu'] < 28:
        findings['density_concern'] = True
        findings['notes'].append(
            f"Reduced brain density: {brain['mean_hu']:.1f} HU (normal: 30-35 HU). Possible edema."
        )
    
    return findings
```

---

## Clinical Scenarios

### Scenario 1: Sinus CT with Incidental Mastoiditis
```python
from src.ear.temporal_bone_metrics import analyze_temporal_bones, detect_mastoiditis

# Run standard sinus analysis
sinus_results = run_sinus_analysis(nifti_path)

# Add ear analysis
temporal_results = analyze_temporal_bones(volume, spacing)
mastoiditis_screen = detect_mastoiditis(temporal_results)

if mastoiditis_screen['left_concern'] or mastoiditis_screen['right_concern']:
    print("⚠️ INCIDENTAL FINDING:")
    for note in mastoiditis_screen['notes']:
        print(f"  - {note}")
```

### Scenario 2: Comprehensive Head CT Review
```python
from src.head_ct_analyzer import HeadCTAnalyzer

analyzer = HeadCTAnalyzer(nifti_path, roi_provider_type='totalsegmentator')

# Analyze ALL regions
sinus_report = analyzer.analyze_all_sinuses()
skull_report = analyzer.analyze_skull_structures()

# Custom ear analysis
temporal_results = analyze_temporal_bones(analyzer.volume, analyzer.spacing, analyzer.roi_provider)

# Custom brain analysis  
brain_results = analyze_brain(analyzer.volume, analyzer.spacing, analyzer.roi_provider)

# Generate comprehensive report
comprehensive = {
    'sinuses': sinus_report,
    'skull': skull_report,
    'temporal_bones': temporal_results,
    'brain': brain_results,
}

with open('comprehensive_head_analysis.json', 'w') as f:
    json.dump(comprehensive, f, indent=2)
```

---

## Performance & Limitations

### TotalSegmentator Performance
- **CPU**: 30-60 seconds for full head segmentation
- **GPU**: 5-10 seconds (CUDA required)
- **Memory**: ~4GB RAM for typical head CT

### Current Limitations
1. **Inner ear structures**: Not directly segmented (contained within temporal bone)
   - Can't automatically segment: cochlea, semicircular canals, ossicles
   - Would need specialized model (e.g., custom training on temporal bone CTs)

2. **Brain substructures**: Limited granularity
   - TotalSegmentator provides: whole brain, brainstem, pituitary
   - Doesn't segment: thalamus, hippocampus, ventricles individually
   - Would need specialized neuroimaging model (e.g., FreeSurfer, FSL)

3. **CT resolution**: Sinus CT may not extend to full brain
   - Your scans may end at mid-brain level
   - Check `volume.shape[0]` and slice range

### Workarounds
- **Inner ear**: Analyze temporal bone subregions manually
- **Ventricles**: Use HU-based segmentation (0-15 HU) within brain mask
- **Custom structures**: Train your own model on specific anatomy

---

## Next Steps

### Immediate (Today)
```bash
# 1. Install TotalSegmentator
pip install totalsegmentator

# 2. Run comprehensive analysis
python src/head_ct_analyzer.py \
    --input data/processed/sinus_ct.nii.gz \
    --provider totalsegmentator \
    --output docs/metrics/full_scan_analysis.json

# 3. Check what structures were found
python -c "
from src.core.roi_provider import create_roi_provider
import nibabel as nib

nii = nib.load('data/processed/sinus_ct.nii.gz')
volume = nii.get_fdata()
spacing = nii.header.get_zooms()

provider = create_roi_provider('totalsegmentator')
provider.get_roi_mask(volume, spacing, 'brain')  # Trigger segmentation

print('Available structures:')
for struct in provider.get_available_structures():
    print(f'  - {struct}')
"
```

### Short Term (This Week)
1. Create `src/ear/` directory with temporal bone metrics
2. Create `src/brain/` directory with brain metrics
3. Add ear/brain to `HeadCTAnalyzer.generate_comprehensive_report()`
4. Test on your actual CT data

### Medium Term (Next 2 Weeks)
1. **Literature comparison**: Find normal ranges for temporal bone pneumatization, brain volumes
2. **Visualization**: Add temporal bone + brain overlays to 3D viewer
3. **Validation**: Compare TotalSegmentator vs manual measurements
4. **Documentation**: Clinical interpretation guide for ear/brain findings

---

## Summary

**You can immediately analyze:**
- ✅ Temporal bones (volume, density, asymmetry)
- ✅ Mastoid pneumatization (air cell quantification)
- ✅ Brain parenchyma (volume, HU distribution)
- ✅ Brainstem (volume, density)
- ✅ Pituitary gland (volume, density)

**With ~10 lines of code** using your new architecture! 🚀
