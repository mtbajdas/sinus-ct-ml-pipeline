"""
Deep sinus analysis - Sphenoid and posterior structures.

Provides quantitative metrics for deep paranasal sinuses:
- Sphenoid sinus volume and drainage
- Posterior ethmoid air cells
- Skull base integrity
"""
from __future__ import annotations

from typing import Dict, Tuple, Optional
import numpy as np
from scipy import ndimage

# Use absolute import to avoid relative import issues
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.roi_provider import ROIProvider, ManualROIProvider


def measure_sphenoid_volume(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    air_threshold: float = -400.0,
    roi_provider: Optional[ROIProvider] = None,
) -> Dict[str, float]:
    """
    Measure sphenoid sinus volume and characteristics.
    
    Sphenoid sinus location:
    - Most posterior sinus
    - Behind posterior ethmoid, anterior to pituitary
    - Typically at inferior 20-40% of sinus CT in z-axis
    - Central in x-axis (straddling midline)
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        air_threshold: HU threshold for air
        roi_provider: Optional ROI provider (uses manual if None)
    
    Returns:
        Dict with:
        - sphenoid_volume_ml: Total sphenoid air volume
        - left_volume_ml: Left sphenoid volume
        - right_volume_ml: Right sphenoid volume
        - pneumatization_grade: 0-3 (absent, conchal, presellar, sellar)
        - air_fraction: Fraction of sphenoid region that is air
    """
    if roi_provider is None:
        roi_provider = ManualROIProvider(air_threshold=air_threshold)
    
    z, y, x = volume.shape
    voxel_volume_mm3 = np.prod(spacing)
    
    # Get ROI bounds from provider
    roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'sphenoid')
    if roi_bounds is None:
        # Fallback to manual if provider doesn't support sphenoid
        roi_provider = ManualROIProvider(air_threshold=air_threshold)
        roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'sphenoid')
    
    sphenoid_roi = volume[roi_bounds]
    
    # Segment air in ROI
    air_mask = sphenoid_roi < air_threshold
    
    # Morphological opening to clean noise
    air_mask = ndimage.binary_opening(air_mask, structure=np.ones((3, 3, 3)))
    
    # Total sphenoid volume
    total_air_voxels = air_mask.sum()
    total_volume_ml = total_air_voxels * voxel_volume_mm3 / 1000
    
    # Split left/right by midline
    roi_midline = air_mask.shape[2] // 2
    left_air = air_mask[:, :, :roi_midline].sum()
    right_air = air_mask[:, :, roi_midline:].sum()
    
    left_vol_ml = left_air * voxel_volume_mm3 / 1000
    right_vol_ml = right_air * voxel_volume_mm3 / 1000
    
    # Pneumatization grade (based on volume)
    # 0: Absent (<0.5 mL)
    # 1: Conchal (0.5-2 mL) - rudimentary
    # 2: Presellar (2-6 mL) - moderate
    # 3: Sellar (>6 mL) - extensive, extends to sella
    if total_volume_ml < 0.5:
        pneumatization_grade = 0
    elif total_volume_ml < 2.0:
        pneumatization_grade = 1
    elif total_volume_ml < 6.0:
        pneumatization_grade = 2
    else:
        pneumatization_grade = 3
    
    # Air fraction in ROI
    air_fraction = total_air_voxels / sphenoid_roi.size if sphenoid_roi.size > 0 else 0.0
    
    return {
        'sphenoid_volume_ml': float(total_volume_ml),
        'left_volume_ml': float(left_vol_ml),
        'right_volume_ml': float(right_vol_ml),
        'pneumatization_grade': int(pneumatization_grade),
        'air_fraction': float(air_fraction),
    }


