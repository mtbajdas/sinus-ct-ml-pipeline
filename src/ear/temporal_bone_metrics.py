"""
Temporal bone and ear analysis using TotalSegmentator.

Analyzes:
1. Mastoid pneumatization (air cell volume)
2. Temporal bone density
3. Left-right asymmetry
4. Potential pathology detection
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from core.roi_provider import ROIProvider, create_roi_provider


def analyze_temporal_bones(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    roi_provider: Optional[ROIProvider] = None,
    air_threshold: float = -400.0,
) -> Dict:
    """
    Comprehensive temporal bone analysis.
    
    Args:
        volume: CT volume (z, y, x)
        spacing: Voxel spacing in mm (z, y, x)
        roi_provider: ROI provider (auto-created if None)
        air_threshold: HU threshold for air (default: -400)
    
    Returns:
        Dictionary with left/right metrics:
        - total_volume_ml: Total temporal bone volume
        - air_volume_ml: Mastoid air cell volume
        - pneumatization_pct: Air fraction (normal: 40-60%)
        - mean_bone_hu: Average bone density
        - soft_tissue_pct: Soft tissue fraction (elevated in mastoiditis)
        - mean_hu: Overall mean HU
        - std_hu: HU standard deviation
        - asymmetry: Volume and pneumatization differences
    """
    if roi_provider is None:
        roi_provider = create_roi_provider('auto')
    
    # Get segmentations
    left_mask = roi_provider.get_roi_mask(volume, spacing, 'temporal_bone_left')
    right_mask = roi_provider.get_roi_mask(volume, spacing, 'temporal_bone_right')
    
    if left_mask is None or right_mask is None:
        return {
            'error': 'Temporal bones not segmented',
            'note': 'Scan may not include temporal bones or TotalSegmentator not available'
        }
    
    # Calculate voxel volume
    voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    
    # Use standard thresholds
    bone_threshold = 200  # Standard bone threshold
    
    results = {}
    
    for side, mask in [('left', left_mask), ('right', right_mask)]:
        roi = volume[mask > 0]
        
        if roi.size == 0:
            results[side] = {
                'error': f'{side.capitalize()} temporal bone not found in scan'
            }
            continue
        
        # Volume measurements
        total_volume_ml = roi.size * voxel_volume_mm3 / 1000
        
        # Mastoid pneumatization (air cells)
        air_voxels = (roi < air_threshold).sum()
        air_fraction = air_voxels / roi.size
        air_volume_ml = air_voxels * voxel_volume_mm3 / 1000
        
        # Bone density
        bone_voxels = roi[roi > bone_threshold]
        mean_bone_hu = float(bone_voxels.mean()) if len(bone_voxels) > 0 else 0.0
        
        # Soft tissue (potential pathology)
        soft_tissue = ((roi > -100) & (roi < bone_threshold)).sum()
        soft_tissue_fraction = soft_tissue / roi.size
        
        results[side] = {
            'total_volume_ml': float(total_volume_ml),
            'air_volume_ml': float(air_volume_ml),
            'pneumatization_pct': float(air_fraction * 100),
            'mean_bone_hu': float(mean_bone_hu),
            'soft_tissue_pct': float(soft_tissue_fraction * 100),
            'mean_hu': float(roi.mean()),
            'std_hu': float(roi.std()),
        }
    
    # Asymmetry score
    if 'error' not in results.get('left', {}) and 'error' not in results.get('right', {}):
        volume_asymmetry = abs(
            results['left']['total_volume_ml'] - results['right']['total_volume_ml']
        )
        pneumatization_asymmetry = abs(
            results['left']['pneumatization_pct'] - results['right']['pneumatization_pct']
        )
        
        results['asymmetry'] = {
            'volume_difference_ml': float(volume_asymmetry),
            'pneumatization_difference_pct': float(pneumatization_asymmetry),
        }
    
    return results


def detect_mastoiditis(temporal_results: Dict) -> Dict:
    """
    Screen for potential mastoiditis based on mastoid air cell patterns.
    
    Red flags:
    - Reduced pneumatization (<20% vs normal 40-60%)
    - Increased soft tissue fraction (>20% vs normal <10%)
    - Significant asymmetry (>15% difference)
    
    Args:
        temporal_results: Output from analyze_temporal_bones()
    
    Returns:
        Dictionary with:
        - left_concern: Bool indicating left-sided concern
        - right_concern: Bool indicating right-sided concern
        - asymmetry_concern: Bool indicating asymmetry
        - notes: List of specific findings
        - interpretation: Clinical interpretation string
    """
    findings = {
        'left_concern': False,
        'right_concern': False,
        'asymmetry_concern': False,
        'notes': []
    }
    
    # Check if analysis was successful
    if 'error' in temporal_results:
        findings['notes'].append(temporal_results['error'])
        findings['interpretation'] = 'Unable to assess'
        return findings
    
    # Check left side
    if 'left' in temporal_results and 'error' not in temporal_results['left']:
        left = temporal_results['left']
        
        if left['pneumatization_pct'] < 20:
            findings['left_concern'] = True
            findings['notes'].append(
                f"Left mastoid: Reduced pneumatization ({left['pneumatization_pct']:.1f}% vs normal 40-60%)"
            )
        
        if left['soft_tissue_pct'] > 20:
            findings['left_concern'] = True
            findings['notes'].append(
                f"Left mastoid: Increased soft tissue ({left['soft_tissue_pct']:.1f}% vs normal <10%)"
            )
    
    # Check right side
    if 'right' in temporal_results and 'error' not in temporal_results['right']:
        right = temporal_results['right']
        
        if right['pneumatization_pct'] < 20:
            findings['right_concern'] = True
            findings['notes'].append(
                f"Right mastoid: Reduced pneumatization ({right['pneumatization_pct']:.1f}% vs normal 40-60%)"
            )
        
        if right['soft_tissue_pct'] > 20:
            findings['right_concern'] = True
            findings['notes'].append(
                f"Right mastoid: Increased soft tissue ({right['soft_tissue_pct']:.1f}% vs normal <10%)"
            )
    
    # Check asymmetry
    if 'asymmetry' in temporal_results:
        if temporal_results['asymmetry']['pneumatization_difference_pct'] > 15:
            findings['asymmetry_concern'] = True
            findings['notes'].append(
                f"Asymmetric pneumatization: {temporal_results['asymmetry']['pneumatization_difference_pct']:.1f}% difference"
            )
    
    # Generate interpretation
    if findings['left_concern'] or findings['right_concern'] or findings['asymmetry_concern']:
        findings['interpretation'] = (
            'Findings suggestive of possible mastoid pathology. '
            'Clinical correlation recommended. Consider: chronic otitis media, '
            'mastoiditis, cholesteatoma.'
        )
    else:
        findings['interpretation'] = (
            'Mastoid air cells appear normally pneumatized. '
            'No obvious signs of mastoiditis.'
        )
    
    return findings
