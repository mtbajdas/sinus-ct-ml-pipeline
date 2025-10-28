import numpy as np
import nibabel as nib
from scipy import ndimage

nii = nib.load('data/processed/sinus_ct.nii.gz')
volume = nii.get_fdata()
spacing = nii.header.get_zooms()

z, y, x = volume.shape
oropharynx_z_start = int(z * 0.75)

print(f"Oropharynx ROI: slices {oropharynx_z_start} to {z-1}")
print(f"Total slices: {z - oropharynx_z_start}")
print()

oropharynx_roi = volume[oropharynx_z_start:, :, :]

# Check soft tissue segmentation
hu_min, hu_max = -100, 150
tissue_mask = (oropharynx_roi >= hu_min) & (oropharynx_roi <= hu_max)
tissue_mask_opened = ndimage.binary_opening(tissue_mask, structure=np.ones((3, 3, 3)))

print("Tissue segmentation (-100 to 150 HU):")
print(f"  Before morphological opening: {tissue_mask.sum()} voxels")
print(f"  After opening: {tissue_mask_opened.sum()} voxels")
print(f"  Volume: {tissue_mask_opened.sum() * np.prod(spacing) / 1000:.1f} mL")
print()

# Check airway
airway_mask = oropharynx_roi < -200
print(f"Airway (<-200 HU): {airway_mask.sum()} voxels")
print(f"  Volume: {airway_mask.sum() * np.prod(spacing) / 1000:.1f} mL")
print()

# Find slice with max tissue
tissue_per_slice = tissue_mask_opened.sum(axis=(1, 2))
max_slice_idx = np.argmax(tissue_per_slice)
max_slice_abs = oropharynx_z_start + max_slice_idx

print(f"Slice with maximum tissue:")
print(f"  Relative index: {max_slice_idx}")
print(f"  Absolute z: {max_slice_abs} ({max_slice_abs/z*100:.0f}%)")
print(f"  Tissue voxels: {tissue_per_slice[max_slice_idx]}")
print()

# Analyze this slice
max_slice = volume[max_slice_abs, :, :]
print(f"Slice {max_slice_abs} statistics:")
print(f"  Mean HU: {max_slice.mean():.1f}")
print(f"  Air (<-200): {100*(max_slice < -200).sum()/max_slice.size:.1f}%")
print(f"  Soft tissue (-100 to 150): {100*((max_slice > -100) & (max_slice < 150)).sum()/max_slice.size:.1f}%")
print()

# Check lateral distribution
tissue_slice = tissue_mask_opened[max_slice_idx, :, :]
x_coords = np.argwhere(tissue_slice)[:, 1] if tissue_slice.sum() > 0 else []

if len(x_coords) > 0:
    print(f"Tissue lateral extent:")
    print(f"  X range: {x_coords.min()} to {x_coords.max()} (span: {x_coords.max() - x_coords.min()} voxels = {(x_coords.max() - x_coords.min())*spacing[2]:.1f} mm)")
    print(f"  Midline: {x // 2}")
    print()
    print(f"⚠️  Span of {(x_coords.max() - x_coords.min())*spacing[2]:.1f} mm suggests segmentation is too broad")
    print(f"   Likely including jaw/mandible, not just tonsils")
print()

# Check if we're at the right anatomical level
print("ANATOMICAL CHECK:")
print("  Expected at this level (75-95% inferior):")
print("    - Oropharynx (throat)")
print("    - Palatine tonsils (small paired structures)")
print("    - Open airway (~20-40mm diameter)")
print()
print("  Issue: Segmentation is catching entire mandible/jaw")
print("  Solution: Need tighter anatomical constraints")
