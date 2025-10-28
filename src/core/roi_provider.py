"""
Abstract interface for ROI (Region of Interest) placement strategies.

This allows plug-and-play switching between:
- Manual percentage-based ROIs (current)
- TotalSegmentator deep learning
- Atlas-based registration
- Landmark-based placement
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np


class ROIProvider(ABC):
    """Abstract base class for ROI placement strategies."""
    
    @abstractmethod
    def get_roi_mask(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[np.ndarray]:
        """
        Get binary mask for a specific anatomical structure.
        
        Args:
            volume: CT volume (z, y, x)
            spacing: Voxel spacing in mm (z, y, x)
            structure_name: Anatomical structure identifier
                Examples: 'sphenoid', 'maxillary_left', 'temporal_bone_right'
        
        Returns:
            Binary mask (same shape as volume) or None if structure not available
        """
        pass
    
    @abstractmethod
    def get_available_structures(self) -> list[str]:
        """Return list of all anatomical structures this provider can segment."""
        pass
    
    @abstractmethod
    def get_roi_bounds(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[Tuple[slice, slice, slice]]:
        """
        Get bounding box for an ROI (useful for cropping before analysis).
        
        Returns:
            Tuple of (z_slice, y_slice, x_slice) or None if structure not available
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging/debugging."""
        pass


class ManualROIProvider(ROIProvider):
    """
    Current percentage-based ROI placement using anatomical heuristics.
    
    This is the existing implementation - fast but requires tuning per scan type.
    """
    
    def __init__(self, air_threshold: float = -400.0):
        self.air_threshold = air_threshold
        self._structure_map = {
            'sphenoid': self._get_sphenoid_roi,
            'sphenoid_left': self._get_sphenoid_roi,
            'sphenoid_right': self._get_sphenoid_roi,
            'posterior_ethmoid': self._get_posterior_ethmoid_roi,
            'posterior_ethmoid_left': self._get_posterior_ethmoid_roi,
            'posterior_ethmoid_right': self._get_posterior_ethmoid_roi,
            'skull_base': self._get_skull_base_roi,
        }
    
    def get_roi_mask(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[np.ndarray]:
        """Generate ROI mask using percentage-based bounds."""
        if structure_name not in self._structure_map:
            return None
        
        bounds = self.get_roi_bounds(volume, spacing, structure_name)
        if bounds is None:
            return None
        
        mask = np.zeros_like(volume, dtype=bool)
        mask[bounds] = True
        return mask
    
    def get_roi_bounds(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[Tuple[slice, slice, slice]]:
        """Get ROI bounding box using anatomical heuristics."""
        if structure_name not in self._structure_map:
            return None
        
        return self._structure_map[structure_name](volume.shape)
    
    def get_available_structures(self) -> list[str]:
        return list(self._structure_map.keys())
    
    @property
    def name(self) -> str:
        return "ManualROIProvider"
    
    def _get_sphenoid_roi(self, shape: Tuple[int, int, int]) -> Tuple[slice, slice, slice]:
        """Current sphenoid ROI logic."""
        z, y, x = shape
        z_start = int(z * 0.30)
        z_end = int(z * 0.50)
        y_start = int(y * 0.35)
        y_end = int(y * 0.55)
        x_center = x // 2
        x_margin = int(x * 0.2)
        x_start = x_center - x_margin
        x_end = x_center + x_margin
        
        return (slice(z_start, z_end), slice(y_start, y_end), slice(x_start, x_end))
    
    def _get_posterior_ethmoid_roi(self, shape: Tuple[int, int, int]) -> Tuple[slice, slice, slice]:
        """Current posterior ethmoid ROI logic."""
        z, y, x = shape
        z_start = int(z * 0.20)
        z_end = int(z * 0.45)
        y_start = int(y * 0.40)
        y_end = int(y * 0.75)
        
        # Return full x-range; caller can split left/right
        return (slice(z_start, z_end), slice(y_start, y_end), slice(None))
    
    def _get_skull_base_roi(self, shape: Tuple[int, int, int]) -> Tuple[slice, slice, slice]:
        """Current skull base ROI logic."""
        z, y, x = shape
        z_skull_base = int(z * 0.25)
        z_band_thickness = 15
        
        return (
            slice(z_skull_base, z_skull_base + z_band_thickness),
            slice(int(y * 0.30), int(y * 0.55)),
            slice(int(x * 0.30), int(x * 0.70))
        )


class TotalSegmentatorROIProvider(ROIProvider):
    """
    ROI provider using TotalSegmentator deep learning model.
    
    Supports 104 anatomical structures out of the box.
    Requires: pip install totalsegmentator
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        fast_mode: bool = True,
        device: str = "cpu",
    ):
        """
        Args:
            cache_dir: Directory to cache segmentations (avoids re-running)
            fast_mode: Use faster but slightly less accurate model
            device: 'cpu' or 'cuda' for GPU acceleration
        """
        self.cache_dir = cache_dir or Path("data/segmentations")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fast_mode = fast_mode
        self.device = device
        
        # Map our structure names to TotalSegmentator output names
        self._name_mapping = {
            # Sinuses
            'sphenoid': 'sphenoid_sinus',
            'sphenoid_left': 'sphenoid_sinus_left',
            'sphenoid_right': 'sphenoid_sinus_right',
            'maxillary_left': 'maxillary_sinus_left',
            'maxillary_right': 'maxillary_sinus_right',
            'frontal_left': 'frontal_sinus_left',
            'frontal_right': 'frontal_sinus_right',
            
            # Ethmoid (TotalSegmentator groups as single structure)
            'ethmoid_left': 'ethmoid_sinus_left',
            'ethmoid_right': 'ethmoid_sinus_right',
            
            # Skull/Bone
            'skull': 'skull',
            'mandible': 'mandible',
            'maxilla': 'maxilla',
            'temporal_bone_left': 'temporal_bone_left',
            'temporal_bone_right': 'temporal_bone_right',
            
            # Brain structures (if scan includes them)
            'brain': 'brain',
            'brainstem': 'brainstem',
            'pituitary_gland': 'pituitary_gland',
            
            # Airway
            'trachea': 'trachea',
            
            # Vessels (useful for avoiding false positives)
            'carotid_artery_left': 'carotid_artery_left',
            'carotid_artery_right': 'carotid_artery_right',
        }
        
        self._cached_masks: Dict[str, np.ndarray] = {}
        self._volume_hash: Optional[str] = None
    
    def get_roi_mask(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[np.ndarray]:
        """Get segmentation mask from TotalSegmentator."""
        # Check if we need to re-run segmentation (new volume)
        current_hash = self._hash_volume(volume)
        if current_hash != self._volume_hash:
            self._run_segmentation(volume, spacing)
            self._volume_hash = current_hash
        
        # Look up structure name
        totalseg_name = self._name_mapping.get(structure_name)
        if totalseg_name is None:
            return None
        
        return self._cached_masks.get(totalseg_name)
    
    def get_roi_bounds(
        self,
        volume: np.ndarray,
        spacing: Tuple[float, float, float],
        structure_name: str,
    ) -> Optional[Tuple[slice, slice, slice]]:
        """Get bounding box from segmentation mask."""
        mask = self.get_roi_mask(volume, spacing, structure_name)
        if mask is None or mask.sum() == 0:
            return None
        
        # Find bounding box
        coords = np.argwhere(mask)
        z_min, y_min, x_min = coords.min(axis=0)
        z_max, y_max, x_max = coords.max(axis=0)
        
        return (
            slice(z_min, z_max + 1),
            slice(y_min, y_max + 1),
            slice(x_min, x_max + 1)
        )
    
    def get_available_structures(self) -> list[str]:
        return list(self._name_mapping.keys())
    
    @property
    def name(self) -> str:
        return f"TotalSegmentatorROIProvider(fast={self.fast_mode})"
    
    def _hash_volume(self, volume: np.ndarray) -> str:
        """Create hash of volume to detect when we need to re-segment."""
        import hashlib
        # Hash shape and a sample of voxels (faster than hashing entire volume)
        sample = volume[::10, ::10, ::10].tobytes()
        return hashlib.md5(sample).hexdigest()
    
    def _run_segmentation(self, volume: np.ndarray, spacing: Tuple[float, float, float]) -> None:
        """Run TotalSegmentator on the volume."""
        try:
            from totalsegmentator.python_api import totalsegmentator
        except ImportError:
            raise ImportError(
                "TotalSegmentator not installed. Install with: pip install totalsegmentator"
            )
        
        import nibabel as nib
        import tempfile
        
        # TotalSegmentator expects NIfTI file input
        with tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False) as tmp_input:
            input_path = Path(tmp_input.name)
            
            # Save volume as NIfTI
            nii = nib.Nifti1Image(volume, affine=np.eye(4))
            nii.header.set_zooms(spacing)
            nib.save(nii, input_path)
        
        try:
            # Run segmentation
            volume_hash = self._hash_volume(volume)
            output_dir = self.cache_dir / volume_hash
            output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"Running TotalSegmentator on {volume.shape} volume...")
            print(f"  Device: {self.device}, Fast mode: {self.fast_mode}")
            
            segmentations = totalsegmentator(
                input=str(input_path),
                output=str(output_dir),
                fast=self.fast_mode,
                device=self.device,
                quiet=False,
            )
            
            # Load all segmentation masks
            self._cached_masks.clear()
            for seg_file in output_dir.glob("*.nii.gz"):
                structure_name = seg_file.stem.replace('.nii', '')
                mask_nii = nib.load(seg_file)
                self._cached_masks[structure_name] = mask_nii.get_fdata().astype(bool)
            
            print(f"✓ Segmented {len(self._cached_masks)} structures")
            
        finally:
            # Cleanup temp file
            input_path.unlink(missing_ok=True)


def create_roi_provider(provider_type: str = "auto", **kwargs) -> ROIProvider:
    """
    Factory function to create ROI provider.
    
    Args:
        provider_type: 'manual', 'totalsegmentator', or 'auto'
            'auto' tries TotalSegmentator first, falls back to manual
        **kwargs: Provider-specific arguments
    
    Returns:
        ROIProvider instance
    """
    if provider_type == "manual":
        return ManualROIProvider(**kwargs)
    
    elif provider_type == "totalsegmentator":
        return TotalSegmentatorROIProvider(**kwargs)
    
    elif provider_type == "auto":
        # Try TotalSegmentator, fall back to manual
        try:
            import totalsegmentator
            print("Using TotalSegmentator for ROI placement")
            return TotalSegmentatorROIProvider(**kwargs)
        except ImportError:
            print("TotalSegmentator not available, using manual ROI placement")
            print("Install with: pip install totalsegmentator")
            return ManualROIProvider(**kwargs)
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
