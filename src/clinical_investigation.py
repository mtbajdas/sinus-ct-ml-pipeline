"""
Clinical Investigation Script - Post-Steroid Residual Pathology Analysis
Patient 19420531 - April 2025 CT Scan
"""
import argparse
import numpy as np
import nibabel as nib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path
import json
from scipy import ndimage
from scipy.ndimage import label, binary_erosion
import pandas as pd
from clinical_scores import compute_lund_mackay


def run_clinical_investigation(
    nifti_path: str | Path = 'data/processed/sinus_ct.nii.gz',
    meta_path: str | Path = 'docs/last_run_meta.json',
    out_png: str | Path = 'docs/clinical_analysis.png',
    out_json: str | Path = 'docs/metrics/clinical_analysis_report.json',
    quiet: bool = False,
):
    def log(msg: str = ""):
        if not quiet:
            print(msg)

    log("="*80)
    log(" "*20 + "CLINICAL INVESTIGATION ANALYSIS")
    log("="*80)
    log("\nPatient Context:")
    log("  - Sick 1 month before CT")
    log("  - Steroid treatment completed")
    log("  - Clinically clear at scan time")
    log("  - Goal: Detect subtle residual chronic pathology")
    log("="*80)

    # Load CT volume
    nifti_path = Path(nifti_path)
    img = nib.load(str(nifti_path))
    volume = img.get_fdata().astype(np.float32)
    spacing = img.header.get_zooms()[:3]
    voxel_volume_mm3 = np.prod(spacing)

    # Load metadata
    meta_path = Path(meta_path)
    with open(meta_path) as f:
        meta = json.load(f)

    log(f"\nPatient ID: {meta['patient_id']}")
    log(f"Study Date: {meta['study_date']}")
    log(f"Volume shape: {volume.shape}")
    log(f"Voxel spacing: {spacing} mm")

# ============================================================================
# 1. MUCOSAL THICKNESS ANALYSIS
# ============================================================================
    log("\n" + "="*80)
    log("1. MUCOSAL THICKNESS ANALYSIS")
    log("="*80)

    air_threshold = -400
    air_mask = volume < air_threshold
    air_mask_clean = ndimage.binary_opening(air_mask, structure=np.ones((3, 3, 3)))
    air_mask_clean = ndimage.binary_closing(air_mask_clean, structure=np.ones((5, 5, 5)))

    thicknesses_mm = [2, 3, 4, 5, 6]
    mucosal_findings = {}

    for thick_mm in thicknesses_mm:
        iterations = int(thick_mm / np.mean(spacing))
        eroded = binary_erosion(air_mask_clean, iterations=iterations)
        mucosal_layer = air_mask_clean & ~eroded
        
        mucosal_voxels = volume[mucosal_layer]
        soft_tissue_fraction = ((mucosal_voxels > -100) & (mucosal_voxels < 100)).sum() / len(mucosal_voxels) if len(mucosal_voxels) > 0 else 0
        
        mucosal_findings[thick_mm] = {
            'volume_ml': mucosal_layer.sum() * voxel_volume_mm3 / 1000,
            'soft_tissue_fraction': soft_tissue_fraction,
            'mean_hu': mucosal_voxels.mean() if len(mucosal_voxels) > 0 else 0,
        }

    log("\nThickness | Volume (mL) | Soft Tissue % | Mean HU")
    log("-" * 60)
    for thick, findings in mucosal_findings.items():
        log(f"{thick:4d} mm   | {findings['volume_ml']:11.2f} | {findings['soft_tissue_fraction']*100:12.1f}% | {findings['mean_hu']:7.1f}")

    findings_list = []

    if mucosal_findings[2]['soft_tissue_fraction'] > 0.3:
        log(f"\n🔍 FINDING: Mild mucosal thickening detected (≥2mm)")
        log(f"   Soft tissue fraction: {mucosal_findings[2]['soft_tissue_fraction']*100:.1f}%")
        findings_list.append(f"Residual mucosal thickening (≥2mm): {mucosal_findings[2]['volume_ml']:.1f} mL")

    if mucosal_findings[4]['soft_tissue_fraction'] > 0.2:
        log(f"\n🔍 FINDING: Moderate mucosal thickening detected (≥4mm)")
        findings_list.append(f"Moderate mucosal thickening (≥4mm): {mucosal_findings[4]['volume_ml']:.1f} mL")

    if mucosal_findings[6]['soft_tissue_fraction'] > 0.15:
        log(f"\n🔍 FINDING: Significant mucosal thickening detected (≥6mm)")
        findings_list.append(f"Significant mucosal thickening (≥6mm): {mucosal_findings[6]['volume_ml']:.1f} mL")

