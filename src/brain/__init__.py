"""
Brain CT analysis module.

Modules:
- brain_metrics.py: Brain volume, tissue distribution, density analysis
- (future) hemorrhage.py: Acute blood detection
- (future) midline.py: Mass effect quantification
- (future) stroke.py: Hypodense region detection and ASPECTS scoring
- (future) ventricles.py: CSF space measurement for hydrocephalus
"""

from .brain_metrics import (
    analyze_brain,
    detect_brain_abnormalities,
)

__all__ = [
    'analyze_brain',
    'detect_brain_abnormalities',
]
