"""
Validation Test - Orlando Normal Scan (April 2025)

Ground truth from radiologist report: "essentially clear; trace mucus in right sphenoid"

Expected bands for this scan:
- OMC patency: Patent bilaterally (air fraction > 50%)
- Cyst count: 0
- Sclerotic fraction: < 5%
- Sphenoid mucus: trace (< 1.0 mL)
"""
import sys
from pathlib import Path
import json
import numpy as np
import nibabel as nib

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from calibration import calibrate_volume, adaptive_threshold_air_tissue
from sinus import (
    build_sinus_wall_shell,
    compute_sclerosis_zscore,
    estimate_reference_bone_stats,
    measure_omc_patency_coronal,
    detect_retention_cysts_strict,
)


def test_orlando_normal():
    """
    Validation test for the Orlando April 2025 normal scan.
    """
    print("="*80)
    print(" "*20 + "ORLANDO NORMAL SCAN VALIDATION")
    print("="*80)
    
    # Load processed volume (series 5309 - bone kernel)
    nifti_path = Path('data/processed/sinus_ct.nii.gz')
    if not nifti_path.exists():
        print(f"[SKIP] {nifti_path} not found. Run pipeline first.")
        return
    
    img = nib.load(str(nifti_path))
    volume_raw = img.get_fdata().astype(np.float32)
    spacing = img.header.get_zooms()[:3]
    
    print(f"\nLoaded: {nifti_path}")
    print(f"   Shape: {volume_raw.shape}")
    print(f"   Spacing: {spacing} mm")
    
    # 1. HU Calibration
    print("\n" + "-"*80)
    print("1. HU CALIBRATION")
    print("-"*80)
    
    volume, cal_meta = calibrate_volume(volume_raw, output_json=Path('docs/validation/calibration.json'))
    
    air = cal_meta['air_anchor']
    bone = cal_meta['bone_anchor']
    correction = cal_meta['correction']
    
    print(f"\n[OK] Air anchor: {air['measured_hu']:.1f} HU (expected {air['expected_hu']:.0f} +/- 50)")
    print(f"  Pass: {air['pass']}")
    print(f"\n[OK] Bone anchor: {bone['measured_hu']:.1f} HU (expected {bone['expected_hu']:.0f} +/- 200)")
    print(f"  Pass: {bone['pass']}")
    
    if correction and correction.get('apply'):
        print(f"\n[OK] Correction applied:")
        print(f"  Slope: {correction['slope']:.4f}")
        print(f"  Intercept: {correction['intercept']:.2f} HU")
    else:
        print("\n[OK] No correction needed (delta within tolerance)")
    
    # 2. Adaptive Thresholds
    print("\n" + "-"*80)
    print("2. ADAPTIVE THRESHOLDS")
    print("-"*80)
    
    # Build rough cavity mask for adaptive thresholding
    air_mask_rough = volume < -400
    thresholds = adaptive_threshold_air_tissue(volume, sinus_mask=air_mask_rough)
    
    print(f"\n[OK] Air threshold: {thresholds['air_threshold']:.1f} HU")
    print(f"  Air peak: {thresholds['air_peak']:.1f} HU")
    print(f"  Tissue peak: {thresholds['tissue_peak']:.1f} HU")
    print(f"  Bone threshold: {thresholds['bone_threshold']:.0f} HU")
    print(f"  Sclerosis threshold: {thresholds['sclerosis_threshold']:.0f} HU")
    
    # 3. OMC Patency
    print("\n" + "-"*80)
    print("3. OMC PATENCY (Anatomical Corridor Method)")
    print("-"*80)
    
    # Use relaxed air threshold (-200 HU) for OMC measurement
    # Rationale: thin air columns in OMC have partial volume effects, sit at -200 to -400 HU
    # Also save visualization slices for debugging
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    
    omc_results = measure_omc_patency_coronal(
        volume,
        spacing,
        air_threshold=-200.0,
    )
    
    # Quick visualization of OMC corridors
    z, y, x = volume.shape
    midline = x // 2
    z_mid = int(z * 0.35)  # Mid-point of anterior_superior region
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(volume[z_mid, :, :], cmap='gray', vmin=-1000, vmax=400)
    ax.set_title(f'OMC Corridor Visualization (z={z_mid}, ~35% superior-inferior)', fontsize=14)
    
    # Overlay all 3 candidate regions
    cands = [
        ('anterior_superior', (int(y * 0.35), int(y * 0.55)), 'cyan'),
        ('mid_anterior', (int(y * 0.40), int(y * 0.60)), 'yellow'),
        ('posterior_mid', (int(y * 0.50), int(y * 0.70)), 'magenta'),
    ]
    
    for name, (y_start, y_end), color in cands:
        rect_left = Rectangle((midline - 50, y_start), 45, y_end - y_start, 
                              linewidth=2, edgecolor=color, facecolor='none', label=f'{name} L')
        rect_right = Rectangle((midline + 5, y_start), 45, y_end - y_start,
                               linewidth=2, edgecolor=color, facecolor='none', linestyle='--', label=f'{name} R')
        ax.add_patch(rect_left)
        ax.add_patch(rect_right)
    
    ax.axvline(midline, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Midline')
    ax.legend(loc='upper left', fontsize=8)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig('docs/validation/omc_corridor_overlay.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [SAVED] OMC corridor visualization: docs/validation/omc_corridor_overlay.png")
    
    print(f"\n[OK] Left OMC:")
    print(f"  Air fraction: {omc_results['left']['air_fraction_pct']:.1f}%")
    print(f"  Classification: {omc_results['left']['classification']}")
    print(f"  Confidence: {omc_results['left']['confidence']:.2f}")
    
    print(f"\n[OK] Right OMC:")
    print(f"  Air fraction: {omc_results['right']['air_fraction_pct']:.1f}%")
    print(f"  Classification: {omc_results['right']['classification']}")
    print(f"  Confidence: {omc_results['right']['confidence']:.2f}")
    
    # Expected: Patent bilaterally
    omc_pass = (
        omc_results['left']['classification'] == 'Patent' and
        omc_results['right']['classification'] == 'Patent'
    )
    
    # 4. Sclerotic Bone
    print("\n" + "-"*80)
    print("4. SCLEROTIC BONE (Wall Shell + Z-Score Method)")
    print("-"*80)
    
    # Build cavity mask and wall shell
    air_mask = volume < thresholds['air_threshold']
    from scipy import ndimage
    air_mask_clean = ndimage.binary_opening(air_mask, structure=np.ones((3, 3, 3)))
    air_mask_clean = ndimage.binary_closing(air_mask_clean, structure=np.ones((5, 5, 5)))
    
    wall_shell = build_sinus_wall_shell(air_mask_clean, shell_thickness=2)
    
    # Estimate reference bone stats
    ref_bone = estimate_reference_bone_stats(volume)
    
    sclerosis = compute_sclerosis_zscore(
        volume,
        wall_shell,
        reference_bone_hu=ref_bone,
        z_threshold=2.0,
        min_cluster_size=30,
    )
    
    print(f"\n[OK] Reference bone: {ref_bone[0]:.1f} +/- {ref_bone[1]:.1f} HU")
    print(f"  Sclerosis threshold: {sclerosis['threshold_hu']:.1f} HU (z > {sclerosis['z_threshold']})")
    print(f"  Sclerotic fraction: {sclerosis['sclerotic_fraction'] * 100:.2f}%")
    print(f"  Clusters (>=30 voxels): {sclerosis['n_clusters']}")
    
    # Expected: < 5%
    sclerosis_pass = sclerosis['sclerotic_fraction'] < 0.05
    
    # 5. Retention Cysts
    print("\n" + "-"*80)
    print("5. RETENTION CYSTS (Strict Anatomical Rules)")
    print("-"*80)
    
    cysts = detect_retention_cysts_strict(
        volume,
        air_mask_clean,
        spacing,
        hu_range=(-50, 50),
        min_area_mm2=15.0,
        max_area_mm2=500.0,
        wall_proximity_voxels=3,
    )
    
    print(f"\n[OK] Cyst count: {cysts['cyst_count']}")
    if cysts['cysts']:
        for i, cyst in enumerate(cysts['cysts'], start=1):
            print(f"  Cyst {i}: {cyst['volume_mm3']:.1f} mm^3, {cyst['mean_hu']:.1f} HU")
    
    # Expected: 0
    cyst_pass = cysts['cyst_count'] == 0
    
    # 6. Summary
    print("\n" + "="*80)
    print(" "*20 + "VALIDATION SUMMARY")
    print("="*80)
    
    tests = [
        ("HU Calibration", air['pass'] and bone['pass']),
        ("OMC Patency (Patent bilaterally)", omc_pass),
        ("Sclerotic Fraction (< 5%)", sclerosis_pass),
        ("Cyst Count (= 0)", cyst_pass),
    ]
    
    all_pass = True
    for test_name, passed in tests:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")
        all_pass = all_pass and passed
    
    print("\n" + "="*80)
    if all_pass:
        print("SUCCESS: ALL TESTS PASSED - Pipeline agrees with clinical ground truth")
    else:
        print("WARNING: SOME TESTS FAILED - Review thresholds and anatomical heuristics")
    print("="*80)
    
    # Save results
    results = {
        'scan': 'Orlando_April_2025_series_5309',
        'ground_truth': {
            'omc_patency': 'Patent bilaterally',
            'cyst_count': 0,
            'sclerotic_fraction': '< 5%',
            'sphenoid_mucus': 'trace (< 1 mL)',
        },
        'calibration': cal_meta,
        'adaptive_thresholds': thresholds,
        'omc_patency': omc_results,
        'sclerosis': sclerosis,
        'cysts': cysts,
        'tests_passed': all_pass,
    }
    
    output_json = Path('docs/validation/orlando_normal_results.json')
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n[SAVED] Results saved to: {output_json}")
    
    return all_pass


if __name__ == '__main__':
    passed = test_orlando_normal()
    sys.exit(0 if passed else 1)