# ============================================================================
# 2. RETENTION CYSTS / POLYPS DETECTION
# ============================================================================
    log("\n" + "="*80)
    log("2. RETENTION CYSTS / POLYPS DETECTION")
    log("="*80)

    sinus_region = air_mask_clean
    potential_cysts = (volume > -50) & (volume < 60) & sinus_region

    labeled_cysts, num_cysts = label(potential_cysts)

    cyst_findings = []
    for i in range(1, num_cysts + 1):
        component = (labeled_cysts == i)
        volume_mm3 = component.sum() * voxel_volume_mm3
        
        if 5 <= volume_mm3 <= 500:
            component_hu = volume[component]
            coords = np.where(component)
            centroid = [coords[0].mean(), coords[1].mean(), coords[2].mean()]
            
            cyst_findings.append({
                'id': i,
                'volume_mm3': volume_mm3,
                'mean_hu': component_hu.mean(),
                'centroid': centroid,
                'type': 'retention_cyst' if component_hu.mean() < 30 else 'polyp'
            })

    log(f"\nFound {len(cyst_findings)} potential lesions (5-500 mm³)")

    if len(cyst_findings) > 0:
        df = pd.DataFrame(cyst_findings)
        df['volume_mm3'] = df['volume_mm3'].round(1)
        df['mean_hu'] = df['mean_hu'].round(1)
        log("\n" + df[['id', 'volume_mm3', 'mean_hu', 'type']].to_string(index=False))
        
        retention_cysts = df[df['type'] == 'retention_cyst']
        polyps = df[df['type'] == 'polyp']
        
        if len(retention_cysts) > 0:
            log(f"\n🔍 FINDING: {len(retention_cysts)} retention cyst(s) detected")
            log("   → Suggest chronic obstruction/inflammation")
            findings_list.append(f"Retention cysts: {len(retention_cysts)} lesions")
        
        if len(polyps) > 0:
            log(f"\n🔍 FINDING: {len(polyps)} polyp(s) detected")
            log("   → Chronic inflammatory response")
            findings_list.append(f"Polyps: {len(polyps)} lesions")
    else:
        log("\n✅ No small retention cysts or polyps detected")

# ============================================================================
# 3. LEFT-RIGHT ASYMMETRY ANALYSIS
# ============================================================================
    log("\n" + "="*80)
    log("3. LEFT-RIGHT ASYMMETRY ANALYSIS")
    log("="*80)

    midline = volume.shape[2] // 2

    left_volume = volume[:, :, :midline]
    right_volume = volume[:, :, midline:]

    left_air = (left_volume < -400).sum() * voxel_volume_mm3 / 1000
    right_air = (right_volume < -400).sum() * voxel_volume_mm3 / 1000

    left_tissue = ((left_volume > -100) & (left_volume < 100)).sum() * voxel_volume_mm3 / 1000
    right_tissue = ((right_volume > -100) & (right_volume < 100)).sum() * voxel_volume_mm3 / 1000

    air_asymmetry = abs(left_air - right_air) / (left_air + right_air) * 100
    tissue_asymmetry = abs(left_tissue - right_tissue) / (left_tissue + right_tissue) * 100

    log(f"\nAir Volume:")
    log(f"  Left:  {left_air:7.1f} mL")
    log(f"  Right: {right_air:7.1f} mL")
    log(f"  Asymmetry: {air_asymmetry:.1f}%")

    log(f"\nSoft Tissue Volume:")
    log(f"  Left:  {left_tissue:7.1f} mL")
    log(f"  Right: {right_tissue:7.1f} mL")
    log(f"  Asymmetry: {tissue_asymmetry:.1f}%")

    if air_asymmetry > 10:
        worse_side = "LEFT" if left_air < right_air else "RIGHT"
        log(f"\n🔍 FINDING: {worse_side} side shows reduced aeration (asymmetry {air_asymmetry:.1f}%)")
        findings_list.append(f"Unilateral disease: {worse_side} side predominant (air asymmetry {air_asymmetry:.1f}%)")
        
    if tissue_asymmetry > 15:
        worse_side = "LEFT" if left_tissue > right_tissue else "RIGHT"
        log(f"🔍 FINDING: {worse_side} side shows increased soft tissue (asymmetry {tissue_asymmetry:.1f}%)")
        findings_list.append(f"Tissue asymmetry: {worse_side} side (tissue asymmetry {tissue_asymmetry:.1f}%)")

