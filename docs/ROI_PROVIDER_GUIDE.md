# ROI Provider Architecture

## Overview

The ROI (Region of Interest) provider system enables **plug-and-play switching** between different anatomical structure localization methods. This architecture centralizes ROI placement logic and makes it easy to add new methods without modifying analysis code.

## Quick Start

### Using Manual ROI Provider (Current)
```python
from src.head_ct_analyzer import HeadCTAnalyzer

# Analyze using percentage-based manual ROIs
analyzer = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='manual'
)

results = analyzer.analyze_deep_sinuses()
```

### Using TotalSegmentator (Automatic Segmentation)
```bash
# Install TotalSegmentator
pip install totalsegmentator

# Use it automatically
python src/head_ct_analyzer.py --input data/processed/sinus_ct.nii.gz --provider totalsegmentator
```

```python
# Or in code
analyzer = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='totalsegmentator'
)

# Analyze ALL available structures (104 with TotalSegmentator!)
report = analyzer.generate_comprehensive_report()
```

### Auto Mode (Tries TotalSegmentator, Falls Back to Manual)
```python
analyzer = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='auto'  # Default
)
```

## Architecture

### Core Components

```
src/
├── core/
│   └── roi_provider.py          # Abstract interface + implementations
├── head_ct_analyzer.py          # High-level orchestrator
├── sinus/
│   └── deep_sinus.py            # Uses ROI providers for analysis
└── oropharynx/
    └── tonsil_metrics.py        # Can be updated to use providers
```

### ROI Provider Interface

All providers implement this interface:

```python
class ROIProvider(ABC):
    @abstractmethod
    def get_roi_mask(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[np.ndarray]:
        """Return binary mask for structure."""
        pass
    
    @abstractmethod
    def get_roi_bounds(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[Tuple[slice, slice, slice]]:
        """Return bounding box for structure."""
        pass
    
    @abstractmethod
    def get_available_structures(self) -> list[str]:
        """List all structures this provider can segment."""
        pass
```

## Available Providers

### 1. ManualROIProvider (Current Implementation)
- **Speed**: Instant (no computation)
- **Structures**: 7 (sphenoid, posterior_ethmoid, skull_base, etc.)
- **Accuracy**: Good for sinus CT, requires tuning for other scan types
- **Requirements**: None

### 2. TotalSegmentatorROIProvider (Deep Learning)
- **Speed**: 30-60 seconds on CPU, 5-10 seconds on GPU
- **Structures**: 104 (all head/neck anatomy)
- **Accuracy**: State-of-the-art (trained on 1100+ CTs)
- **Requirements**: `pip install totalsegmentator`

Supported structures include:
- **Sinuses**: Sphenoid, maxillary (L/R), frontal (L/R), ethmoid (L/R)
- **Skull**: Skull, mandible, maxilla
- **Bones**: Temporal bones (L/R), zygomatic (L/R)
- **Brain**: Brain, brainstem, pituitary gland
- **Vessels**: Carotid arteries (L/R), internal jugular veins (L/R)
- **Airway**: Trachea, pharynx
- **And 80+ more structures...**

## Usage Examples

### Example 1: Compare Manual vs TotalSegmentator

```python
from src.head_ct_analyzer import HeadCTAnalyzer

nifti_path = 'data/processed/sinus_ct.nii.gz'

# Manual approach
analyzer_manual = HeadCTAnalyzer(nifti_path, roi_provider_type='manual')
manual_results = analyzer_manual.analyze_deep_sinuses()

# TotalSegmentator approach
analyzer_auto = HeadCTAnalyzer(nifti_path, roi_provider_type='totalsegmentator')
auto_results = analyzer_auto.analyze_deep_sinuses()

# Compare
print(f"Manual sphenoid: {manual_results['sphenoid']['sphenoid_volume_ml']:.1f} mL")
print(f"TotalSeg sphenoid: {auto_results['sphenoid']['sphenoid_volume_ml']:.1f} mL")
```

### Example 2: Analyze All Sinuses

```python
analyzer = HeadCTAnalyzer(nifti_path, roi_provider_type='totalsegmentator')

# Get all sinus structures
sinus_results = analyzer.analyze_all_sinuses()

for structure, metrics in sinus_results.items():
    print(f"{structure}: {metrics['volume_ml']:.1f} mL, {metrics['air_fraction']*100:.1f}% air")
```

### Example 3: Analyze Skull and Temporal Bones

```python
analyzer = HeadCTAnalyzer(nifti_path, roi_provider_type='totalsegmentator')

skull_results = analyzer.analyze_skull_structures()

for structure, metrics in skull_results.items():
    print(f"{structure}: {metrics['volume_ml']:.1f} mL, {metrics['mean_hu']:.0f} HU")
```

### Example 4: Update Existing Code to Use ROI Providers

**Before:**
```python
def measure_sphenoid_volume(volume, spacing):
    # Hard-coded ROI bounds
    z_start = int(z * 0.30)
    z_end = int(z * 0.50)
    roi = volume[z_start:z_end, ...]
    # ... analysis
```

