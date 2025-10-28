"""
Debug deep sinus measurements to verify ROI positioning and calculations.
"""
import numpy as np
import nibabel as nib
import json

def debug_deep_sinus():
    """Diagnostic analysis of deep sinus measurements."""
    
    # Load CT volume
    nifti_path = 'data/processed/sinus_ct.nii.gz'
    
    print("Loading CT volume...")
    nii = nib.load(nifti_path)
    volume = nii.get_fdata()
    spacing = nii.header.get_zooms()[:3]
    
    z, y, x = volume.shape
    print(f"Volume shape: {volume.shape}")
    print(f"Spacing: {spacing}")
    print(f"Physical dimensions: {z*spacing[0]:.1f} x {y*spacing[1]:.1f} x {x*spacing[2]:.1f} mm")
    
    # Check sphenoid ROI
    print("\n" + "="*60)
    print("SPHENOID SINUS ROI (NEW CORRECTED POSITIONING)")
    print("="*60)
    
    # NEW positioning - z=0 is SUPERIOR (top of head)
    z_start = int(z * 0.30)  # Superior
    z_end = int(z * 0.50)    # Inferior
    y_start = int(y * 0.60)  # Posterior
    y_end = int(y * 0.85)
    x_center = x // 2
    x_margin = int(x * 0.2)
    
    print(f"Z range: slices {z_start}-{z_end} ({z_end-z_start} slices)")
    print(f"  Physical: {z_start*spacing[0]:.1f} - {z_end*spacing[0]:.1f} mm")
    print(f"Y range: rows {y_start}-{y_end} ({y_end-y_start} rows)")
    print(f"X range: cols {x_center-x_margin}-{x_center+x_margin} ({2*x_margin} cols)")
    
    sphenoid_roi = volume[z_start:z_end, y_start:y_end, x_center-x_margin:x_center+x_margin]
    print(f"\nROI shape: {sphenoid_roi.shape}")
    print(f"ROI volume: {np.prod(sphenoid_roi.shape) * np.prod(spacing) / 1000:.1f} mL")
    
    # Check air content
    air_voxels_400 = (sphenoid_roi < -400).sum()
    air_voxels_200 = (sphenoid_roi < -200).sum()
    total_voxels = sphenoid_roi.size
    
    voxel_vol = np.prod(spacing)
    
    print(f"\nAir content:")
    print(f"  < -400 HU: {air_voxels_400} voxels ({air_voxels_400/total_voxels*100:.1f}%) = {air_voxels_400*voxel_vol/1000:.2f} mL")
    print(f"  < -200 HU: {air_voxels_200} voxels ({air_voxels_200/total_voxels*100:.1f}%) = {air_voxels_200*voxel_vol/1000:.2f} mL")
    
    print(f"\nHU distribution in ROI:")
    print(f"  Min: {sphenoid_roi.min():.0f}")
    print(f"  Max: {sphenoid_roi.max():.0f}")
    print(f"  Mean: {sphenoid_roi.mean():.1f}")
    print(f"  Median: {np.median(sphenoid_roi):.1f}")
    
    # Check posterior ethmoid ROI
    print("\n" + "="*60)
    print("POSTERIOR ETHMOID ROI (NEW CORRECTED POSITIONING)")
    print("="*60)
    
    # NEW positioning - posterior ethmoid is SUPERIOR to sphenoid
    z_post_eth_start = int(z * 0.20)  # More superior
    z_post_eth_end = int(z * 0.45)
    y_post_eth_start = int(y * 0.40)
    y_post_eth_end = int(y * 0.75)
    x_post_eth_center = x // 2
    x_post_eth_margin = int(x * 0.18)
    
    print(f"Z range: slices {z_post_eth_start}-{z_post_eth_end} ({z_post_eth_end-z_post_eth_start} slices)")
    print(f"  Physical: {z_post_eth_start*spacing[0]:.1f} - {z_post_eth_end*spacing[0]:.1f} mm")
    print(f"Y range: rows {y_post_eth_start}-{y_post_eth_end} ({y_post_eth_end-y_post_eth_start} rows)")
    print(f"X range: cols {x_post_eth_center-x_post_eth_margin}-{x_post_eth_center+x_post_eth_margin}")
    
    post_eth_roi = volume[
        z_post_eth_start:z_post_eth_end,
        y_post_eth_start:y_post_eth_end,
        x_post_eth_center-x_post_eth_margin:x_post_eth_center+x_post_eth_margin
    ]
    
    print(f"\nROI shape: {post_eth_roi.shape}")
    print(f"ROI volume: {np.prod(post_eth_roi.shape) * np.prod(spacing) / 1000:.1f} mL")
    
    # Check air content
    post_eth_air_400 = (post_eth_roi < -400).sum()
    post_eth_air_200 = (post_eth_roi < -200).sum()
    post_eth_total = post_eth_roi.size
    
    print(f"\nAir content:")
    print(f"  < -400 HU: {post_eth_air_400} voxels ({post_eth_air_400/post_eth_total*100:.1f}%) = {post_eth_air_400*voxel_vol/1000:.2f} mL")
    print(f"  < -200 HU: {post_eth_air_200} voxels ({post_eth_air_200/post_eth_total*100:.1f}%) = {post_eth_air_200*voxel_vol/1000:.2f} mL")
    
    print(f"\nHU distribution in ROI:")
    print(f"  Min: {post_eth_roi.min():.0f}")
    print(f"  Max: {post_eth_roi.max():.0f}")
    print(f"  Mean: {post_eth_roi.mean():.1f}")
    print(f"  Median: {np.median(post_eth_roi):.1f}")
    
    # Sample a few z-slices to understand anatomy
    print("\n" + "="*60)
    print("SLICE-BY-SLICE ANALYSIS")
    print("="*60)
    
    sample_slices = [
        int(z * 0.3),  # Superior
        int(z * 0.4),
        int(z * 0.5),  # Mid
        int(z * 0.6),
        int(z * 0.7),  # Inferior
    ]
    
    for slice_idx in sample_slices:
        slice_data = volume[slice_idx, :, :]
        air_pct = (slice_data < -400).sum() / slice_data.size * 100
        tissue_pct = ((slice_data >= -100) & (slice_data <= 100)).sum() / slice_data.size * 100
        print(f"Slice {slice_idx}/{z} ({slice_idx*spacing[0]:.1f}mm): "
              f"Air={air_pct:.1f}%, Tissue={tissue_pct:.1f}%, Mean HU={slice_data.mean():.0f}")
    
    # Recommendation
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    if air_voxels_400 * voxel_vol / 1000 < 2.0:
        print("⚠ SPHENOID: Very small air volume detected (<2 mL)")
        print("  Possible issues:")
        print("  - ROI may be too inferior (below sphenoid)")
        print("  - Sphenoid may be opacified")
        print("  - ROI positioning needs adjustment")
        print(f"  Recommendation: Check z-range, current: {z_start*spacing[0]:.1f}-{z_end*spacing[0]:.1f}mm")
    
    if post_eth_air_400 * voxel_vol / 1000 > 50:
        print("\n⚠ POSTERIOR ETHMOID: Very large air volume (>50 mL)")
        print("  Possible issues:")
        print("  - ROI may include maxillary sinuses")
        print("  - ROI may include anterior ethmoid")
        print("  - ROI too large")
        print(f"  Recommendation: Refine z-range or reduce ROI size")


if __name__ == '__main__':
    debug_deep_sinus()
