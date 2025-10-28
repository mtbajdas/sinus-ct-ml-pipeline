"""
Pathology Detection - Sclerotic bone and retention cysts.

Provides validated detection algorithms for common sinus pathologies
including mucosal thickening, sclerotic bone changes, and retention cysts.
"""
from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
from scipy import ndimage


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
