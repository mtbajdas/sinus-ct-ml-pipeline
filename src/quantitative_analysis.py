"""
Quantitative analysis of sinus CT scans using PyRadiomics and custom metrics.

Extracts:
1. Volumetric measurements (air, mucosa, fluid)
2. PyRadiomics texture features
3. Anatomical landmarks and asymmetry
4. Longitudinal change detection
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

import nibabel as nib
import numpy as np
from scipy import ndimage
from scipy.spatial.distance import euclidean

logger = logging.getLogger(__name__)


@dataclass
class VolumetricMetrics:
    """Volumetric measurements for sinus analysis."""
    total_sinus_volume_ml: float
    air_volume_ml: float
    soft_tissue_volume_ml: float
    air_fraction: float
    
    # Per-sinus breakdown (if labeled)
    maxillary_left_ml: float | None = None
    maxillary_right_ml: float | None = None
    frontal_left_ml: float | None = None
    frontal_right_ml: float | None = None
    ethmoid_left_ml: float | None = None
    ethmoid_right_ml: float | None = None
    sphenoid_ml: float | None = None


@dataclass
class TextureMetrics:
    """PyRadiomics texture features."""
    # First-order statistics
    mean_intensity: float
    std_intensity: float
    skewness: float
    kurtosis: float
    entropy: float
    
    # GLCM features
    glcm_contrast: float
    glcm_homogeneity: float
    glcm_energy: float
    
    # GLRLM features
    glrlm_sre: float  # Short run emphasis
    glrlm_lre: float  # Long run emphasis


@dataclass
class AnalysisReport:
    """Complete quantitative analysis report."""
    patient_id: str
    study_date: str
    volumetric: VolumetricMetrics
    texture: TextureMetrics | None
    asymmetry_score: float | None
    metadata: Dict


class SinusAnalyzer:
    """Comprehensive sinus CT analysis."""
    
    def __init__(
        self,
        image_path: Path,
        mask_path: Path | None = None,
        spacing: tuple[float, float, float] | None = None,
    ):
        self.image_path = image_path
        self.mask_path = mask_path
        
        # Load image
        img = nib.load(str(image_path))
        self.volume = img.get_fdata().astype(np.float32)
        self.spacing = spacing or img.header.get_zooms()[:3]
        self.voxel_volume_mm3 = np.prod(self.spacing)
        
        # Load mask if provided
        self.mask = None
        if mask_path and mask_path.exists():
            mask_img = nib.load(str(mask_path))
            self.mask = mask_img.get_fdata().astype(np.uint8)
        
        logger.info(f"Loaded volume: {self.volume.shape}, spacing: {self.spacing}")
    
    def compute_volumetric_metrics(self) -> VolumetricMetrics:
        """Compute volumetric measurements."""
        if self.mask is None:
            # Generate simple threshold-based mask
            self.mask = self._generate_threshold_mask()
        
        # Calculate total sinus volume
        total_voxels = self.mask.sum()
        total_volume_ml = total_voxels * self.voxel_volume_mm3 / 1000
        
        # Separate air vs soft tissue within mask
        masked_volume = self.volume[self.mask > 0]
        air_voxels = (masked_volume < -400).sum()
        soft_tissue_voxels = (masked_volume >= -400).sum()
        
        air_volume_ml = air_voxels * self.voxel_volume_mm3 / 1000
        soft_tissue_volume_ml = soft_tissue_voxels * self.voxel_volume_mm3 / 1000
        air_fraction = air_voxels / total_voxels if total_voxels > 0 else 0
        
        metrics = VolumetricMetrics(
            total_sinus_volume_ml=total_volume_ml,
            air_volume_ml=air_volume_ml,
            soft_tissue_volume_ml=soft_tissue_volume_ml,
            air_fraction=air_fraction,
        )
        
        # If mask has multiple labels, compute per-sinus volumes
        if self.mask.max() > 1:
            metrics = self._compute_per_sinus_volumes(metrics)
        
        logger.info(f"Volumetric analysis: {air_volume_ml:.2f} mL air, {soft_tissue_volume_ml:.2f} mL tissue")
        return metrics
    
    def _generate_threshold_mask(self) -> np.ndarray:
        """Generate simple threshold-based sinus mask."""
        # Threshold for air cavities
        air_mask = self.volume < -400
        
        # Clean up with morphological operations
        air_mask = ndimage.binary_opening(air_mask, structure=np.ones((3, 3, 3)))
        air_mask = ndimage.binary_closing(air_mask, structure=np.ones((5, 5, 5)))
        
        # Keep only large components (remove trachea, external air)
        labeled, num_features = ndimage.label(air_mask)
        
        # Find components in central region (likely sinuses)
        center_z = self.volume.shape[0] // 2
        center_y = self.volume.shape[1] // 2
        center_x = self.volume.shape[2] // 2
        
        sinus_mask = np.zeros_like(air_mask, dtype=np.uint8)
        for i in range(1, num_features + 1):
            component = (labeled == i)
            
            # Check if component overlaps with central region
            central_region = component[
                max(0, center_z - 50):min(self.volume.shape[0], center_z + 50),
                max(0, center_y - 50):min(self.volume.shape[1], center_y + 50),
                max(0, center_x - 80):min(self.volume.shape[2], center_x + 80),
            ]
            
            if central_region.sum() > 100:  # At least 100 voxels in central region
                sinus_mask[component] = 1
        
        return sinus_mask
    
    def _compute_per_sinus_volumes(self, metrics: VolumetricMetrics) -> VolumetricMetrics:
        """Compute volume for each labeled sinus region."""
        # Assuming labels: 1=maxillary_left, 2=maxillary_right, etc.
        label_map = {
            1: "maxillary_left_ml",
            2: "maxillary_right_ml",
            3: "frontal_left_ml",
            4: "frontal_right_ml",
            5: "ethmoid_left_ml",
            6: "ethmoid_right_ml",
            7: "sphenoid_ml",
        }
        
        for label_id, attr_name in label_map.items():
            if (self.mask == label_id).any():
                volume_ml = (self.mask == label_id).sum() * self.voxel_volume_mm3 / 1000
                setattr(metrics, attr_name, volume_ml)
        
        return metrics
    
    def compute_texture_metrics(self) -> TextureMetrics | None:
        """Extract PyRadiomics texture features."""
        if self.mask is None:
            logger.warning("No mask available for radiomics extraction")
            return None
        
        try:
            from radiomics import featureextractor
            
            # Create temporary NIfTI files for PyRadiomics
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as img_tmp:
                nib.save(nib.Nifti1Image(self.volume, np.eye(4)), img_tmp.name)
                img_tmp_path = img_tmp.name
            
            with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as mask_tmp:
                nib.save(nib.Nifti1Image(self.mask, np.eye(4)), mask_tmp.name)
                mask_tmp_path = mask_tmp.name
            
            # Extract features
            extractor = featureextractor.RadiomicsFeatureExtractor()
            extractor.disableAllFeatures()
            extractor.enableFeatureClassByName('firstorder')
            extractor.enableFeatureClassByName('glcm')
            extractor.enableFeatureClassByName('glrlm')
            
            result = extractor.execute(img_tmp_path, mask_tmp_path)
            
            # Clean up temp files
            Path(img_tmp_path).unlink()
            Path(mask_tmp_path).unlink()
            
            # Extract key features
            metrics = TextureMetrics(
                mean_intensity=float(result.get("original_firstorder_Mean", 0)),
                std_intensity=float(result.get("original_firstorder_StandardDeviation", 0)),
                skewness=float(result.get("original_firstorder_Skewness", 0)),
                kurtosis=float(result.get("original_firstorder_Kurtosis", 0)),
                entropy=float(result.get("original_firstorder_Entropy", 0)),
                glcm_contrast=float(result.get("original_glcm_Contrast", 0)),
                glcm_homogeneity=float(result.get("original_glcm_Imc1", 0)),
                glcm_energy=float(result.get("original_glcm_Energy", 0)),
                glrlm_sre=float(result.get("original_glrlm_ShortRunEmphasis", 0)),
                glrlm_lre=float(result.get("original_glrlm_LongRunEmphasis", 0)),
            )
            
            logger.info("Texture analysis complete")
            return metrics
            
        except Exception as e:
            logger.error(f"PyRadiomics extraction failed: {e}")
            return None
    
    def compute_asymmetry_score(self) -> float | None:
        """
        Compute left-right asymmetry score for paired sinuses.
        
        Returns asymmetry index: 0 = perfect symmetry, higher = more asymmetric
        """
        if self.mask is None or self.mask.max() < 2:
            return None
        
        # Assuming labels 1-2 are maxillary L/R
        left_vol = (self.mask == 1).sum() * self.voxel_volume_mm3
        right_vol = (self.mask == 2).sum() * self.voxel_volume_mm3
        
        if left_vol == 0 and right_vol == 0:
            return None
        
        # Asymmetry index: absolute difference / sum
        asymmetry = abs(left_vol - right_vol) / (left_vol + right_vol)
        
        logger.info(f"Asymmetry score: {asymmetry:.3f}")
        return asymmetry
    
    def generate_report(
        self,
        patient_id: str = "unknown",
        study_date: str = "unknown",
    ) -> AnalysisReport:
        """Generate comprehensive analysis report."""
        logger.info("Generating comprehensive analysis report...")
        
        volumetric = self.compute_volumetric_metrics()
        texture = self.compute_texture_metrics()
        asymmetry = self.compute_asymmetry_score()
        
        metadata = {
            "image_path": str(self.image_path),
            "mask_path": str(self.mask_path) if self.mask_path else None,
            "volume_shape": list(self.volume.shape),
            "spacing_mm": list(self.spacing),
        }
        
        report = AnalysisReport(
            patient_id=patient_id,
            study_date=study_date,
            volumetric=volumetric,
            texture=texture,
            asymmetry_score=asymmetry,
            metadata=metadata,
        )
        
        return report


def compare_longitudinal(
    reports: List[AnalysisReport],
) -> Dict:
    """Compare multiple timepoint reports to detect changes."""
    if len(reports) < 2:
        return {"error": "Need at least 2 timepoints for comparison"}
    
    # Sort by study date
    reports = sorted(reports, key=lambda r: r.study_date)
    
    changes = {
        "baseline": reports[0].study_date,
        "latest": reports[-1].study_date,
        "air_volume_change_ml": reports[-1].volumetric.air_volume_ml - reports[0].volumetric.air_volume_ml,
        "air_volume_change_pct": (
            (reports[-1].volumetric.air_volume_ml - reports[0].volumetric.air_volume_ml) /
            reports[0].volumetric.air_volume_ml * 100
            if reports[0].volumetric.air_volume_ml > 0 else 0
        ),
        "tissue_volume_change_ml": (
            reports[-1].volumetric.soft_tissue_volume_ml - reports[0].volumetric.soft_tissue_volume_ml
        ),
    }
    
    # Track air fraction trend
    air_fractions = [r.volumetric.air_fraction for r in reports]
    changes["air_fraction_trend"] = "improving" if air_fractions[-1] > air_fractions[0] else "worsening"
    
    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantitative sinus CT analysis")
    parser.add_argument("--image", type=Path, required=True, help="Path to CT NIfTI volume")
    parser.add_argument("--mask", type=Path, help="Optional segmentation mask")
    parser.add_argument("--output", type=Path, help="Output JSON path for report")
    parser.add_argument("--patient-id", default="unknown", help="Patient identifier")
    parser.add_argument("--study-date", default="unknown", help="Study date")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    # Run analysis
    analyzer = SinusAnalyzer(args.image, args.mask)
    report = analyzer.generate_report(args.patient_id, args.study_date)
    
    # Convert to dict for JSON serialization
    def _to_serializable(obj):
        """Convert numpy types to native Python types for JSON."""
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: _to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_to_serializable(item) for item in obj]
        return obj
    
    report_dict = {
        "patient_id": report.patient_id,
        "study_date": report.study_date,
        "volumetric": _to_serializable(asdict(report.volumetric)),
        "texture": _to_serializable(asdict(report.texture)) if report.texture else None,
        "asymmetry_score": _to_serializable(report.asymmetry_score),
        "metadata": _to_serializable(report.metadata),
    }
    
    # Print summary
    print("\n" + "="*60)
    print("QUANTITATIVE ANALYSIS REPORT")
    print("="*60)
    print(f"Patient ID: {report.patient_id}")
    print(f"Study Date: {report.study_date}")
    print(f"\nVolumetric Metrics:")
    print(f"  Total sinus volume: {report.volumetric.total_sinus_volume_ml:.2f} mL")
    print(f"  Air volume: {report.volumetric.air_volume_ml:.2f} mL")
    print(f"  Soft tissue volume: {report.volumetric.soft_tissue_volume_ml:.2f} mL")
    print(f"  Air fraction: {report.volumetric.air_fraction:.1%}")
    
    if report.asymmetry_score is not None:
        print(f"\nAsymmetry Score: {report.asymmetry_score:.3f}")
    
    if report.texture:
        print(f"\nTexture Features:")
        print(f"  Mean intensity: {report.texture.mean_intensity:.2f} HU")
        print(f"  Entropy: {report.texture.entropy:.3f}")
    
    # Save to file
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report_dict, indent=2))
        logger.info(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
