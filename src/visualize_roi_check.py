"""
Visualize where the deep sinus ROIs are actually positioned.
"""
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Load volume
nii = nib.load('data/processed/sinus_ct.nii.gz')
volume = nii.get_fdata()
spacing = nii.header.get_zooms()

z, y, x = volume.shape
print(f"Volume shape: {volume.shape}")
print(f"Spacing: {spacing}")

# Define sphenoid ROI
z_start = int(z * 0.30)
z_end = int(z * 0.50)
y_start = int(y * 0.60)
y_end = int(y * 0.85)
x_center = x // 2
x_margin = int(x * 0.2)
x_start = x_center - x_margin
x_end = x_center + x_margin

# Define posterior ethmoid ROI
z_start_pe = int(z * 0.20)
z_end_pe = int(z * 0.45)
y_start_pe = int(y * 0.40)
y_end_pe = int(y * 0.75)
x_margin_pe = int(x * 0.10)

print(f"\nSphenoid ROI: z=[{z_start}:{z_end}], y=[{y_start}:{y_end}], x=[{x_start}:{x_end}]")
print(f"Posterior ethmoid ROI: z=[{z_start_pe}:{z_end_pe}], y=[{y_start_pe}:{y_end_pe}]")

# Show slices at different z-levels with ROI overlays
fig, axes = plt.subplots(2, 4, figsize=(20, 10))

# Check slices at various z-positions
z_positions = [
    int(z * 0.15),  # Very superior
    int(z * 0.25),  # Superior (skull base)
    int(z * 0.35),  # Sphenoid level
    int(z * 0.45),  # Lower sphenoid
    int(z * 0.55),  # Below sphenoid
    int(z * 0.65),  # Mid face
    int(z * 0.75),  # Lower face
    int(z * 0.85),  # Very inferior
]

for idx, z_pos in enumerate(z_positions):
    ax = axes[idx // 4, idx % 4]
    
    # Show axial slice
    slice_data = volume[z_pos, :, :]
    ax.imshow(slice_data, cmap='gray', vmin=-1000, vmax=500)
    ax.set_title(f'z={z_pos} ({z_pos*spacing[0]:.1f}mm) - {z_pos/z*100:.0f}%', fontsize=10)
    
    # Overlay sphenoid ROI if at that level
    if z_start <= z_pos < z_end:
        rect = Rectangle((x_start, y_start), x_end-x_start, y_end-y_start, 
                        linewidth=2, edgecolor='red', facecolor='none', label='Sphenoid ROI')
        ax.add_patch(rect)
        ax.text(x_center, y_start-10, 'SPHENOID', color='red', ha='center', fontsize=8, weight='bold')
    
    # Overlay posterior ethmoid ROI if at that level
    if z_start_pe <= z_pos < z_end_pe:
        # Left side
        rect_l = Rectangle((x_center-x_margin_pe-10, y_start_pe), x_margin_pe, y_end_pe-y_start_pe,
                          linewidth=2, edgecolor='blue', facecolor='none', linestyle='--')
        ax.add_patch(rect_l)
        # Right side
        rect_r = Rectangle((x_center+10, y_start_pe), x_margin_pe, y_end_pe-y_start_pe,
                          linewidth=2, edgecolor='blue', facecolor='none', linestyle='--')
        ax.add_patch(rect_r)
        ax.text(x_center, y_start_pe-10, 'POST ETHMOID', color='blue', ha='center', fontsize=8, weight='bold')
    
    ax.axis('off')

plt.tight_layout()
plt.savefig('docs/roi_visualization.png', dpi=150, bbox_inches='tight')
print(f"\nSaved visualization to docs/roi_visualization.png")

# Now check HU values at key anatomical slices
print("\n" + "="*60)
print("HU ANALYSIS AT KEY SLICES")
print("="*60)

for z_pos, label in [(int(z*0.25), "Skull base"), 
                      (int(z*0.35), "Sphenoid sinus level"),
                      (int(z*0.45), "Lower sphenoid"),
                      (int(z*0.60), "Maxillary sinus level")]:
    slice_data = volume[z_pos, :, :]
    air_pct = 100 * (slice_data < -400).sum() / slice_data.size
    soft_tissue_pct = 100 * ((slice_data > -100) & (slice_data < 100)).sum() / slice_data.size
    print(f"\n{label} (z={z_pos}, {z_pos/z*100:.0f}%):")
    print(f"  Mean HU: {slice_data.mean():.1f}")
    print(f"  Air content (<-400): {air_pct:.1f}%")
    print(f"  Soft tissue (-100 to +100): {soft_tissue_pct:.1f}%")
    
    # Check specific sphenoid ROI region
    if z_start <= z_pos < z_end:
        roi_region = slice_data[y_start:y_end, x_start:x_end]
        roi_air_pct = 100 * (roi_region < -400).sum() / roi_region.size
        roi_soft_pct = 100 * ((roi_region > -100) & (roi_region < 100)).sum() / roi_region.size
        print(f"  In sphenoid ROI:")
        print(f"    Mean HU: {roi_region.mean():.1f}")
        print(f"    Air: {roi_air_pct:.1f}%, Soft tissue: {roi_soft_pct:.1f}%")
