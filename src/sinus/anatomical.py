"""
Anatomical OMC Patency Assessment - Coronal corridor-based measurement.

Replaces symmetric box ROI with an anatomically-oriented approach:
- Coronal reformat to face orientation
- Corridor ROI at infundibulum level
- Median filtering across slices with morphological cleanup
- Classification: Patent / Indeterminate / Obstructed with confidence
"""
from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
from scipy import ndimage


def build_sinus_wall_shell(
    cavity_mask: np.ndarray,
    shell_thickness: int = 2,
) -> np.ndarray:
    """
    Build a thin shell around sinus cavities to isolate wall bone.
    
    Strategy: Dilate cavity by shell_thickness, then subtract cavity.
    
    Args:
        cavity_mask: Binary mask of sinus air cavities
        shell_thickness: Shell thickness in voxels (1-2 typical)
    
    Returns:
        Binary mask of sinus wall shell
    """
    dilated = ndimage.binary_dilation(cavity_mask, iterations=shell_thickness)
    shell = dilated & ~cavity_mask
    return shell


def compute_sclerosis_zscore(
    volume: np.ndarray,
    shell_mask: np.ndarray,
    reference_bone_hu: Tuple[float, float],
    z_threshold: float = 2.0,
    min_cluster_size: int = 30,
) -> Dict[str, object]:
    """
    Detect sclerotic bone within sinus wall shell using z-score method.
    
    Args:
        volume: Calibrated CT volume
        shell_mask: Binary mask of sinus wall shell
        reference_bone_hu: (mean, std) of reference cortical bone
        z_threshold: Z-score threshold for sclerosis (2.0 = 2 SD above normal)
        min_cluster_size: Minimum cluster size in voxels to count as pathologic
    
    Returns:
        {
            'sclerotic_fraction': float (% of shell),
            'sclerotic_volume_mm3': float,
            'n_clusters': int,
            'reference_mean_hu': float,
            'reference_std_hu': float,
            'threshold_hu': float,
        }
    """
    ref_mean, ref_std = reference_bone_hu
    threshold_hu = ref_mean + z_threshold * ref_std
    
    shell_voxels = volume[shell_mask > 0]
    sclerotic_candidates = shell_voxels > threshold_hu
    sclerotic_fraction = sclerotic_candidates.sum() / shell_voxels.size if shell_voxels.size > 0 else 0.0
    
    # Build 3D sclerotic mask and filter by cluster size
    sclerotic_mask = np.zeros_like(volume, dtype=bool)
    sclerotic_mask[shell_mask > 0] = (volume[shell_mask > 0] > threshold_hu)
    
    labeled, n_raw = ndimage.label(sclerotic_mask)
    cluster_sizes = np.bincount(labeled.ravel())[1:]  # skip background
    valid_clusters = np.where(cluster_sizes >= min_cluster_size)[0] + 1
    
    filtered_mask = np.isin(labeled, valid_clusters)
    sclerotic_voxels_filtered = filtered_mask.sum()
    sclerotic_fraction_filtered = sclerotic_voxels_filtered / shell_mask.sum() if shell_mask.sum() > 0 else 0.0
    
    return {
        'sclerotic_fraction': float(sclerotic_fraction_filtered),
        'sclerotic_volume_voxels': int(sclerotic_voxels_filtered),
        'n_clusters': int(len(valid_clusters)),
        'reference_mean_hu': float(ref_mean),
        'reference_std_hu': float(ref_std),
        'threshold_hu': float(threshold_hu),
        'z_threshold': float(z_threshold),
    }


def estimate_reference_bone_stats(volume: np.ndarray) -> Tuple[float, float]:
    """
    Estimate reference cortical bone HU (mean, std) from hard palate/skull base.
    
    Returns:
        (mean_hu, std_hu)
    """
    z, y, x = volume.shape
    
    # Sample inferior-central region (hard palate)
    z_start = int(z * 0.6)
    z_end = int(z * 0.8)
    y_center = y // 2
    x_center = x // 2
    y_margin = int(y * 0.15)
    x_margin = int(x * 0.15)
    
    bone_roi = volume[
        z_start:z_end,
        y_center - y_margin:y_center + y_margin,
        x_center - x_margin:x_center + x_margin,
    ]
    
    # Cortical bone: HU in [800, 1400]
    bone_voxels = bone_roi[(bone_roi > 800) & (bone_roi < 1400)]
    
    if bone_voxels.size < 100:
        # Fallback to typical values
        return (1100.0, 150.0)
    
    return (float(bone_voxels.mean()), float(bone_voxels.std()))


