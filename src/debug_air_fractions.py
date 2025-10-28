"""
Debug air fractions and skull base measurements for deep sinuses.
"""
import numpy as np
import nibabel as nib
from scipy import ndimage

# Load the processed NIfTI
nii = nib.load('data/processed/sinus_ct.nii.gz')
volume = nii.get_fdata()
spacing = nii.header.get_zooms()

print(f"Volume shape: {volume.shape}")
print(f"Spacing (mm): {spacing}")
print(f"HU range: [{volume.min():.1f}, {volume.max():.1f}]")
print()

# Test sphenoid ROI
z, y, x = volume.shape
z_start = int(z * 0.30)
z_end = int(z * 0.50)
y_start = int(y * 0.60)
y_end = int(y * 0.85)
x_center = x // 2
x_margin = int(x * 0.2)
x_start = x_center - x_margin
x_end = x_center + x_margin

sphenoid_roi = volume[z_start:z_end, y_start:y_end, x_start:x_end]
print(f"SPHENOID ROI:")
print(f"  Slices z={z_start}-{z_end} ({z_start*spacing[0]:.1f}-{z_end*spacing[0]:.1f} mm)")
print(f"  Shape: {sphenoid_roi.shape}")
print(f"  HU stats: mean={sphenoid_roi.mean():.1f}, median={np.median(sphenoid_roi):.1f}")
print()

# Check air before and after morphological opening
air_threshold = -400
air_mask_raw = sphenoid_roi < air_threshold
air_mask_opened = ndimage.binary_opening(air_mask_raw, structure=np.ones((3, 3, 3)))

air_fraction_raw = air_mask_raw.sum() / sphenoid_roi.size
air_fraction_opened = air_mask_opened.sum() / sphenoid_roi.size

print(f"  Air detection (<{air_threshold} HU):")
print(f"    Before morphological opening: {air_mask_raw.sum()} voxels ({air_fraction_raw*100:.1f}%)")
print(f"    After morphological opening:  {air_mask_opened.sum()} voxels ({air_fraction_opened*100:.1f}%)")
print(f"    Voxels removed by opening: {air_mask_raw.sum() - air_mask_opened.sum()}")
print()

# Check HU distribution in sphenoid ROI
hu_bins = [-1000, -500, -400, -200, 0, 100, 200, 500, 1000, 2000]
hist, _ = np.histogram(sphenoid_roi, bins=hu_bins)
print(f"  HU distribution in sphenoid ROI:")
for i in range(len(hu_bins)-1):
    pct = 100 * hist[i] / sphenoid_roi.size
    print(f"    {hu_bins[i]:5d} to {hu_bins[i+1]:5d} HU: {hist[i]:6d} voxels ({pct:5.1f}%)")
print()

# Check if sphenoid is actually opacified (should have soft tissue, not air)
soft_tissue_mask = (sphenoid_roi > -100) & (sphenoid_roi < 100)
soft_tissue_fraction = soft_tissue_mask.sum() / sphenoid_roi.size
print(f"  Soft tissue content (-100 to +100 HU): {soft_tissue_fraction*100:.1f}%")
print(f"  → This confirms Complete opacification (filled with mucus/tissue)" if soft_tissue_fraction > 0.8 else "")
print()

# Test posterior ethmoid ROI
z_start_pe = int(z * 0.20)
z_end_pe = int(z * 0.45)
y_start_pe = int(y * 0.40)
y_end_pe = int(y * 0.75)
x_margin_pe = int(x * 0.10)

left_roi = volume[z_start_pe:z_end_pe, y_start_pe:y_end_pe, x_center-x_margin_pe-10:x_center-10]
right_roi = volume[z_start_pe:z_end_pe, y_start_pe:y_end_pe, x_center+10:x_center+x_margin_pe+10]

print(f"POSTERIOR ETHMOID ROI:")
print(f"  Slices z={z_start_pe}-{z_end_pe} ({z_start_pe*spacing[0]:.1f}-{z_end_pe*spacing[0]:.1f} mm)")
print(f"  Left shape: {left_roi.shape}, Right shape: {right_roi.shape}")
print()

