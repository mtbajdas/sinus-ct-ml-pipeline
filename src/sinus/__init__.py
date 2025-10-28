"""
Metrics Module - Anatomically-informed quantitative measurements.

This module provides validated measurements for sinus pathology including
OMC patency, sclerotic bone, retention cysts, clinical scoring, and deep sinus analysis.
"""
from .anatomical import (
    build_sinus_wall_shell,
    estimate_reference_bone_stats,
    measure_omc_patency_coronal,
)
from .pathology import (
    compute_sclerosis_zscore,
    detect_retention_cysts_strict,
)
from .deep_sinus import (
    measure_sphenoid_volume,
    measure_posterior_ethmoid_volume,
    check_sphenoid_opacification,
    measure_skull_base_thickness,
)

__all__ = [
    'build_sinus_wall_shell',
    'estimate_reference_bone_stats',
    'measure_omc_patency_coronal',
    'compute_sclerosis_zscore',
    'detect_retention_cysts_strict',
    'measure_sphenoid_volume',
    'measure_posterior_ethmoid_volume',
    'check_sphenoid_opacification',
    'measure_skull_base_thickness',
]