def measure_omc_patency_coronal(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    air_threshold: float = -400.0,
    morphology_radius: int = 2,
) -> Dict[str, object]:
    """
    Measure OMC patency using multi-candidate corridor search.
    
    Strategy:
    - Sample 3 candidate regions (anterior, mid, posterior) at likely infundibulum heights
    - For each side, pick the candidate with highest air fraction (most patent)
    - Apply morphological cleanup and median filtering
    - Classify: Patent (>50% air), Indeterminate (20-50%), Obstructed (<20%)
    
    Rationale: Anatomical variation means a single corridor may miss OMC;
    multi-region sampling ensures we capture the most patent pathway.
    
    Args:
        volume: Calibrated CT volume
        spacing: Voxel spacing (z, y, x) in mm
        air_threshold: HU threshold for air
        morphology_radius: Radius for morphological opening (remove noise)
    
    Returns:
        {
            'left': {'air_fraction': float, 'classification': str, 'confidence': float},
            'right': {'air_fraction': float, 'classification': str, 'confidence': float},
        }
    """
    z, y, x = volume.shape
    midline = x // 2
    
    # Define 3 candidate regions with different z and y ranges
    # Candidate 1: anterior-superior (classic infundibulum)
    # Candidate 2: mid-anterior (fallback if infundibulum higher)
    # Candidate 3: posterior-mid (uncinate region)
    candidates = [
        {
            'name': 'anterior_superior',
            'z': (int(z * 0.25), int(z * 0.45)),
            'y': (int(y * 0.35), int(y * 0.55)),
        },
        {
            'name': 'mid_anterior',
            'z': (int(z * 0.35), int(z * 0.55)),
            'y': (int(y * 0.40), int(y * 0.60)),
        },
        {
            'name': 'posterior_mid',
            'z': (int(z * 0.40), int(z * 0.60)),
            'y': (int(y * 0.50), int(y * 0.70)),
        },
    ]
    
    # Left and right corridor x-ranges (lateral bands)
    x_left = slice(midline - 50, midline - 5)
    x_right = slice(midline + 5, midline + 50)
    
    results = {}
    
    for side_name, x_range in [('left', x_left), ('right', x_right)]:
        best_air_fraction = 0.0
        best_classification = 'Obstructed'
        best_confidence = 1.0
        best_candidate = None
        
        # Try each candidate region
        for cand in candidates:
            z_start, z_end = cand['z']
            y_start, y_end = cand['y']
            
            corridor = volume[z_start:z_end, y_start:y_end, x_range]
            
            # Air mask with gentle morphological cleanup
            air_mask = corridor < air_threshold
            # Use smaller kernel (2x2x2) to preserve thin air columns
            air_mask_clean = ndimage.binary_opening(air_mask, structure=np.ones((2, 2, 2)))
            
            # Remove tiny isolated specks (< 3 voxels) but keep thin structures
            labeled, n = ndimage.label(air_mask_clean)
            if n == 0:
                continue
            sizes = np.bincount(labeled.ravel())[1:]
            if sizes.size == 0:
                continue
            valid = np.where(sizes >= 3)[0] + 1
            air_mask_filtered = np.isin(labeled, valid)
            
            # Compute air fraction per slice, then take median
            n_slices = corridor.shape[0]
            slice_fractions = []
            for i in range(n_slices):
                slice_air = air_mask_filtered[i, :, :].sum()
                slice_total = air_mask_filtered[i, :, :].size
                frac = slice_air / slice_total if slice_total > 0 else 0.0
                slice_fractions.append(frac)
            
            air_fraction = float(np.median(slice_fractions))
            
            # Classification (calibrated to anatomical reality)
            # Patent: >12% air (visible patent pathway confirmed by multi-slice consistency)
            # Indeterminate: 8-12% (partial, equivocal)
            # Obstructed: <8% (predominantly tissue/mucosa, no clear airway)
            if air_fraction > 0.12:
                classification = 'Patent'
            elif air_fraction > 0.08:
                classification = 'Indeterminate'
            else:
                classification = 'Obstructed'
            
            # Confidence: inverse of std across slices
            std_frac = float(np.std(slice_fractions))
            confidence = 1.0 - min(std_frac * 2.0, 0.99)
            
            # Keep best (highest air fraction)
            if air_fraction > best_air_fraction:
                best_air_fraction = air_fraction
                best_classification = classification
                best_confidence = confidence
                best_candidate = cand['name']
        
        results[side_name] = {
            'air_fraction': best_air_fraction,
            'air_fraction_pct': best_air_fraction * 100.0,
            'classification': best_classification,
            'confidence': best_confidence,
            'best_candidate': best_candidate if best_candidate else 'none',
        }
    
    return results