**After:**
```python
def measure_sphenoid_volume(volume, spacing, roi_provider=None):
    if roi_provider is None:
        roi_provider = ManualROIProvider()
    
    # Get ROI from provider
    roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'sphenoid')
    roi = volume[roi_bounds]
    # ... analysis
```

## Adding New ROI Providers

### Example: Atlas-Based Provider

```python
class AtlasROIProvider(ROIProvider):
    """ROI provider using atlas registration."""
    
    def __init__(self, atlas_path: Path):
        self.atlas = load_atlas(atlas_path)
        self._cached_registration = None
    
    def get_roi_mask(self, volume, spacing, structure_name):
        # Register atlas to patient scan
        if self._cached_registration is None:
            self._cached_registration = register(self.atlas, volume)
        
        # Warp atlas label to patient space
        atlas_label = self.atlas.labels[structure_name]
        patient_mask = self._cached_registration.apply(atlas_label)
        return patient_mask
    
    def get_available_structures(self):
        return list(self.atlas.labels.keys())
    
    @property
    def name(self):
        return "AtlasROIProvider"
```

Then use it:
```python
from core.roi_provider import AtlasROIProvider

atlas_provider = AtlasROIProvider(atlas_path='atlases/head_ct_atlas.nii.gz')

analyzer = HeadCTAnalyzer(
    nifti_path='patient.nii.gz',
    roi_provider=atlas_provider
)
```

## Command-Line Interface

```bash
# Manual ROI placement (fast, current method)
python src/head_ct_analyzer.py \
    --input data/processed/sinus_ct.nii.gz \
    --provider manual \
    --output results.json

# TotalSegmentator (automatic, 104 structures)
python src/head_ct_analyzer.py \
    --input data/processed/sinus_ct.nii.gz \
    --provider totalsegmentator \
    --output results.json

# Auto (tries TotalSegmentator, falls back to manual)
python src/head_ct_analyzer.py \
    --input data/processed/sinus_ct.nii.gz \
    --provider auto \
    --output results.json
```

## Integration with Existing Pipeline

The current `sinus_analysis.py` can be updated to use ROI providers:

```python
# In sinus_analysis.py
from core.roi_provider import create_roi_provider

# Initialize provider (uses auto mode by default)
roi_provider = create_roi_provider('auto')

# Pass to deep sinus functions
sphenoid_metrics = measure_sphenoid_volume(
    volume,
    spacing,
    roi_provider=roi_provider  # New parameter
)
```

## Performance Comparison

| Provider | Speed | Structures | Accuracy | GPU Required |
|----------|-------|------------|----------|--------------|
| Manual | Instant | 7 | Good for sinuses | No |
| TotalSegmentator | 30-60s (CPU) | 104 | State-of-the-art | Optional |
| Atlas (future) | 2-5 min | Unlimited | Excellent | No |

## Future Extensions

### 1. Landmark-Based Provider
```python
class LandmarkROIProvider(ROIProvider):
    """Place ROIs relative to detected anatomical landmarks."""
    
    def __init__(self, landmark_detector):
        self.detector = landmark_detector
    
    def get_roi_bounds(self, volume, spacing, structure_name):
        # Detect landmarks (e.g., sella turcica, nasion)
        landmarks = self.detector.detect(volume)
        
        # Place ROI relative to landmarks
        if structure_name == 'sphenoid':
            sella = landmarks['sella_turcica']
            return self._roi_around_point(sella, size=(30, 40, 20))
```

### 2. Hybrid Provider
```python
class HybridROIProvider(ROIProvider):
    """Use different providers for different structures."""
    
    def __init__(self):
        self.totalseg = TotalSegmentatorROIProvider()
        self.manual = ManualROIProvider()
    
    def get_roi_mask(self, volume, spacing, structure_name):
        # Use TotalSegmentator for major structures
        if structure_name in ['skull', 'mandible', 'brain']:
            return self.totalseg.get_roi_mask(volume, spacing, structure_name)
        
        # Use manual for specialized sinus analysis
        return self.manual.get_roi_mask(volume, spacing, structure_name)
```

## Troubleshooting

### TotalSegmentator Not Found
```
ImportError: totalsegmentator not found
```

**Solution**: Install TotalSegmentator
```bash
pip install totalsegmentator
```

### TotalSegmentator Slow
Running on CPU takes 30-60 seconds.

**Solution**: Use GPU
```python
from core.roi_provider import TotalSegmentatorROIProvider

provider = TotalSegmentatorROIProvider(device='cuda')  # Use GPU
```

### Structure Not Available
```
Warning: structure 'xyz' not available
```

**Solution**: Check available structures
```python
provider = create_roi_provider('auto')
print(provider.get_available_structures())
```

## References

- **TotalSegmentator**: Wasserthal et al. (2023) "TotalSegmentator: robust segmentation of 104 anatomical structures in CT images"
- **ANTsPy**: Avants et al. (2011) "A reproducible evaluation of ANTs similarity metric performance in brain image registration"
- **MONAI**: Project MONAI (2020) "Medical Open Network for AI"
