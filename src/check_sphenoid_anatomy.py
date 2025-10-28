"""
Check sagittal view to understand sphenoid positioning.
"""
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt

nii = nib.load('data/processed/sinus_ct.nii.gz')
volume = nii.get_fdata()
z, y, x = volume.shape

# Show sagittal slice through midline to see sphenoid anatomy
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# Midline sagittal
x_mid = x // 2
sagittal_mid = volume[:, :, x_mid]

ax = axes[0]
ax.imshow(sagittal_mid.T, cmap='gray', vmin=-1000, vmax=500, origin='lower', aspect='auto')
ax.set_title(f'Midline Sagittal (x={x_mid})', fontsize=12)
ax.set_xlabel('Z (superior→inferior)')
ax.set_ylabel('Y (anterior→posterior)')

# Mark sphenoid ROI z-range
z_start = int(z * 0.30)
z_end = int(z * 0.50)
y_start = int(y * 0.45)  # More anterior
y_end = int(y * 0.70)     # Don't go too far back
ax.axvline(z_start, color='red', linestyle='--', label=f'z={z_start} (30%)')
ax.axvline(z_end, color='red', linestyle='--', label=f'z={z_end} (50%)')
ax.axhline(y_start, color='cyan', linestyle='--', label=f'y={y_start} (45%)')
ax.axhline(y_end, color='cyan', linestyle='--', label=f'y={y_end} (70%)')

# Draw ROI box
from matplotlib.patches import Rectangle
rect = Rectangle((z_start, y_start), z_end-z_start, y_end-y_start,
                linewidth=3, edgecolor='red', facecolor='none', label='Sphenoid ROI')
ax.add_patch(rect)
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Coronal slice through middle of sphenoid
z_sph = int(z * 0.40)
coronal_sph = volume[z_sph, :, :]

ax = axes[1]
ax.imshow(coronal_sph, cmap='gray', vmin=-1000, vmax=500)
ax.set_title(f'Coronal at z={z_sph} (40% - sphenoid level)', fontsize=12)
ax.set_xlabel('X (left→right)')
ax.set_ylabel('Y (anterior→posterior)')

# Mark ROI boundaries
x_center = x // 2
x_margin = int(x * 0.2)
x_start = x_center - x_margin
x_end = x_center + x_margin
ax.axvline(x_start, color='red', linestyle='--')
ax.axvline(x_end, color='red', linestyle='--')
ax.axhline(y_start, color='cyan', linestyle='--')
ax.axhline(y_end, color='cyan', linestyle='--')

rect = Rectangle((x_start, y_start), x_end-x_start, y_end-y_start,
                linewidth=3, edgecolor='red', facecolor='none')
ax.add_patch(rect)
ax.grid(True, alpha=0.3)

# HU profile through midline
z_profile = sagittal_mid[:, y // 2]  # Mid anterior-posterior
ax = axes[2]
ax.plot(range(len(z_profile)), z_profile, 'b-', linewidth=1)
ax.axhline(-400, color='green', linestyle='--', label='Air threshold')
ax.axhline(0, color='orange', linestyle='--', label='Soft tissue')
ax.axhline(200, color='brown', linestyle='--', label='Bone threshold')
ax.axvspan(z_start, z_end, alpha=0.2, color='red', label='Sphenoid ROI z-range')
ax.set_xlabel('Z index (superior→inferior)')
ax.set_ylabel('HU value')
ax.set_title('HU Profile Along Z-axis (midline)', fontsize=12)
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)
ax.set_ylim(-1200, 1000)

plt.tight_layout()
plt.savefig('docs/sphenoid_anatomy_check.png', dpi=150, bbox_inches='tight')
print("Saved to docs/sphenoid_anatomy_check.png")

# Analyze ROI contents in detail
print("\n" + "="*60)
print("DETAILED ROI ANALYSIS")
print("="*60)

sphenoid_roi = volume[z_start:z_end, y_start:y_end, x_start:x_end]
print(f"\nSphenoid ROI shape: {sphenoid_roi.shape}")
print(f"ROI boundaries:")
print(f"  Z: [{z_start}:{z_end}] = indices {z_start} to {z_end-1}")
print(f"  Y: [{y_start}:{y_end}] = posterior {100*y_start/y:.0f}% to {100*y_end/y:.0f}%")
print(f"  X: [{x_start}:{x_end}] = central ±{100*x_margin/x:.0f}%")

# HU histogram
print(f"\nHU distribution in ROI:")
bins = [-2000, -1000, -500, -400, -200, -100, 0, 100, 200, 500, 1000, 2000, 5000]
hist, _ = np.histogram(sphenoid_roi.flatten(), bins=bins)
for i in range(len(bins)-1):
    pct = 100 * hist[i] / sphenoid_roi.size
    if hist[i] > 0:
        print(f"  {bins[i]:5d} to {bins[i+1]:5d} HU: {hist[i]:7d} voxels ({pct:5.1f}%)")

# Check if ROI is actually in air-filled region vs soft tissue
print(f"\nDiagnosis:")
air_voxels = (sphenoid_roi < -400).sum()
soft_tissue_voxels = ((sphenoid_roi > -100) & (sphenoid_roi < 100)).sum()
bone_voxels = (sphenoid_roi > 200).sum()

print(f"  Air voxels (<-400 HU): {air_voxels} ({100*air_voxels/sphenoid_roi.size:.1f}%)")
print(f"  Soft tissue (-100 to +100 HU): {soft_tissue_voxels} ({100*soft_tissue_voxels/sphenoid_roi.size:.1f}%)")
print(f"  Bone (>200 HU): {bone_voxels} ({100*bone_voxels/sphenoid_roi.size:.1f}%)")

if soft_tissue_voxels > sphenoid_roi.size * 0.5:
    print(f"\n⚠️  ROI IS DOMINATED BY SOFT TISSUE")
    print(f"   This could mean:")
    print(f"   1. Patient actually has opacified sphenoid (fluid/mucus)")
    print(f"   2. ROI is positioned in wrong anatomical location")
    print(f"   3. ROI includes too much skull base bone/nasopharynx tissue")