left_air_raw = (left_roi < air_threshold)
left_air_opened = ndimage.binary_opening(left_air_raw, structure=np.ones((2, 2, 2)))
right_air_raw = (right_roi < air_threshold)
right_air_opened = ndimage.binary_opening(right_air_raw, structure=np.ones((2, 2, 2)))

total_roi_size = left_roi.size + right_roi.size
total_air_raw = left_air_raw.sum() + right_air_raw.sum()
total_air_opened = left_air_opened.sum() + right_air_opened.sum()

print(f"  Air detection (<{air_threshold} HU):")
print(f"    Before opening: {total_air_raw} voxels ({100*total_air_raw/total_roi_size:.1f}%)")
print(f"    After opening:  {total_air_opened} voxels ({100*total_air_opened/total_roi_size:.1f}%)")
print(f"    Voxels removed: {total_air_raw - total_air_opened}")
print()

# Check soft tissue in posterior ethmoid
left_soft = ((left_roi > -100) & (left_roi < 100)).sum()
right_soft = ((right_roi > -100) & (right_roi < 100)).sum()
total_soft = left_soft + right_soft
print(f"  Soft tissue content: {total_soft} voxels ({100*total_soft/total_roi_size:.1f}%)")
print()

# Test skull base ROI
z_skull_base = int(z * 0.25)
z_band_thickness = 15

skull_base_roi = volume[
    z_skull_base:z_skull_base+z_band_thickness,
    int(y*0.55):int(y*0.85),
    int(x*0.30):int(x*0.70),
]

print(f"SKULL BASE ROI:")
print(f"  Slices z={z_skull_base}-{z_skull_base+z_band_thickness} ({z_skull_base*spacing[0]:.1f}-{(z_skull_base+z_band_thickness)*spacing[0]:.1f} mm)")
print(f"  Shape: {skull_base_roi.shape}")
print(f"  HU stats: mean={skull_base_roi.mean():.1f}, median={np.median(skull_base_roi):.1f}")
print()

bone_threshold = 200
bone_mask = skull_base_roi > bone_threshold
bone_fraction = bone_mask.sum() / skull_base_roi.size

print(f"  Bone detection (>{bone_threshold} HU):")
print(f"    Bone voxels: {bone_mask.sum()} ({bone_fraction*100:.1f}%)")
print()

# Analyze thickness measurements
thicknesses = []
thicknesses_unfiltered = []
for y_idx in range(skull_base_roi.shape[1]):
    for x_idx in range(skull_base_roi.shape[2]):
        column = bone_mask[:, y_idx, x_idx]
        
        if column.sum() > 0:
            # Count consecutive bone runs
            runs = []
            current_run = 0
            for val in column:
                if val:
                    current_run += 1
                else:
                    if current_run > 0:
                        runs.append(current_run)
                    current_run = 0
            if current_run > 0:
                runs.append(current_run)
            
            if runs:
                max_run_voxels = max(runs)
                thickness_mm = max_run_voxels * spacing[0]
                thicknesses_unfiltered.append(thickness_mm)
                
                # Apply filter: require at least 2 consecutive voxels
                if max_run_voxels >= 2:
                    thicknesses.append(thickness_mm)

if thicknesses:
    thicknesses = np.array(thicknesses)
    print(f"  Thickness measurements:")
    print(f"    Min: {thicknesses.min():.2f} mm ({int(thicknesses.min()/spacing[0])} voxels)")
    print(f"    Mean: {thicknesses.mean():.2f} mm")
    print(f"    Max: {thicknesses.max():.2f} mm")
    print(f"    10th percentile: {np.percentile(thicknesses, 10):.2f} mm")
    print(f"    90th percentile: {np.percentile(thicknesses, 90):.2f} mm")
    
    # Count how many measurements are only 1 voxel
    one_voxel_count = (thicknesses < spacing[0] * 1.5).sum()
    print(f"    Single-voxel measurements (< {spacing[0]*1.5:.2f} mm): {one_voxel_count} ({100*one_voxel_count/len(thicknesses):.1f}%)")
    
    if one_voxel_count > len(thicknesses) * 0.01:  # More than 1%
        print(f"    ⚠️  Many single-voxel measurements suggest possible artifacts or truly thin bone")