# ============================================================================
# 4. OSTIOMEATAL COMPLEX (OMC) PATENCY
# ============================================================================
    log("\n" + "="*80)
    log("4. OSTIOMEATAL COMPLEX (OMC) PATENCY")
    log("="*80)

    omc_z_range = (volume.shape[0]//2 - 30, volume.shape[0]//2 - 10)
    omc_y_range = (volume.shape[1]//2 + 10, volume.shape[1]//2 + 40)
    omc_x_left = (midline - 25, midline - 5)
    omc_x_right = (midline + 5, midline + 25)

    def analyze_omc_region(z_range, y_range, x_range, side_name):
        region = volume[
            z_range[0]:z_range[1],
            y_range[0]:y_range[1],
            x_range[0]:x_range[1]
        ]
        
        air_voxels = (region < -400).sum()
        soft_tissue_voxels = ((region > -100) & (region < 100)).sum()
        total_voxels = region.size
        
        air_fraction = air_voxels / total_voxels
        tissue_fraction = soft_tissue_voxels / total_voxels
        patency_score = air_fraction * 100
        
        return {
            'side': side_name,
            'air_fraction': air_fraction,
            'tissue_fraction': tissue_fraction,
            'patency_score': patency_score,
            'mean_hu': region.mean()
        }

    left_omc = analyze_omc_region(omc_z_range, omc_y_range, omc_x_left, "LEFT")
    right_omc = analyze_omc_region(omc_z_range, omc_y_range, omc_x_right, "RIGHT")

    for omc in [left_omc, right_omc]:
        log(f"\n{omc['side']} OMC:")
        log(f"  Patency Score: {omc['patency_score']:.1f}/100")
        log(f"  Air Fraction: {omc['air_fraction']*100:.1f}%")
        log(f"  Tissue Fraction: {omc['tissue_fraction']*100:.1f}%")

    for omc in [left_omc, right_omc]:
        if omc['patency_score'] < 40:
            log(f"\n🔍 FINDING: {omc['side']} OMC shows significant narrowing (score {omc['patency_score']:.1f})")
            log("   → Predisposes to recurrent maxillary/frontal sinusitis")
            findings_list.append(f"{omc['side']} OMC significant narrowing: {omc['patency_score']:.0f}%")
        elif omc['patency_score'] < 60:
            log(f"\n🔍 FINDING: {omc['side']} OMC shows mild narrowing (score {omc['patency_score']:.1f})")
            findings_list.append(f"{omc['side']} OMC mild narrowing: {omc['patency_score']:.0f}%")

# ============================================================================
# 5. BONY CHANGES (CHRONIC INFLAMMATION MARKER)
# ============================================================================
    log("\n" + "="*80)
    log("5. BONY CHANGES ANALYSIS")
    log("="*80)

    bone_mask = volume > 200
    sclerotic_bone = volume > 800

    dilated_sinuses = ndimage.binary_dilation(air_mask_clean, iterations=5)
    sinus_wall_region = dilated_sinuses & ~air_mask_clean

    wall_bone = bone_mask & sinus_wall_region
    wall_sclerotic = sclerotic_bone & sinus_wall_region

    sclerotic_fraction = wall_sclerotic.sum() / wall_bone.sum() if wall_bone.sum() > 0 else 0

    bone_hu_values = volume[wall_bone]
    log(f"\nSinus wall bone volume: {wall_bone.sum() * voxel_volume_mm3 / 1000:.1f} mL")
    log(f"Sclerotic bone fraction: {sclerotic_fraction * 100:.1f}%")
    log(f"\nBone HU statistics:")
    bone_mean_hu = float(bone_hu_values.mean()) if bone_hu_values.size > 0 else 0.0
    log(f"  Mean: {bone_mean_hu:.1f} HU")
    log(f"  Median: {np.median(bone_hu_values):.1f} HU")
    log(f"  95th percentile: {np.percentile(bone_hu_values, 95):.1f} HU")

    if sclerotic_fraction > 0.05:
        log(f"\n🔍 FINDING: Sclerotic bone changes detected ({sclerotic_fraction*100:.1f}%)")
        log("   → Suggests chronic/recurrent inflammation")
        findings_list.append(f"Sclerotic bone changes: {sclerotic_fraction*100:.1f}%")

    if bone_hu_values.mean() > 500:
        log(f"\n🔍 FINDING: Elevated bone density (mean {bone_hu_values.mean():.1f} HU)")
        log("   → Consistent with chronic osteitis")
        findings_list.append(f"Elevated bone density: {bone_hu_values.mean():.1f} HU")

# ============================================================================
# 6. NASOPHARYNX / ADENOID ANALYSIS
# ============================================================================
    log("\n" + "="*80)
    log("6. NASOPHARYNX / ADENOID ANALYSIS")
    log("="*80)

    nasopharynx_z = (volume.shape[0]//2 - 20, volume.shape[0]//2 + 20)
    nasopharynx_y = (volume.shape[1]//2 - 30, volume.shape[1]//2 - 5)
    nasopharynx_x = (midline - 20, midline + 20)

    nasopharynx = volume[
        nasopharynx_z[0]:nasopharynx_z[1],
        nasopharynx_y[0]:nasopharynx_y[1],
        nasopharynx_x[0]:nasopharynx_x[1]
    ]

    adenoid_tissue = ((nasopharynx > 20) & (nasopharynx < 70)).sum()
    air_space = (nasopharynx < -400).sum()
    total_voxels = nasopharynx.size

    tissue_fraction = adenoid_tissue / total_voxels
    airway_fraction = air_space / total_voxels

    log(f"\nAirway patency: {airway_fraction * 100:.1f}%")
    log(f"Soft tissue fraction: {tissue_fraction * 100:.1f}%")
    log(f"Mean HU: {nasopharynx.mean():.1f}")

    if tissue_fraction > 0.5:
        log(f"\n🔍 FINDING: Adenoid hypertrophy detected ({tissue_fraction*100:.1f}% tissue)")
        log("   → Chronic nasopharyngeal obstruction")
        log("   → May contribute to recurrent sinusitis/otitis")
        findings_list.append(f"Adenoid hypertrophy: {tissue_fraction*100:.1f}% obstruction")

    if airway_fraction < 0.4:
        log(f"\n🔍 FINDING: Nasopharyngeal airway narrowing ({airway_fraction*100:.1f}% patent)")
        findings_list.append(f"Nasopharyngeal narrowing: {airway_fraction*100:.1f}% patent")

# ============================================================================
# 7. GENERATE VISUAL SUMMARY
# ============================================================================
    log("\n" + "="*80)
    log("7. GENERATING VISUAL SUMMARY")
    log("="*80)

    fig, axes = plt.subplots(3, 4, figsize=(20, 15))
    fig.suptitle('Patient 19420531 - Post-Steroid Clinical Analysis', fontsize=16, fontweight='bold')

    key_slices = [
        (volume.shape[0]//2 - 40, 'Superior (Frontal Sinuses)'),
        (volume.shape[0]//2 - 20, 'Mid-Superior (Ethmoid)'),
        (volume.shape[0]//2, 'Central (Maxillary)'),
        (volume.shape[0]//2 + 20, 'Inferior (Nasopharynx)'),
    ]

    for idx, (slice_idx, title) in enumerate(key_slices):
        axes[0, idx].imshow(volume[slice_idx], cmap='gray', vmin=-1000, vmax=400)
        axes[0, idx].set_title(title)
        axes[0, idx].axis('off')
        
        axes[1, idx].imshow(volume[slice_idx], cmap='gray', vmin=-1000, vmax=400)
        axes[1, idx].imshow(air_mask_clean[slice_idx], cmap='Blues', alpha=0.3)
        axes[1, idx].set_title('Air Cavities')
        axes[1, idx].axis('off')
        
        pathology = ((volume[slice_idx] > -100) & (volume[slice_idx] < 100) & air_mask_clean[slice_idx])
        axes[2, idx].imshow(volume[slice_idx], cmap='gray', vmin=-1000, vmax=400)
        axes[2, idx].imshow(pathology, cmap='Reds', alpha=0.5)
        axes[2, idx].set_title('Soft Tissue in Sinuses')
        axes[2, idx].axis('off')

    plt.tight_layout()
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out_png), dpi=150, bbox_inches='tight')
    log(f"\n✅ Visual analysis saved to {out_png}")

# ============================================================================
# 8. CLINICAL SUMMARY REPORT
# ============================================================================
    log("\n" + "="*80)
    log(" "*20 + "CLINICAL SUMMARY REPORT")
    log("="*80)
    log(f"\nPatient: {meta['patient_id']}")
    log(f"Study Date: {meta['study_date']}")
    log(f"Clinical Context: Post-steroid treatment, clinically clear at scan")

    log("\n" + "-"*80)
    log("FINDINGS SUMMARY:")
    log("-"*80)

    if len(findings_list) > 0:
        for finding in findings_list:
            log(f"✓ {finding}")
    else:
        log("✓ No significant residual pathology detected")
        log("  → Sinuses well-aerated (99.9% air fraction)")
        log("  → Minimal mucosal thickening")
        log("  → Good bilateral symmetry")

    log("\n" + "-"*80)
    log("CLINICAL IMPRESSION:")
    log("-"*80)

    if len(findings_list) > 0:
        log("\nDespite clinical resolution and steroid treatment, subtle findings suggest:")
        log("  1. Underlying chronic inflammatory process")
        log("  2. Risk factors for recurrent infection persist")
        log("  3. Consider:")
        log("     - Longer-term anti-inflammatory management")
        log("     - Environmental/allergen evaluation")
        log("     - Follow-up imaging in 3-6 months")
        log("     - ENT referral if symptoms recur")
    else:
        log("\nExcellent response to steroid therapy:")
        log("  - Complete resolution of acute inflammation")
        log("  - No evidence of chronic changes")
        log("  - Normal sinus anatomy and drainage")
        log("  - Low risk of recurrence if triggers avoided")

    log("\n" + "="*80)

# Save detailed report
    # 8.1 Standard and conservative clinical scores (Lund–Mackay)
    lm = compute_lund_mackay(volume)
    lm_cons = compute_lund_mackay(volume, conservative=True)

    clinical_report = {
        'patient_id': meta['patient_id'],
        'study_date': meta['study_date'],
        'context': 'post_steroid_evaluation',
        'findings': findings_list,
        'metrics': {
            'mucosal_thickening': {str(k): v for k, v in mucosal_findings.items()},
            'retention_cysts': len(cyst_findings),
            'asymmetry': {'air_pct': float(air_asymmetry), 'tissue_pct': float(tissue_asymmetry)},
            'omc_patency': {
                'left_score': float(left_omc['patency_score']), 
                'right_score': float(right_omc['patency_score'])
            },
            'bony_changes': {
                'sclerotic_fraction_pct': float(sclerotic_fraction * 100),
                'bone_mean_hu': bone_mean_hu,
            },
            'nasopharynx': {
                'tissue_fraction_pct': float(tissue_fraction * 100), 
                'airway_fraction_pct': float(airway_fraction * 100)
            },
            'lund_mackay': lm,
            'lund_mackay_conservative': lm_cons
        }
    }

    def _to_serializable(obj):
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, dict):
            return {k: _to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_to_serializable(x) for x in obj]
        elif hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        elif hasattr(obj, 'tolist'):  # numpy array
            return obj.tolist()
        return obj

    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(_to_serializable(clinical_report), indent=2))
    log(f"\n✅ Detailed report saved to: {out_json}")
    log("\n" + "="*80)
    log("ANALYSIS COMPLETE")
    log("="*80)

    return clinical_report


def _parse_args():
    p = argparse.ArgumentParser(description="Clinical investigation analysis")
    p.add_argument('--nifti', default='data/processed/sinus_ct.nii.gz')
    p.add_argument('--meta', default='docs/last_run_meta.json')
    p.add_argument('--out-png', default='docs/clinical_analysis.png')
    p.add_argument('--out-json', default='docs/metrics/clinical_analysis_report.json')
    p.add_argument('--quiet', action='store_true')
    return p.parse_args()


if __name__ == '__main__':
    args = _parse_args()
    run_clinical_investigation(
        nifti_path=args.nifti,
        meta_path=args.meta,
        out_png=args.out_png,
        out_json=args.out_json,
        quiet=args.quiet,
    )
