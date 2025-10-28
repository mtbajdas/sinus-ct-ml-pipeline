"""
Palatine tonsil quantitative metrics.

Functions for measuring tonsil volumes, airway obstruction grading,
and oropharyngeal airway patency from CT volumes.
"""
from __future__ import annotations

from typing import Dict, Tuple, Optional
import numpy as np
from scipy import ndimage


def has_oropharynx_coverage(volume: np.ndarray, spacing: Tuple[float, float, float]) -> bool:
    """
    Check if CT scan includes oropharyngeal region.
    
    Oropharynx extends from soft palate to hyoid bone (C2-C3 vertebral level).
    Requires sufficient inferior coverage beyond typical sinus CT.
    
    Args:
        volume: CT volume
        spacing: Voxel spacing (z, y, x) in mm
    
    Returns:
        True if oropharynx is included in scan
    """
    z, y, x = volume.shape
    
    # Check for sufficient superior-inferior extent
    # Typical sinus CT: ~80-100mm, sinus+oropharynx: >120mm
    si_extent_mm = z * spacing[0]
    
    if si_extent_mm < 100:
        return False
    
    # Check for presence of posterior airway (oropharynx has more posterior air)
    # Sample posterior region for air voxels
    posterior_third = volume[:, y//3:, :]
    air_fraction = (posterior_third < -200).sum() / posterior_third.size
    
    # Oropharynx should have >5% air in posterior region
    return air_fraction > 0.05


def segment_tonsils(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    soft_tissue_hu_range: Tuple[float, float] = (-100, 150),
) -> np.ndarray:
    """
    Segment palatine tonsils from CT volume.
    
    Strategy:
    - Lymphoid tissue HU range: -100 to 150 (wide soft tissue window for robustness to HU calibration)
    - Lateral to oropharyngeal airway
    - Paired symmetric structures
    - Located at oropharynx level (behind soft palate)
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        soft_tissue_hu_range: HU range for lymphoid tissue (default: -100 to 150 for calibration robustness)
    
    Returns:
        Binary mask of tonsil tissue (0=background, 1=left tonsil, 2=right tonsil)
    """
    # Find oropharynx level (inferior 25% of volume - the throat region)
    # Oropharynx is below nasopharynx and nasal cavity, typically at 75-95% inferior
    z, y, x = volume.shape
    oropharynx_z_start = int(z * 0.75)  # Start at 75% inferior (throat level)
    oropharynx_roi = volume[oropharynx_z_start:, :, :]
    
    # Soft tissue segmentation
    hu_min, hu_max = soft_tissue_hu_range
    tissue_mask = (oropharynx_roi >= hu_min) & (oropharynx_roi <= hu_max)
    
    # Morphological opening to remove noise
    tissue_mask = ndimage.binary_opening(tissue_mask, structure=np.ones((3, 3, 3)))
    
    # Find airway centerline (air voxels, HU < -200)
    airway_mask = oropharynx_roi < -200
    
    # For each axial slice, find lateral structures (tonsils are lateral to airway)
    tonsil_mask = np.zeros_like(tissue_mask, dtype=np.uint8)
    midline_x = x // 2
    
    # Tonsils are paramedian structures - limit search to ±30% from midline
    # This excludes lateral jaw/mandible tissues
    x_margin = int(x * 0.30)  # 30% on each side
    x_min_search = midline_x - x_margin
    x_max_search = midline_x + x_margin
    
    for z_idx in range(tissue_mask.shape[0]):
        slice_tissue = tissue_mask[z_idx, :, :].copy()
        slice_airway = airway_mask[z_idx, :, :]
        
        # Restrict to paramedian region only
        slice_tissue[:, :x_min_search] = 0  # Exclude far left
        slice_tissue[:, x_max_search:] = 0  # Exclude far right
        
        if slice_airway.sum() < 10:  # Skip slices without clear airway
            continue
        
        # Find airway centroid
        airway_coords = np.argwhere(slice_airway)
        if len(airway_coords) < 5:
            continue
        
        airway_center_x = int(airway_coords[:, 1].mean())
        
        # Left tonsil: tissue lateral to airway on left side (but within search region)
        left_region = slice_tissue.copy()
        left_region[:, airway_center_x:] = 0  # Keep only left side
        
        # Right tonsil: tissue lateral to airway on right side (but within search region)
        right_region = slice_tissue.copy()
        right_region[:, :airway_center_x] = 0  # Keep only right side
        
        # Label connected components and keep largest on each side
        # Also filter by size - tonsils are typically 100-5000 voxels per slice
        min_size = 100  # Minimum voxels for valid tonsil
        max_size = 5000  # Maximum voxels (exclude large jaw structures)
        
        if left_region.sum() > min_size:
            left_labeled, n_left = ndimage.label(left_region)
            if n_left > 0:
                sizes = np.bincount(left_labeled.ravel())[1:]
                # Find largest component within size limits
                valid_components = [(i+1, s) for i, s in enumerate(sizes) if min_size < s < max_size]
                if valid_components:
                    largest_idx, _ = max(valid_components, key=lambda x: x[1])
                    tonsil_mask[z_idx, :, :][left_labeled == largest_idx] = 1
        
        if right_region.sum() > min_size:
            right_labeled, n_right = ndimage.label(right_region)
            if n_right > 0:
                sizes = np.bincount(right_labeled.ravel())[1:]
                valid_components = [(i+1, s) for i, s in enumerate(sizes) if min_size < s < max_size]
                if valid_components:
                    largest_idx, _ = max(valid_components, key=lambda x: x[1])
                    tonsil_mask[z_idx, :, :][right_labeled == largest_idx] = 2
    
    # Reconstruct full volume mask
    full_mask = np.zeros_like(volume, dtype=np.uint8)
    full_mask[oropharynx_z_start:, :, :] = tonsil_mask
    
    return full_mask


def measure_tonsil_volumes(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    tonsil_mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """
    Measure palatine tonsil volumes.
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        tonsil_mask: Optional pre-segmented tonsil mask (1=left, 2=right)
    
    Returns:
        Dict with:
        - left_tonsil_volume_ml: Left tonsil volume in mL
        - right_tonsil_volume_ml: Right tonsil volume in mL
        - total_tonsil_volume_ml: Combined volume
        - asymmetry_ratio: Larger/smaller ratio (>2.0 = significant)
        - has_coverage: Whether scan includes oropharynx
    """
    if not has_oropharynx_coverage(volume, spacing):
        return {
            'left_tonsil_volume_ml': 0.0,
            'right_tonsil_volume_ml': 0.0,
            'total_tonsil_volume_ml': 0.0,
            'asymmetry_ratio': 0.0,
            'has_coverage': False,
        }
    
    # Segment tonsils if mask not provided
    if tonsil_mask is None:
        tonsil_mask = segment_tonsils(volume, spacing)
    
    # Compute volumes
    voxel_volume_mm3 = np.prod(spacing)
    
    left_voxels = (tonsil_mask == 1).sum()
    right_voxels = (tonsil_mask == 2).sum()
    
    left_vol_ml = left_voxels * voxel_volume_mm3 / 1000
    right_vol_ml = right_voxels * voxel_volume_mm3 / 1000
    total_vol_ml = left_vol_ml + right_vol_ml
    
    # Compute asymmetry ratio (larger/smaller)
    if left_vol_ml > 0 and right_vol_ml > 0:
        asymmetry_ratio = max(left_vol_ml, right_vol_ml) / min(left_vol_ml, right_vol_ml)
    else:
        asymmetry_ratio = 0.0
    
    return {
        'left_tonsil_volume_ml': float(left_vol_ml),
        'right_tonsil_volume_ml': float(right_vol_ml),
        'total_tonsil_volume_ml': float(total_vol_ml),
        'asymmetry_ratio': float(asymmetry_ratio),
        'has_coverage': True,
    }


def compute_brodsky_grade(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    tonsil_mask: Optional[np.ndarray] = None,
) -> Dict[str, object]:
    """
    Compute Brodsky obstruction grade (0-4 scale).
    
    Brodsky grading based on percentage of oropharyngeal airway obstructed:
    - Grade 0: Tonsils not visible/surgically removed
    - Grade 1: <25% obstruction
    - Grade 2: 25-50% obstruction
    - Grade 3: 50-75% obstruction
    - Grade 4: >75% obstruction (kissing tonsils)
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        tonsil_mask: Optional pre-segmented tonsil mask (1=left, 2=right)
    
    Returns:
        Dict with:
        - brodsky_grade: 0-4 integer grade
        - obstruction_pct: Percentage obstruction
        - minimum_airway_diameter_mm: Narrowest point
        - maximum_tonsil_span_mm: Widest tonsil extent
    """
    if not has_oropharynx_coverage(volume, spacing):
        return {
            'brodsky_grade': 0,
            'obstruction_pct': 0.0,
            'minimum_airway_diameter_mm': 0.0,
            'maximum_tonsil_span_mm': 0.0,
        }
    
    # Segment tonsils if not provided
    if tonsil_mask is None:
        tonsil_mask = segment_tonsils(volume, spacing)
    
    if tonsil_mask.sum() == 0:
        return {
            'brodsky_grade': 0,
            'obstruction_pct': 0.0,
            'minimum_airway_diameter_mm': 0.0,
            'maximum_tonsil_span_mm': 0.0,
        }
    
    # Find slice with maximum tonsil extent
    tonsil_areas_per_slice = (tonsil_mask > 0).sum(axis=(1, 2))
    max_slice_idx = np.argmax(tonsil_areas_per_slice)
    
    # Analyze at maximum tonsil level
    max_slice_tonsils = tonsil_mask[max_slice_idx, :, :]
    max_slice_volume = volume[max_slice_idx, :, :]
    
    # Find tonsil lateral extent
    left_tonsil_coords = np.argwhere(max_slice_tonsils == 1)
    right_tonsil_coords = np.argwhere(max_slice_tonsils == 2)
    
    if len(left_tonsil_coords) == 0 or len(right_tonsil_coords) == 0:
        return {
            'brodsky_grade': 0,
            'obstruction_pct': 0.0,
            'minimum_airway_diameter_mm': 0.0,
            'maximum_tonsil_span_mm': 0.0,
        }
    
    # Measure distance between medial tonsil edges (airway width)
    left_medial_x = left_tonsil_coords[:, 1].max()  # Rightmost point of left tonsil
    right_medial_x = right_tonsil_coords[:, 1].min()  # Leftmost point of right tonsil
    
    airway_width_voxels = right_medial_x - left_medial_x
    
    # Sanity check: if airway width is negative or too small, tonsils may be overlapping
    # or segmentation caught non-tonsil structures. Set minimum of 5mm.
    if airway_width_voxels < 1:
        airway_width_voxels = 5  # Assume at least 5 voxels (~2.5mm) airway
    
    airway_width_mm = airway_width_voxels * spacing[2]
    
    # Measure total lateral span (outer edges of tonsils)
    left_lateral_x = left_tonsil_coords[:, 1].min()
    right_lateral_x = right_tonsil_coords[:, 1].max()
    
    total_span_voxels = right_lateral_x - left_lateral_x
    total_span_mm = total_span_voxels * spacing[2]
    
    # Obstruction percentage
    tonsil_span_voxels = total_span_voxels - airway_width_voxels
    obstruction_pct = (tonsil_span_voxels / total_span_voxels) * 100
    
    # Brodsky grade classification
    if obstruction_pct < 25:
        brodsky_grade = 1
    elif obstruction_pct < 50:
        brodsky_grade = 2
    elif obstruction_pct < 75:
        brodsky_grade = 3
    else:
        brodsky_grade = 4
    
    return {
        'brodsky_grade': int(brodsky_grade),
        'obstruction_pct': float(obstruction_pct),
        'minimum_airway_diameter_mm': float(airway_width_mm),
        'maximum_tonsil_span_mm': float(total_span_mm),
    }


def measure_oropharyngeal_airway(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    air_threshold: float = -200.0,
) -> Dict[str, float]:
    """
    Measure oropharyngeal airway dimensions.
    
    Note: This function measures posterior airspace which may include
    nasal cavities and sinuses if scan has extensive coverage.
    For dedicated oropharynx measurement, would need soft palate/epiglottis landmarks.
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        air_threshold: HU threshold for airway (default -200)
    
    Returns:
        Dict with:
        - minimum_diameter_mm: Narrowest airway point
        - mean_diameter_mm: Average airway width
        - minimum_cross_sectional_area_mm2: Smallest area
        - mean_cross_sectional_area_mm2: Average area
        - airway_volume_ml: Total oropharyngeal airway volume
    """
    if not has_oropharynx_coverage(volume, spacing):
        return {
            'minimum_diameter_mm': 0.0,
            'mean_diameter_mm': 0.0,
            'minimum_cross_sectional_area_mm2': 0.0,
            'mean_cross_sectional_area_mm2': 0.0,
            'airway_volume_ml': 0.0,
        }
    
    # Focus on oropharynx region - use more posterior ROI to avoid nasal cavity
    z, y, x = volume.shape
    oropharynx_z_start = int(z * 0.6)
    
    # Focus on posterior region where oropharynx is located
    # Exclude anterior (nasal) regions
    oropharynx_roi = volume[
        oropharynx_z_start:,
        int(y * 0.4):,  # Posterior half only
        :
    ]
    
    # Segment airway
    airway_mask = oropharynx_roi < air_threshold
    
    # Further refine: remove very large connected components (likely sinuses)
    from scipy import ndimage
    labeled, n_components = ndimage.label(airway_mask)
    
    # Keep only mid-sized components (50-5000 voxels)
    # This filters out large sinus cavities and tiny noise
    # Typical oropharyngeal airway: 10-30 mL = ~30,000-100,000 voxels total
    # But fragmented into smaller regions, so use smaller component threshold
    refined_mask = np.zeros_like(airway_mask)
    for i in range(1, n_components + 1):
        component = labeled == i
        size = component.sum()
        if 50 < size < 5000:  # Individual airway segments
            refined_mask |= component
    
    # If no components in range, use more restrictive spatial filter
    if refined_mask.sum() < 50:
        # Use only central 30% of x-dimension and posterior 40% of y
        x_center = oropharynx_roi.shape[2] // 2
        x_margin = int(oropharynx_roi.shape[2] * 0.15)
        refined_mask = airway_mask.copy()
        refined_mask[:, :, :x_center-x_margin] = 0
        refined_mask[:, :, x_center+x_margin:] = 0
    
    # Measure per-slice metrics
    diameters = []
    areas = []
    
    voxel_area_mm2 = spacing[1] * spacing[2]
    
    for z_idx in range(refined_mask.shape[0]):
        slice_airway = refined_mask[z_idx, :, :]
        
        if slice_airway.sum() < 10:
            continue
        
        # Cross-sectional area
        area_mm2 = slice_airway.sum() * voxel_area_mm2
        areas.append(area_mm2)
        
        # Approximate diameter (assume roughly circular)
        # diameter = 2 * sqrt(area / pi)
        diameter_mm = 2 * np.sqrt(area_mm2 / np.pi)
        diameters.append(diameter_mm)
    
    # Total airway volume
    voxel_volume_mm3 = np.prod(spacing)
    airway_volume_ml = refined_mask.sum() * voxel_volume_mm3 / 1000
    
    if len(diameters) == 0:
        return {
            'minimum_diameter_mm': 0.0,
            'mean_diameter_mm': 0.0,
            'minimum_cross_sectional_area_mm2': 0.0,
            'mean_cross_sectional_area_mm2': 0.0,
            'airway_volume_ml': float(airway_volume_ml),
        }
    
    return {
        'minimum_diameter_mm': float(np.min(diameters)),
        'mean_diameter_mm': float(np.mean(diameters)),
        'minimum_cross_sectional_area_mm2': float(np.min(areas)),
        'mean_cross_sectional_area_mm2': float(np.mean(areas)),
        'airway_volume_ml': float(airway_volume_ml),
    }