def measure_posterior_ethmoid_volume(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    air_threshold: float = -400.0,
    roi_provider: Optional[ROIProvider] = None,
) -> Dict[str, float]:
    """
    Measure posterior ethmoid air cell volumes.
    
    Posterior ethmoids:
    - Between anterior ethmoids (front) and sphenoid (back)
    - Drain via sphenoethmoidal recess
    - Typically at mid-depth in z-axis, central in x-axis
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        air_threshold: HU threshold for air
        roi_provider: Optional ROI provider (uses manual if None)
    
    Returns:
        Dict with:
        - posterior_ethmoid_volume_ml: Total volume
        - left_volume_ml: Left side volume
        - right_volume_ml: Right side volume
        - cell_count_estimate: Approximate number of air cells
        - air_fraction: Air fraction in posterior ethmoid region
    """
    if roi_provider is None:
        roi_provider = ManualROIProvider(air_threshold=air_threshold)
    
    z, y, x = volume.shape
    voxel_volume_mm3 = np.prod(spacing)
    
    # Get ROI bounds - try provider first, fallback to manual
    roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'posterior_ethmoid')
    if roi_bounds is None:
        roi_provider = ManualROIProvider(air_threshold=air_threshold)
        roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'posterior_ethmoid')
    
    # For posterior ethmoid, we need left/right separation
    # If provider gives us separate masks, use them; otherwise split manually
    z_slice, y_slice, x_slice = roi_bounds
    x_center = x // 2
    x_margin = int(x * 0.10)
    
    # Left posterior ethmoid (just left of midline)
    left_roi = volume[z_slice, y_slice, x_center-x_margin-10:x_center-10]
    left_air = (left_roi < air_threshold)
    left_air = ndimage.binary_opening(left_air, structure=np.ones((2, 2, 2)))
    left_vol_ml = left_air.sum() * voxel_volume_mm3 / 1000
    
    # Right posterior ethmoid (just right of midline)
    right_roi = volume[z_slice, y_slice, x_center+10:x_center+x_margin+10]
    right_air = (right_roi < air_threshold)
    right_air = ndimage.binary_opening(right_air, structure=np.ones((2, 2, 2)))
    right_vol_ml = right_air.sum() * voxel_volume_mm3 / 1000
    
    # Estimate cell count (label connected components)
    left_labeled, n_left = ndimage.label(left_air)
    right_labeled, n_right = ndimage.label(right_air)
    cell_count_estimate = n_left + n_right
    
    total_volume_ml = left_vol_ml + right_vol_ml
    
    # Air fraction
    total_roi_size = left_roi.size + right_roi.size
    total_air_voxels = left_air.sum() + right_air.sum()
    air_fraction = total_air_voxels / total_roi_size if total_roi_size > 0 else 0.0
    
    return {
        'posterior_ethmoid_volume_ml': float(total_volume_ml),
        'left_volume_ml': float(left_vol_ml),
        'right_volume_ml': float(right_vol_ml),
        'cell_count_estimate': int(cell_count_estimate),
        'air_fraction': float(air_fraction),
    }


def check_sphenoid_opacification(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    air_threshold: float = -400.0,
    roi_provider: Optional[ROIProvider] = None,
) -> Dict[str, object]:
    """
    Check sphenoid sinus for opacification/fluid.
    
    Opacification indicators:
    - Low air fraction (<20% suggests obstruction)
    - Fluid levels (dependent layering, HU 0-40)
    - Mucosal thickening (tissue in sinus periphery)
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        air_threshold: HU threshold for air
    
    Returns:
        Dict with:
        - left_opacification_grade: 0-2 (0=clear, 1=partial, 2=complete)
        - right_opacification_grade: 0-2
        - left_air_fraction: Fraction of left sphenoid that is air
        - right_air_fraction: Fraction of right sphenoid that is air
        - fluid_detected: Boolean for fluid level presence
    """
    if roi_provider is None:
        roi_provider = ManualROIProvider(air_threshold=air_threshold)
    
    z, y, x = volume.shape
    
    # Get ROI bounds
    roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'sphenoid')
    if roi_bounds is None:
        roi_provider = ManualROIProvider(air_threshold=air_threshold)
        roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'sphenoid')
    
    sphenoid_roi = volume[roi_bounds]
    
    # Split left/right
    roi_midline = sphenoid_roi.shape[2] // 2
    left_roi = sphenoid_roi[:, :, :roi_midline]
    right_roi = sphenoid_roi[:, :, roi_midline:]
    
    # Measure air fraction each side
    left_air_fraction = (left_roi < air_threshold).sum() / left_roi.size
    right_air_fraction = (right_roi < air_threshold).sum() / right_roi.size
    
    # Grade opacification (0=clear, 1=partial, 2=complete)
    def grade_opacification(air_frac):
        if air_frac > 0.50:
            return 0  # Clear
        elif air_frac > 0.10:
            return 1  # Partial
        else:
            return 2  # Complete
    
    left_grade = grade_opacification(left_air_fraction)
    right_grade = grade_opacification(right_air_fraction)
    
    # Check for fluid level (dependent density layering)
    # Fluid settles inferiorly, creating horizontal interface
    fluid_detected = False
    
    # Sample inferior vs superior HU in sphenoid
    inferior_slice = sphenoid_roi[-5:, :, :]  # Bottom slices
    superior_slice = sphenoid_roi[:5, :, :]   # Top slices
    
    # Exclude air voxels
    inferior_tissue = inferior_slice[(inferior_slice > air_threshold) & (inferior_slice < 100)]
    superior_tissue = superior_slice[(superior_slice > air_threshold) & (superior_slice < 100)]
    
    if len(inferior_tissue) > 10 and len(superior_tissue) > 10:
        # Fluid is denser than air but less than mucosa
        # Check if inferior is denser (fluid layering)
        if inferior_tissue.mean() > superior_tissue.mean() + 20:
            fluid_detected = True
    
    return {
        'left_opacification_grade': int(left_grade),
        'right_opacification_grade': int(right_grade),
        'left_air_fraction': float(left_air_fraction),
        'right_air_fraction': float(right_air_fraction),
        'fluid_detected': bool(fluid_detected),
    }


