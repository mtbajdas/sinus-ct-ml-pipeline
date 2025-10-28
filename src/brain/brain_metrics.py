"""
Brain parenchyma analysis from head CT.

Analyzes:
1. Total brain volume
2. White/gray matter distribution
3. CSF fraction (ventricle size estimation)
4. Density abnormalities
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from core.roi_provider import ROIProvider, create_roi_provider


def analyze_brain(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    roi_provider: Optional[ROIProvider] = None,
) -> Dict:
    """
    Comprehensive brain analysis.
    
    Args:
        volume: CT volume (z, y, x)
        spacing: Voxel spacing in mm (z, y, x)
        roi_provider: ROI provider (auto-created if None)
    
    Returns:
        Dictionary with brain metrics:
        - brain.total_volume_ml: Total brain parenchyma volume
        - brain.mean_hu: Average brain density
        - brain.csf_volume_ml: CSF volume (ventricular + sulcal)
        - brain.white_matter_volume_ml: White matter volume (HU-based)
        - brain.gray_matter_volume_ml: Gray matter volume (HU-based)
        - brain.*_fraction_pct: Tissue fractions
        - brainstem.volume_ml: Brainstem volume (if available)
        - pituitary.volume_ml: Pituitary gland volume (if available)
    """
    if roi_provider is None:
        roi_provider = create_roi_provider('auto')
    
    # Get segmentations
    brain_mask = roi_provider.get_roi_mask(volume, spacing, 'brain')
    brainstem_mask = roi_provider.get_roi_mask(volume, spacing, 'brainstem')
    pituitary_mask = roi_provider.get_roi_mask(volume, spacing, 'pituitary_gland')
    
    if brain_mask is None:
        return {
            'error': 'Brain not segmented',
            'note': 'Scan may not include brain or TotalSegmentator not available'
        }
    
    voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    
    results = {}
    
    # Total brain analysis
    brain_roi = volume[brain_mask > 0]
    
    if brain_roi.size == 0:
        results['brain'] = {'error': 'Brain not found in scan'}
        return results
    
    total_volume_ml = brain_roi.size * voxel_volume_mm3 / 1000
    
    # Tissue classification by HU (CT-based approximations)
    # CSF: 0-15 HU (ventricular + sulcal)
    # White matter: 25-35 HU
    # Gray matter: 35-45 HU
    # Note: These are rough approximations; CT has limited soft tissue contrast
    
    csf_voxels = ((brain_roi > 0) & (brain_roi < 15)).sum()
    white_matter_voxels = ((brain_roi > 25) & (brain_roi < 35)).sum()
    gray_matter_voxels = ((brain_roi > 35) & (brain_roi < 45)).sum()
    
    csf_volume_ml = csf_voxels * voxel_volume_mm3 / 1000
    white_volume_ml = white_matter_voxels * voxel_volume_mm3 / 1000
    gray_volume_ml = gray_matter_voxels * voxel_volume_mm3 / 1000
    
    results['brain'] = {
        'total_volume_ml': float(total_volume_ml),
        'mean_hu': float(brain_roi.mean()),
        'std_hu': float(brain_roi.std()),
        'csf_volume_ml': float(csf_volume_ml),
        'white_matter_volume_ml': float(white_volume_ml),
        'gray_matter_volume_ml': float(gray_volume_ml),
        'csf_fraction_pct': float(csf_voxels / brain_roi.size * 100),
        'white_matter_fraction_pct': float(white_matter_voxels / brain_roi.size * 100),
        'gray_matter_fraction_pct': float(gray_matter_voxels / brain_roi.size * 100),
    }
    
    # Brainstem analysis
    if brainstem_mask is not None and brainstem_mask.sum() > 0:
        brainstem_roi = volume[brainstem_mask > 0]
        results['brainstem'] = {
            'volume_ml': float(brainstem_roi.size * voxel_volume_mm3 / 1000),
            'mean_hu': float(brainstem_roi.mean()),
            'std_hu': float(brainstem_roi.std()),
        }
    
    # Pituitary analysis
    if pituitary_mask is not None and pituitary_mask.sum() > 0:
        pituitary_roi = volume[pituitary_mask > 0]
        results['pituitary'] = {
            'volume_mm3': float(pituitary_roi.size * voxel_volume_mm3),  # In mm³ (smaller structure)
            'volume_ml': float(pituitary_roi.size * voxel_volume_mm3 / 1000),
            'mean_hu': float(pituitary_roi.mean()),
            'std_hu': float(pituitary_roi.std()),
        }
    
    return results


def detect_brain_abnormalities(brain_results: Dict) -> Dict:
    """
    Screen for potential brain abnormalities.
    
    Reference values (adult):
    - Total brain: 1200-1400 mL
    - White matter: ~40% of brain
    - Gray matter: ~40% of brain
    - CSF: 10-15% of brain (increased in atrophy, hydrocephalus)
    - Mean HU: 30-35 (decreased in edema, infarct)
    - Brainstem: 20-30 mL
    - Pituitary: 400-600 mm³
    
    Args:
        brain_results: Output from analyze_brain()
    
    Returns:
        Dictionary with:
        - atrophy_concern: Bool indicating possible atrophy
        - hydrocephalus_concern: Bool indicating possible hydrocephalus
        - density_concern: Bool indicating abnormal density
        - pituitary_concern: Bool indicating pituitary abnormality
        - notes: List of specific findings
        - interpretation: Clinical interpretation string
    """
    findings = {
        'atrophy_concern': False,
        'hydrocephalus_concern': False,
        'density_concern': False,
        'pituitary_concern': False,
        'notes': []
    }
    
    # Check if analysis was successful
    if 'error' in brain_results:
        findings['notes'].append(brain_results['error'])
        findings['interpretation'] = 'Unable to assess'
        return findings
    
    if 'brain' not in brain_results or 'error' in brain_results.get('brain', {}):
        findings['notes'].append('Brain analysis incomplete')
        findings['interpretation'] = 'Unable to assess'
        return findings
    
    brain = brain_results['brain']
    
    # Volume assessment
    if brain['total_volume_ml'] < 1100:
        findings['atrophy_concern'] = True
        findings['notes'].append(
            f"Reduced brain volume: {brain['total_volume_ml']:.0f} mL (normal: 1200-1400 mL). "
            f"Consider: age-related atrophy, neurodegenerative disease."
        )
    
    # CSF assessment (surrogate for ventricular size)
    if brain['csf_fraction_pct'] > 20:
        findings['hydrocephalus_concern'] = True
        findings['notes'].append(
            f"Increased CSF fraction: {brain['csf_fraction_pct']:.1f}% (normal: 10-15%). "
            f"Consider: hydrocephalus, prominent sulci (atrophy)."
        )
    
    # Density assessment
    if brain['mean_hu'] < 28:
        findings['density_concern'] = True
        findings['notes'].append(
            f"Reduced brain density: {brain['mean_hu']:.1f} HU (normal: 30-35 HU). "
            f"Consider: edema, acute infarct, demyelination."
        )
    
    # Brainstem assessment
    if 'brainstem' in brain_results:
        brainstem = brain_results['brainstem']
        if brainstem['volume_ml'] < 15:
            findings['notes'].append(
                f"Small brainstem volume: {brainstem['volume_ml']:.1f} mL (normal: 20-30 mL). "
                f"May be normal variant or measurement artifact."
            )
    
    # Pituitary assessment
    if 'pituitary' in brain_results:
        pituitary = brain_results['pituitary']
        if pituitary['volume_mm3'] > 800:
            findings['pituitary_concern'] = True
            findings['notes'].append(
                f"Enlarged pituitary: {pituitary['volume_mm3']:.0f} mm³ (normal: 400-600 mm³). "
                f"Consider: macroadenoma, hyperplasia."
            )
        elif pituitary['volume_mm3'] < 300:
            findings['pituitary_concern'] = True
            findings['notes'].append(
                f"Small pituitary: {pituitary['volume_mm3']:.0f} mm³ (normal: 400-600 mm³). "
                f"Consider: hypopituitarism, empty sella."
            )
    
    # Generate interpretation
    concern_count = sum([
        findings['atrophy_concern'],
        findings['hydrocephalus_concern'],
        findings['density_concern'],
        findings['pituitary_concern']
    ])
    
    if concern_count == 0:
        findings['interpretation'] = (
            'Brain parenchyma appears within normal limits. '
            'No obvious structural abnormalities detected.'
        )
    elif concern_count == 1:
        findings['interpretation'] = (
            'One area of concern identified. Clinical correlation recommended. '
            'Consider dedicated neuroimaging if clinically indicated.'
        )
    else:
        findings['interpretation'] = (
            'Multiple areas of concern identified. Recommend dedicated neuroimaging '
            'and clinical correlation. Consider neurology consultation.'
        )
    
    return findings