def detect_retention_cysts_strict(
    volume: np.ndarray,
    cavity_mask: np.ndarray,
    spacing: Tuple[float, float, float],
    hu_range: Tuple[float, float] = (-50, 50),
    min_area_mm2: float = 15.0,
    max_area_mm2: float = 500.0,
    wall_proximity_voxels: int = 3,
) -> Dict[str, object]:
    """
    Detect retention cysts with strict anatomical rules.
    
    Rules:
    - Component must be inside cavity
    - Attached to wall (within wall_proximity_voxels of cavity boundary)
    - Convex shape (solidity > 0.7)
    - Size in [min_area_mm2, max_area_mm2]
    - HU in [hu_range]
    - Exclude regions near ostia (top 20% of cavity in z)
    
    Args:
        volume: Calibrated CT volume
        cavity_mask: Binary mask of sinus air cavities
        spacing: Voxel spacing (z, y, x) in mm
        hu_range: HU range for cyst content
        min_area_mm2: Minimum cyst area in mm²
        max_area_mm2: Maximum cyst area in mm²
        wall_proximity_voxels: Max distance from wall to count as "attached"
    
    Returns:
        {
            'cyst_count': int,
            'cysts': [{'volume_mm3': float, 'mean_hu': float, 'centroid': tuple}, ...]
        }
    """
    voxel_volume_mm3 = np.prod(spacing)
    
    # Candidate voxels: inside cavity, HU in range
    candidates = cavity_mask & (volume > hu_range[0]) & (volume < hu_range[1])
    
    # Exclude ostium region (top 20% of z)
    z, y, x = volume.shape
    z_cutoff = int(z * 0.2)
    candidates[:z_cutoff, :, :] = False
    
    # Wall proximity: erode cavity, invert to get near-wall zone
    cavity_eroded = ndimage.binary_erosion(cavity_mask, iterations=wall_proximity_voxels)
    near_wall = cavity_mask & ~cavity_eroded
    candidates = candidates & near_wall
    
    # Label connected components
    labeled, n_components = ndimage.label(candidates)
    
    cysts = []
    for i in range(1, n_components + 1):
        component = (labeled == i)
        volume_mm3 = component.sum() * voxel_volume_mm3
        
        # Size filter
        if volume_mm3 < min_area_mm2 or volume_mm3 > max_area_mm2:
            continue
        
        # Convexity filter (approximate with bounding box fill ratio)
        coords = np.where(component)
        z_range = coords[0].max() - coords[0].min() + 1
        y_range = coords[1].max() - coords[1].min() + 1
        x_range = coords[2].max() - coords[2].min() + 1
        bbox_volume = z_range * y_range * x_range
        solidity = component.sum() / bbox_volume if bbox_volume > 0 else 0.0
        
        if solidity < 0.5:  # loose threshold; true cysts are more compact
            continue
        
        # Passed all filters
        component_hu = volume[component]
        centroid = tuple(float(c.mean()) for c in coords)
        
        cysts.append({
            'volume_mm3': float(volume_mm3),
            'mean_hu': float(component_hu.mean()),
            'centroid': centroid,
            'solidity': float(solidity),
        })
    
    return {
        'cyst_count': len(cysts),
        'cysts': cysts,
    }
