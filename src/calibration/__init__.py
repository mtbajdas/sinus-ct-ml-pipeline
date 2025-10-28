"""
Calibration Module - Physics-based HU correction and adaptive thresholding.

This module ensures CT scans are properly calibrated using anatomical anchors
(air, bone) and provides adaptive thresholds for tissue segmentation.
"""
from .hu_calibration import (
    calibrate_volume,
    detect_air_anchor,
    detect_bone_anchor,
    compute_hu_correction,
    apply_hu_correction,
)
from .adaptive_thresholds import adaptive_threshold_air_tissue

__all__ = [
    'calibrate_volume',
    'detect_air_anchor',
    'detect_bone_anchor',
    'compute_hu_correction',
    'apply_hu_correction',
    'adaptive_threshold_air_tissue',
]
