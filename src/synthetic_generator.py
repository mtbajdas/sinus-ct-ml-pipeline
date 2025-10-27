"""
Generate synthetic sinus CT volumes with controlled pathology for ML training.

This module creates realistic training data by:
1. Starting from normal sinus anatomy templates
2. Adding controlled mucosal thickening patterns
3. Simulating air-fluid levels and opacification
4. Generating corresponding ground-truth masks
"""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import nibabel as nib
import numpy as np
from scipy import ndimage
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)


@dataclass
class SinusRegion:
    """Define anatomical sinus regions for targeted pathology simulation."""
    name: str
    center: Tuple[int, int, int]
    radius: Tuple[int, int, int]
    
    
class SyntheticSinusGenerator:
    """Generate synthetic sinus CT volumes with realistic pathology patterns."""
    
    def __init__(
        self,
        base_shape: Tuple[int, int, int] = (192, 256, 256),
        spacing: Tuple[float, float, float] = (1.0, 0.5, 0.5),
        seed: int | None = None,
    ):
        self.base_shape = base_shape
        self.spacing = spacing
        if seed is not None:
            np.random.seed(seed)
        
        # Define typical sinus locations (relative to volume center)
        self.sinus_regions = self._initialize_sinus_regions()
        
    def _initialize_sinus_regions(self) -> list[SinusRegion]:
        """Initialize anatomical sinus regions based on typical CT anatomy."""
        mid_z, mid_y, mid_x = [s // 2 for s in self.base_shape]
        
        return [
            # Maxillary sinuses (largest, lateral to nasal cavity)
            SinusRegion("maxillary_left", (mid_z, mid_y, mid_x - 40), (30, 35, 25)),
            SinusRegion("maxillary_right", (mid_z, mid_y, mid_x + 40), (30, 35, 25)),
            
            # Frontal sinuses (superior, smaller)
            SinusRegion("frontal_left", (mid_z - 50, mid_y + 30, mid_x - 10), (20, 20, 15)),
            SinusRegion("frontal_right", (mid_z - 50, mid_y + 30, mid_x + 10), (20, 20, 15)),
            
            # Ethmoid air cells (medial, complex structure)
            SinusRegion("ethmoid_left", (mid_z - 20, mid_y + 10, mid_x - 15), (25, 20, 12)),
            SinusRegion("ethmoid_right", (mid_z - 20, mid_y + 10, mid_x + 15), (25, 20, 12)),
            
            # Sphenoid sinuses (posterior, central)
            SinusRegion("sphenoid", (mid_z - 10, mid_y - 20, mid_x), (20, 20, 20)),
        ]
    
    def generate_base_anatomy(self) -> np.ndarray:
        """
        Create base CT volume with typical head anatomy.
        
        Returns:
            volume: Base CT with skull, soft tissue, and air cavities in HU.
        """
        volume = np.zeros(self.base_shape, dtype=np.float32)
        
        # Create skull (outer shell ~500-1000 HU for cortical bone)
        z, y, x = np.ogrid[:self.base_shape[0], :self.base_shape[1], :self.base_shape[2]]
        center_z, center_y, center_x = [s // 2 for s in self.base_shape]
        
        # Ellipsoid skull
        skull_mask = (
            ((z - center_z) / (self.base_shape[0] * 0.4)) ** 2 +
            ((y - center_y) / (self.base_shape[1] * 0.4)) ** 2 +
            ((x - center_x) / (self.base_shape[2] * 0.4)) ** 2
        ) <= 1.0
        
        # Inner brain/soft tissue region
        brain_mask = (
            ((z - center_z) / (self.base_shape[0] * 0.35)) ** 2 +
            ((y - center_y) / (self.base_shape[1] * 0.35)) ** 2 +
            ((x - center_x) / (self.base_shape[2] * 0.35)) ** 2
        ) <= 1.0
        
        # Set intensities
        volume[skull_mask] = 800 + np.random.normal(0, 100, size=volume[skull_mask].shape)  # Bone
        volume[brain_mask] = 30 + np.random.normal(0, 10, size=volume[brain_mask].shape)  # Brain tissue
        
        # Add nasal cavity (central air space ~-1000 HU)
        nasal_cavity = (
            (z > center_z - 10) & (z < center_z + 60) &
            (y > center_y - 10) & (y < center_y + 40) &
            (x > center_x - 20) & (x < center_x + 20)
        )
        volume[nasal_cavity] = -900 + np.random.normal(0, 50, size=volume[nasal_cavity].shape)
        
        # Create sinus air cavities
        for region in self.sinus_regions:
            mask = self._create_ellipsoid_mask(region.center, region.radius)
            volume[mask] = -950 + np.random.normal(0, 30, size=volume[mask].shape)
        
        # Smooth to simulate partial volume effects
        volume = gaussian_filter(volume, sigma=1.0)
        
        return volume
    
    def _create_ellipsoid_mask(
        self,
        center: Tuple[int, int, int],
        radius: Tuple[int, int, int],
    ) -> np.ndarray:
        """Create ellipsoid mask for a given center and radii."""
        z, y, x = np.ogrid[:self.base_shape[0], :self.base_shape[1], :self.base_shape[2]]
        mask = (
            ((z - center[0]) / radius[0]) ** 2 +
            ((y - center[1]) / radius[1]) ** 2 +
            ((x - center[2]) / radius[2]) ** 2
        ) <= 1.0
        return mask
    
    def add_mucosal_thickening(
        self,
        volume: np.ndarray,
        thickness_mm: float = 3.0,
        affected_sinuses: list[str] | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate mucosal thickening in specified sinuses.
        
        Args:
            volume: Base CT volume
            thickness_mm: Mucosal thickness in mm
            affected_sinuses: List of sinus names to affect (None = all)
        
        Returns:
            modified_volume: CT with mucosal thickening
            mucosa_mask: Binary mask of thickened mucosa
        """
        modified = volume.copy()
        mucosa_mask = np.zeros(self.base_shape, dtype=np.uint8)
        
        # Select sinuses to affect
        if affected_sinuses is None:
            regions_to_modify = self.sinus_regions
        else:
            regions_to_modify = [r for r in self.sinus_regions if r.name in affected_sinuses]
        
        for region in regions_to_modify:
            # Get sinus air cavity
            sinus_mask = self._create_ellipsoid_mask(region.center, region.radius)
            
            # Create mucosal layer by eroding air cavity
            thickness_voxels = int(thickness_mm / np.mean(self.spacing))
            eroded = ndimage.binary_erosion(sinus_mask, iterations=thickness_voxels)
            mucosa_region = sinus_mask & ~eroded
            
            # Set mucosal intensity (soft tissue density ~30-60 HU)
            modified[mucosa_region] = 40 + np.random.normal(0, 10, size=modified[mucosa_region].shape)
            mucosa_mask[mucosa_region] = 1
            
        return modified, mucosa_mask
    
    def add_fluid_level(
        self,
        volume: np.ndarray,
        sinus_name: str,
        fill_fraction: float = 0.5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate air-fluid level in specified sinus.
        
        Args:
            volume: Base CT volume
            sinus_name: Name of sinus to add fluid
            fill_fraction: Fraction of sinus to fill (0-1)
        
        Returns:
            modified_volume: CT with fluid level
            fluid_mask: Binary mask of fluid region
        """
        modified = volume.copy()
        fluid_mask = np.zeros(self.base_shape, dtype=np.uint8)
        
        # Find target sinus
        region = next((r for r in self.sinus_regions if r.name == sinus_name), None)
        if region is None:
            raise ValueError(f"Unknown sinus: {sinus_name}")
        
        # Get sinus mask
        sinus_mask = self._create_ellipsoid_mask(region.center, region.radius)
        
        # Create horizontal fluid level (fill from bottom)
        z_coords = np.where(sinus_mask)[0]
        z_min, z_max = z_coords.min(), z_coords.max()
        fluid_height = z_min + int((z_max - z_min) * fill_fraction)
        
        fluid_region = sinus_mask & (np.arange(self.base_shape[0])[:, None, None] >= fluid_height)
        
        # Set fluid intensity (water/mucus ~0-20 HU)
        modified[fluid_region] = 10 + np.random.normal(0, 5, size=modified[fluid_region].shape)
        fluid_mask[fluid_region] = 1
        
        return modified, fluid_mask
    
    def add_complete_opacification(
        self,
        volume: np.ndarray,
        sinus_name: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate complete sinus opacification (chronic sinusitis).
        
        Args:
            volume: Base CT volume
            sinus_name: Name of sinus to opacify
        
        Returns:
            modified_volume: CT with opacification
            opacity_mask: Binary mask of opacified region
        """
        modified = volume.copy()
        opacity_mask = np.zeros(self.base_shape, dtype=np.uint8)
        
        region = next((r for r in self.sinus_regions if r.name == sinus_name), None)
        if region is None:
            raise ValueError(f"Unknown sinus: {sinus_name}")
        
        sinus_mask = self._create_ellipsoid_mask(region.center, region.radius)
        
        # Fill entire sinus with soft tissue density
        modified[sinus_mask] = 35 + np.random.normal(0, 15, size=modified[sinus_mask].shape)
        opacity_mask[sinus_mask] = 1
        
        return modified, opacity_mask
    
    def generate_training_sample(
        self,
        pathology: str = "normal",
        severity: str = "mild",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a complete training sample with specified pathology.
        
        Args:
            pathology: Type of pathology ("normal", "mucosal", "fluid", "opacified")
            severity: Severity level ("mild", "moderate", "severe")
        
        Returns:
            volume: CT volume in HU
            mask: Binary segmentation mask
        """
        # Generate base anatomy
        volume = self.generate_base_anatomy()
        mask = np.zeros(self.base_shape, dtype=np.uint8)
        
        if pathology == "normal":
            # Mark all sinus air spaces
            for region in self.sinus_regions:
                sinus_mask = self._create_ellipsoid_mask(region.center, region.radius)
                mask[sinus_mask] = 1
        
        elif pathology == "mucosal":
            # Mucosal thickening
            thickness_map = {"mild": 2.0, "moderate": 4.0, "severe": 8.0}
            thickness = thickness_map.get(severity, 3.0)
            
            # Randomly select 2-4 sinuses to affect
            num_affected = np.random.randint(2, 5)
            affected = np.random.choice([r.name for r in self.sinus_regions], num_affected, replace=False)
            
            volume, mucosa_mask = self.add_mucosal_thickening(volume, thickness, affected.tolist())
            mask[mucosa_mask > 0] = 1
        
        elif pathology == "fluid":
            # Air-fluid levels
            fill_map = {"mild": 0.3, "moderate": 0.6, "severe": 0.9}
            fill_fraction = fill_map.get(severity, 0.5)
            
            # Add fluid to 1-2 sinuses
            affected = np.random.choice([r.name for r in self.sinus_regions[:4]], np.random.randint(1, 3), replace=False)
            for sinus_name in affected:
                volume, fluid_mask = self.add_fluid_level(volume, sinus_name, fill_fraction)
                mask[fluid_mask > 0] = 1
        
        elif pathology == "opacified":
            # Complete opacification of 1-3 sinuses
            num_affected = {"mild": 1, "moderate": 2, "severe": 3}.get(severity, 1)
            affected = np.random.choice([r.name for r in self.sinus_regions], num_affected, replace=False)
            
            for sinus_name in affected:
                volume, opacity_mask = self.add_complete_opacification(volume, sinus_name)
                mask[opacity_mask > 0] = 1
        
        return volume, mask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic sinus CT training data")
    parser.add_argument("--output-dir", type=Path, default=Path("data/synthetic"), help="Output directory")
    parser.add_argument("--num-samples", type=int, default=10, help="Number of samples to generate")
    parser.add_argument(
        "--pathology",
        choices=["normal", "mucosal", "fluid", "opacified", "mixed"],
        default="mixed",
        help="Pathology type (mixed = random)",
    )
    parser.add_argument(
        "--severity",
        choices=["mild", "moderate", "severe", "mixed"],
        default="mixed",
        help="Severity level (mixed = random)",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    # Create output directories
    image_dir = args.output_dir / "images"
    mask_dir = args.output_dir / "masks"
    image_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize generator
    generator = SyntheticSinusGenerator(seed=args.seed)
    
    pathology_types = ["normal", "mucosal", "fluid", "opacified"]
    severity_levels = ["mild", "moderate", "severe"]
    
    logger.info(f"Generating {args.num_samples} synthetic samples...")
    
    for i in range(args.num_samples):
        # Select pathology and severity
        if args.pathology == "mixed":
            pathology = np.random.choice(pathology_types)
        else:
            pathology = args.pathology
        
        if args.severity == "mixed":
            severity = np.random.choice(severity_levels)
        else:
            severity = args.severity
        
        # Generate sample
        volume, mask = generator.generate_training_sample(pathology, severity)
        
        # Save as NIfTI
        affine = np.diag(list(generator.spacing) + [1.0])
        
        image_path = image_dir / f"sample_{i:03d}_{pathology}_{severity}.nii.gz"
        mask_path = mask_dir / f"sample_{i:03d}_{pathology}_{severity}.nii.gz"
        
        nib.save(nib.Nifti1Image(volume, affine), str(image_path))
        nib.save(nib.Nifti1Image(mask.astype(np.uint8), affine), str(mask_path))
        
        logger.info(f"Generated sample {i+1}/{args.num_samples}: {pathology} ({severity})")
    
    logger.info(f"Synthetic data generation complete. Output: {args.output_dir}")


if __name__ == "__main__":
    main()
