"""
Oropharyngeal analysis module for head CT scans.

Provides quantitative measurements for:
- Palatine tonsils (size, volume, asymmetry)
- Oropharyngeal airway (patency, diameter)
"""

from .tonsil_metrics import (
    measure_tonsil_volumes,
    compute_brodsky_grade,
    measure_oropharyngeal_airway,
)

__all__ = [
    'measure_tonsil_volumes',
    'compute_brodsky_grade',
    'measure_oropharyngeal_airway',
]
