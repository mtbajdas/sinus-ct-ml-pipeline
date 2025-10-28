"""
Head CT analysis orchestrator using pluggable ROI providers.

This module provides a unified interface for analyzing any head CT structure
by leveraging the ROI provider system.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import nibabel as nib
import numpy as np

from core.roi_provider import create_roi_provider, ROIProvider
from sinus.deep_sinus import (
    measure_sphenoid_volume,
    measure_posterior_ethmoid_volume,
    check_sphenoid_opacification,
    measure_skull_base_thickness,
)
from ear.temporal_bone_metrics import analyze_temporal_bones, detect_mastoiditis
from brain.brain_metrics import analyze_brain, detect_brain_abnormalities

logger = logging.getLogger(__name__)


class HeadCTAnalyzer:
    """
    Comprehensive head CT analysis using pluggable ROI providers.
    
    Supports multiple structures:
    - Paranasal sinuses (sphenoid, ethmoid, maxillary, frontal)
    - Skull base
    - Temporal bones (ears) - mastoid air cells
    - Brain structures (parenchyma, brainstem, pituitary)
    """
    
    def __init__(
        self,
        nifti_path: Path,
        roi_provider: Optional[ROIProvider] = None,
        roi_provider_type: str = "auto",
    ):
        """
        Args:
            nifti_path: Path to processed NIfTI CT volume
            roi_provider: Pre-configured ROI provider (overrides roi_provider_type)
            roi_provider_type: 'manual', 'totalsegmentator', or 'auto'
        """
        self.nifti_path = Path(nifti_path)
        
        # Load volume
        logger.info(f"Loading {self.nifti_path}")
        nii = nib.load(self.nifti_path)
        self.volume = nii.get_fdata()
        self.spacing = nii.header.get_zooms()[:3]
        
        logger.info(f"Volume shape: {self.volume.shape}, spacing: {self.spacing}")
        
        # Initialize ROI provider
        if roi_provider is not None:
            self.roi_provider = roi_provider
        else:
            self.roi_provider = create_roi_provider(roi_provider_type)
        
        logger.info(f"Using ROI provider: {self.roi_provider.name}")
    
    def analyze_deep_sinuses(self) -> Dict:
        """
        Analyze deep paranasal sinuses (sphenoid, posterior ethmoid, skull base).
        
        Returns comprehensive metrics including volumes, air fractions, and pathology indicators.
        """
        logger.info("Analyzing deep sinuses...")
        
        results = {}
        
        # Sphenoid sinus
        try:
            results['sphenoid'] = measure_sphenoid_volume(
                self.volume,
                self.spacing,
                roi_provider=self.roi_provider,
            )
            logger.info(f"  Sphenoid volume: {results['sphenoid']['sphenoid_volume_ml']:.1f} mL")
        except Exception as e:
            logger.error(f"Failed to measure sphenoid: {e}")
            results['sphenoid'] = None
        
        # Sphenoid opacification
        try:
            results['sphenoid_opacification'] = check_sphenoid_opacification(
                self.volume,
                self.spacing,
                roi_provider=self.roi_provider,
            )
            logger.info(f"  Sphenoid opacification: L={results['sphenoid_opacification']['left_opacification_grade']}, R={results['sphenoid_opacification']['right_opacification_grade']}")
        except Exception as e:
            logger.error(f"Failed to check sphenoid opacification: {e}")
            results['sphenoid_opacification'] = None
        
        # Posterior ethmoid
        try:
            results['posterior_ethmoid'] = measure_posterior_ethmoid_volume(
                self.volume,
                self.spacing,
                roi_provider=self.roi_provider,
            )
            logger.info(f"  Posterior ethmoid volume: {results['posterior_ethmoid']['posterior_ethmoid_volume_ml']:.1f} mL")
        except Exception as e:
            logger.error(f"Failed to measure posterior ethmoid: {e}")
            results['posterior_ethmoid'] = None
        
        # Skull base
        try:
            results['skull_base'] = measure_skull_base_thickness(
                self.volume,
                self.spacing,
                roi_provider=self.roi_provider,
            )
            logger.info(f"  Skull base thickness: {results['skull_base']['mean_thickness_mm']:.2f} mm (min: {results['skull_base']['minimum_thickness_mm']:.2f} mm)")
        except Exception as e:
            logger.error(f"Failed to measure skull base: {e}")
            results['skull_base'] = None
        
        return results
    
    def analyze_all_sinuses(self) -> Dict:
        """
        Analyze all paranasal sinuses if provider supports them.
        
        Returns metrics for maxillary, frontal, ethmoid, and sphenoid sinuses.
        """
        available = self.roi_provider.get_available_structures()
        logger.info(f"Provider supports {len(available)} structures")
        
        results = {}
        
        # Identify sinus structures
        sinus_structures = [s for s in available if 'sinus' in s.lower() or 'ethmoid' in s.lower()]
        
        for structure in sinus_structures:
            try:
                mask = self.roi_provider.get_roi_mask(self.volume, self.spacing, structure)
                if mask is not None and mask.sum() > 0:
                    volume_ml = mask.sum() * np.prod(self.spacing) / 1000
                    # Calculate air fraction within mask
                    roi_volume = self.volume[mask]
                    air_fraction = (roi_volume < -400).sum() / roi_volume.size if roi_volume.size > 0 else 0.0
                    
                    results[structure] = {
                        'volume_ml': float(volume_ml),
                        'air_fraction': float(air_fraction),
                        'voxel_count': int(mask.sum()),
                    }
                    logger.info(f"  {structure}: {volume_ml:.1f} mL, {air_fraction*100:.1f}% air")
            except Exception as e:
                logger.warning(f"Failed to analyze {structure}: {e}")
        
        return results
    
    def analyze_skull_structures(self) -> Dict:
        """
        Analyze skull and bone structures.
        
        Returns metrics for skull, mandible, maxilla, temporal bones, etc.
        """
        available = self.roi_provider.get_available_structures()
        
        results = {}
        
        # Identify bone structures
        bone_structures = [
            s for s in available
            if any(keyword in s.lower() for keyword in ['skull', 'bone', 'mandible', 'maxilla', 'temporal'])
        ]
        
        for structure in bone_structures:
            try:
                mask = self.roi_provider.get_roi_mask(self.volume, self.spacing, structure)
                if mask is not None and mask.sum() > 0:
                    volume_ml = mask.sum() * np.prod(self.spacing) / 1000
                    roi_volume = self.volume[mask]
                    mean_hu = roi_volume.mean() if roi_volume.size > 0 else 0.0
                    
                    results[structure] = {
                        'volume_ml': float(volume_ml),
                        'mean_hu': float(mean_hu),
                        'voxel_count': int(mask.sum()),
                    }
                    logger.info(f"  {structure}: {volume_ml:.1f} mL, {mean_hu:.0f} HU")
            except Exception as e:
                logger.warning(f"Failed to analyze {structure}: {e}")
        
        return results
    
    def analyze_temporal_bones(self) -> Dict:
        """
        Analyze temporal bones and mastoid air cells.
        
        Returns:
            Dictionary with left/right temporal bone metrics and mastoiditis screening
        """
        logger.info("\nAnalyzing temporal bones...")
        
        try:
            temporal_results = analyze_temporal_bones(
                self.volume,
                self.spacing,
                self.roi_provider
            )
            
            if 'error' not in temporal_results:
                # Display results
                for side in ['left', 'right']:
                    if side in temporal_results and 'error' not in temporal_results[side]:
                        metrics = temporal_results[side]
                        logger.info(f"  {side.capitalize()} temporal bone:")
                        logger.info(f"    Volume: {metrics['total_volume_ml']:.1f} mL")
                        logger.info(f"    Pneumatization: {metrics['pneumatization_pct']:.1f}%")
                        logger.info(f"    Bone density: {metrics['mean_bone_hu']:.0f} HU")
                
                # Screen for mastoiditis
                mastoiditis_screen = detect_mastoiditis(temporal_results)
                temporal_results['mastoiditis_screening'] = mastoiditis_screen
                
                if mastoiditis_screen['notes']:
                    logger.info(f"\n  ⚠️ Mastoid findings:")
                    for note in mastoiditis_screen['notes']:
                        logger.info(f"    - {note}")
            else:
                logger.info(f"  {temporal_results.get('note', 'Not available')}")
            
            return temporal_results
            
        except Exception as e:
            logger.warning(f"Failed to analyze temporal bones: {e}")
            return {'error': str(e)}
    
    def analyze_brain_structures(self) -> Dict:
        """
        Analyze brain parenchyma and related structures.
        
        Returns:
            Dictionary with brain metrics and abnormality screening
        """
        logger.info("\nAnalyzing brain structures...")
        
        try:
            brain_results = analyze_brain(
                self.volume,
                self.spacing,
                self.roi_provider
            )
            
            if 'error' not in brain_results:
                # Display brain results
                if 'brain' in brain_results:
                    brain = brain_results['brain']
                    logger.info(f"  Brain parenchyma:")
                    logger.info(f"    Total volume: {brain['total_volume_ml']:.0f} mL")
                    logger.info(f"    Mean HU: {brain['mean_hu']:.1f}")
                    logger.info(f"    CSF fraction: {brain['csf_fraction_pct']:.1f}%")
                    logger.info(f"    White matter: {brain['white_matter_volume_ml']:.0f} mL")
                    logger.info(f"    Gray matter: {brain['gray_matter_volume_ml']:.0f} mL")
                
                if 'brainstem' in brain_results:
                    brainstem = brain_results['brainstem']
                    logger.info(f"  Brainstem: {brainstem['volume_ml']:.1f} mL")
                
                if 'pituitary' in brain_results:
                    pituitary = brain_results['pituitary']
                    logger.info(f"  Pituitary gland: {pituitary['volume_mm3']:.0f} mm³")
                
                # Screen for abnormalities
                abnormality_screen = detect_brain_abnormalities(brain_results)
                brain_results['abnormality_screening'] = abnormality_screen
                
                if abnormality_screen['notes']:
                    logger.info(f"\n  ℹ️ Brain findings:")
                    for note in abnormality_screen['notes']:
                        logger.info(f"    - {note}")
            else:
                logger.info(f"  {brain_results.get('note', 'Not available')}")
            
            return brain_results
            
        except Exception as e:
            logger.warning(f"Failed to analyze brain structures: {e}")
            return {'error': str(e)}
    
    def generate_comprehensive_report(self, output_path: Optional[Path] = None) -> Dict:
        """
        Generate comprehensive analysis of all available structures.
        
        Args:
            output_path: Optional path to save JSON report
        
        Returns:
            Dictionary with analysis results for all structures
        """
        logger.info("="*80)
        logger.info(f"HEAD CT COMPREHENSIVE ANALYSIS")
        logger.info(f"ROI Provider: {self.roi_provider.name}")
        logger.info("="*80)
        
        report = {
            'metadata': {
                'nifti_path': str(self.nifti_path),
                'volume_shape': list(self.volume.shape),
                'spacing_mm': list(self.spacing),
                'roi_provider': self.roi_provider.name,
            },
            'deep_sinuses': self.analyze_deep_sinuses(),
            'all_sinuses': self.analyze_all_sinuses(),
            'skull_structures': self.analyze_skull_structures(),
            'temporal_bones': self.analyze_temporal_bones(),
            'brain': self.analyze_brain_structures(),
        }
        
        # Save report
        if output_path is not None:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert numpy types to native Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(v) for v in obj]
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                else:
                    return obj
            
            report = convert_numpy_types(report)
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"\n✓ Report saved to: {output_path}")
        
        return report


def main():
    """Example usage of HeadCTAnalyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive head CT analysis")
    parser.add_argument('--input', type=Path, required=True, help='Input NIfTI file')
    parser.add_argument('--output', type=Path, help='Output JSON report path')
    parser.add_argument(
        '--provider',
        choices=['manual', 'totalsegmentator', 'auto'],
        default='auto',
        help='ROI provider type'
    )
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(message)s'
    )
    
    # Run analysis
    analyzer = HeadCTAnalyzer(
        nifti_path=args.input,
        roi_provider_type=args.provider,
    )
    
    output_path = args.output or Path('docs/metrics/comprehensive_head_analysis.json')
    report = analyzer.generate_comprehensive_report(output_path)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
