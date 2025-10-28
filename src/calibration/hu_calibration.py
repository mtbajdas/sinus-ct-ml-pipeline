"""
HU Calibration - Physics-based anchor detection and correction.

Ensures CT Hounsfield Units align with expected values by detecting internal
reference structures (air, cortical bone) and applying linear correction if needed.
"""
from __future__ import annotations

from typing import Dict, Tuple, Optional
from pathlib import Path
import json
import numpy as np


def detect_air_anchor(volume: np.ndarray, expected_hu: float = -1000.0, tolerance: float = 50.0) -> Dict[str, float]:
    """
    Detect air HU using regions outside the head or in nasopharynx.
    
    Strategy: Find voxels < -800 HU in peripheral regions, compute median.
    
    Returns:
        {'measured_hu': float, 'expected_hu': float, 'delta': float, 'pass': bool}
    """
    # Sample peripheral air (edges of FOV)
    z, y, x = volume.shape
    margin = 10
    peripheral_slices = [
        volume[:margin, :, :],
        volume[-margin:, :, :],
        volume[:, :margin, :],
        volume[:, -margin:, :],
    ]
    peripheral = np.concatenate([s.ravel() for s in peripheral_slices])
    
    # Air candidates: HU < -800
    air_candidates = peripheral[peripheral < -800]
    
    if air_candidates.size == 0:
        return {'measured_hu': np.nan, 'expected_hu': expected_hu, 'delta': np.nan, 'pass': False}
    
    measured = float(np.median(air_candidates))
    delta = measured - expected_hu
    passed = abs(delta) <= tolerance
    
    return {
        'measured_hu': measured,
        'expected_hu': expected_hu,
        'delta': delta,
        'pass': passed,
        'n_samples': int(air_candidates.size),
    }


def detect_bone_anchor(volume: np.ndarray, expected_hu: float = 1200.0, tolerance: float = 200.0) -> Dict[str, float]:
    """
    Detect cortical bone HU using hard palate or skull base regions.
    
    Strategy: Find dense bone (HU > 900) in inferior-central region (hard palate zone).
    
    Returns:
        {'measured_hu': float, 'expected_hu': float, 'delta': float, 'pass': bool}
    """
    z, y, x = volume.shape
    
    # Sample inferior-central region (hard palate ~ lower 20% of z, central 40% of x/y)
    z_start = int(z * 0.6)
    z_end = int(z * 0.8)
    y_center = y // 2
    x_center = x // 2
    y_margin = int(y * 0.2)
    x_margin = int(x * 0.2)
    
    palate_roi = volume[
        z_start:z_end,
        y_center - y_margin:y_center + y_margin,
        x_center - x_margin:x_center + x_margin,
    ]
    
    # Cortical bone candidates: HU > 900
    bone_candidates = palate_roi[palate_roi > 900]
    
    if bone_candidates.size == 0:
        return {'measured_hu': np.nan, 'expected_hu': expected_hu, 'delta': np.nan, 'pass': False}
    
    measured = float(np.median(bone_candidates))
    delta = measured - expected_hu
    passed = abs(delta) <= tolerance
    
    return {
        'measured_hu': measured,
        'expected_hu': expected_hu,
        'delta': delta,
        'pass': passed,
        'n_samples': int(bone_candidates.size),
    }


def compute_hu_correction(
    air_anchor: Dict[str, float],
    bone_anchor: Dict[str, float],
    correction_threshold: float = 50.0,
) -> Optional[Dict[str, float]]:
    """
    Compute linear HU correction: HU_corrected = slope * HU_raw + intercept.
    
    Only apply correction if both anchors are valid and delta exceeds threshold.
    
    Returns:
        {'slope': float, 'intercept': float, 'apply': bool} or None
    """
    if not (air_anchor['pass'] and bone_anchor['pass']):
        return None
    
    # Check if correction is needed
    max_delta = max(abs(air_anchor['delta']), abs(bone_anchor['delta']))
    if max_delta < correction_threshold:
        return {'slope': 1.0, 'intercept': 0.0, 'apply': False, 'max_delta': float(max_delta)}
    
    # Two-point linear fit: [air_measured, bone_measured] -> [air_expected, bone_expected]
    x = np.array([air_anchor['measured_hu'], bone_anchor['measured_hu']])
    y = np.array([air_anchor['expected_hu'], bone_anchor['expected_hu']])
    
    slope = (y[1] - y[0]) / (x[1] - x[0])
    intercept = y[0] - slope * x[0]
    
    return {
        'slope': float(slope),
        'intercept': float(intercept),
        'apply': True,
        'max_delta': float(max_delta),
    }


def apply_hu_correction(volume: np.ndarray, correction: Dict[str, float]) -> np.ndarray:
    """
    Apply linear HU correction to volume.
    
    Args:
        volume: Raw CT volume
        correction: Dict with 'slope', 'intercept', 'apply'
    
    Returns:
        Corrected volume (copy if applied, original if not)
    """
    if not correction or not correction.get('apply', False):
        return volume
    
    slope = correction['slope']
    intercept = correction['intercept']
    
    corrected = slope * volume + intercept
    return corrected.astype(volume.dtype)


def calibrate_volume(
    volume: np.ndarray,
    output_json: Optional[Path] = None,
) -> Tuple[np.ndarray, Dict[str, object]]:
    """
    Full calibration pipeline: detect anchors, compute correction, apply if needed.
    
    Args:
        volume: Raw CT volume
        output_json: Optional path to save calibration metadata
    
    Returns:
        (calibrated_volume, calibration_metadata)
    """
    air = detect_air_anchor(volume)
    bone = detect_bone_anchor(volume)
    correction = compute_hu_correction(air, bone)
    
    calibrated = apply_hu_correction(volume, correction) if correction else volume
    
    metadata = {
        'air_anchor': air,
        'bone_anchor': bone,
        'correction': correction,
        'applied': correction.get('apply', False) if correction else False,
    }
    
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(metadata, indent=2))
    
    return calibrated, metadata