def measure_skull_base_thickness(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    bone_threshold: float = 200.0,  # Lowered from 300 to catch thinner bone
    roi_provider: Optional[ROIProvider] = None,
) -> Dict[str, float]:
    """
    Measure skull base bone thickness near sphenoid.
    
    Important for:
    - Assessing erosion risk in sphenoid infections
    - Surgical planning (transsphenoidal approaches)
    - CSF leak risk assessment
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        bone_threshold: HU threshold for bone (default 200, lower to catch thin bone)
    
    Returns:
        Dict with:
        - mean_thickness_mm: Average skull base thickness
        - minimum_thickness_mm: Thinnest point (concern if <1mm)
        - bone_volume_ml: Total bone volume in region
        - bone_hu_mean: Average bone HU (normal >500)
    """
    if roi_provider is None:
        roi_provider = ManualROIProvider()
    
    z, y, x = volume.shape
    
    # Get ROI bounds
    roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'skull_base')
    if roi_bounds is None:
        roi_provider = ManualROIProvider()
        roi_bounds = roi_provider.get_roi_bounds(volume, spacing, 'skull_base')
    
    skull_base_roi = volume[roi_bounds]
    
    # Segment bone
    bone_mask = skull_base_roi > bone_threshold
    
    if bone_mask.sum() < 10:
        # Return non-zero values with warning
        return {
            'mean_thickness_mm': 0.0,
            'minimum_thickness_mm': 0.0,
            'bone_volume_ml': 0.0,
            'bone_hu_mean': 0.0,
        }
    
    # Measure thickness along z-axis (superior-inferior)
    # For each (y, x) position, count consecutive bone voxels
    thicknesses = []
    for y_idx in range(skull_base_roi.shape[1]):
        for x_idx in range(skull_base_roi.shape[2]):
            column = bone_mask[:, y_idx, x_idx]
            
            # Find longest run of consecutive bone voxels
            if column.sum() > 0:
                # Count consecutive runs
                runs = []
                current_run = 0
                for val in column:
                    if val:
                        current_run += 1
                    else:
                        if current_run > 0:
                            runs.append(current_run)
                        current_run = 0
                if current_run > 0:
                    runs.append(current_run)
                
                # Use longest run as thickness at this position
                # Filter out single-voxel measurements (likely artifacts/foramina)
                if runs:
                    max_run_voxels = max(runs)
                    if max_run_voxels >= 2:  # Require at least 2 consecutive voxels
                        thickness_mm = max_run_voxels * spacing[0]
                        thicknesses.append(thickness_mm)
    
    if len(thicknesses) == 0:
        return {
            'mean_thickness_mm': 0.0,
            'minimum_thickness_mm': 0.0,
            'bone_volume_ml': 0.0,
            'bone_hu_mean': 0.0,
        }
    
    mean_thickness = np.mean(thicknesses)
    min_thickness = np.min(thicknesses)
    
    # Bone volume
    voxel_volume_mm3 = np.prod(spacing)
    bone_volume_ml = bone_mask.sum() * voxel_volume_mm3 / 1000
    
    # Mean bone HU
    bone_hu_mean = skull_base_roi[bone_mask].mean()
    
    return {
        'mean_thickness_mm': float(mean_thickness),
        'minimum_thickness_mm': float(min_thickness),
        'bone_volume_ml': float(bone_volume_ml),
        'bone_hu_mean': float(bone_hu_mean),
    }
