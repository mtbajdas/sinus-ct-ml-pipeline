"""
Adaptive Thresholding - Histogram-based tissue segmentation.

Computes optimal HU thresholds for air/tissue/bone separation using
bimodal histogram analysis within sinus cavity regions.
"""
from typing import Dict, Optional
import numpy as np


def adaptive_threshold_air_tissue(
    volume: np.ndarray,
    sinus_mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """
    Compute adaptive air/tissue thresholds using histogram within sinus cavities.
    
    Uses bimodal separation (Otsu-like) within the cavity region to find the
    valley between air peak (~-900) and tissue peak (~0).
    
    Args:
        volume: Calibrated CT volume
        sinus_mask: Optional binary mask of sinus cavities (if None, uses global histogram)
    
    Returns:
        {'air_threshold': float, 'tissue_lower': float, 'tissue_upper': float, 'bone_threshold': float}
    """
    if sinus_mask is not None:
        roi = volume[sinus_mask > 0]
    else:
        # Use central 50% of volume to avoid peripheral air/bone
        z, y, x = volume.shape
        roi = volume[
            z//4:3*z//4,
            y//4:3*y//4,
            x//4:3*x//4,
        ].ravel()
    
    # Histogram in range [-1000, 400] (typical sinus range)
    hist, bin_edges = np.histogram(roi, bins=140, range=(-1000, 400))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Find air peak (lowest HU with significant count)
    air_candidates = bin_centers < -600
    if air_candidates.sum() > 0:
        air_peak_idx = np.argmax(hist[air_candidates])
        air_peak = bin_centers[air_candidates][air_peak_idx]
    else:
        air_peak = -900.0
    
    # Find tissue peak (around 0 HU)
    tissue_candidates = (bin_centers > -200) & (bin_centers < 200)
    if tissue_candidates.sum() > 0:
        tissue_peak_idx = np.argmax(hist[tissue_candidates])
        tissue_peak = bin_centers[tissue_candidates][tissue_peak_idx]
    else:
        tissue_peak = 0.0
    
    # Valley between peaks = adaptive air threshold
    valley_region = (bin_centers > air_peak) & (bin_centers < tissue_peak)
    if valley_region.sum() > 0:
        valley_idx = np.argmin(hist[valley_region])
        air_threshold = bin_centers[valley_region][valley_idx]
    else:
        air_threshold = -400.0  # fallback
    
    return {
        'air_threshold': float(air_threshold),
        'tissue_lower': float(tissue_peak - 100),
        'tissue_upper': float(tissue_peak + 100),
        'bone_threshold': 300.0,  # conservative bone start
        'sclerosis_threshold': 900.0,  # high-density bone
        'air_peak': float(air_peak),
        'tissue_peak': float(tissue_peak),
    }
