"""
Comprehensive Sinus CT Analysis

Uses validated methods from sinus module to perform complete quantitative analysis:
- HU calibration with air/bone anchors
- OMC patency measurement (multi-candidate corridor method)
- Sclerosis detection (z-score method)
- Retention cyst detection (strict anatomical rules)
- Lund-Mackay clinical scoring
- Volumetric analysis
- Deep sinus analysis (sphenoid, posterior ethmoid)
- Oropharyngeal analysis (tonsils, airway) if coverage permits
"""
import argparse
import sys
from pathlib import Path
import json
from datetime import datetime

import numpy as np
import nibabel as nib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from calibration import calibrate_volume, adaptive_threshold_air_tissue
from sinus import (
    measure_omc_patency_coronal,
    compute_sclerosis_zscore,
    detect_retention_cysts_strict,
    build_sinus_wall_shell,
    estimate_reference_bone_stats,
    measure_sphenoid_volume,
    measure_posterior_ethmoid_volume,
    check_sphenoid_opacification,
    measure_skull_base_thickness,
)
from oropharynx import (
    measure_tonsil_volumes,
    compute_brodsky_grade,
    measure_oropharyngeal_airway,
)
from clinical_scores import compute_lund_mackay


def run_comprehensive_analysis(
    nifti_path: str | Path = 'data/processed/sinus_ct.nii.gz',
    meta_path: str | Path = 'docs/last_run_meta.json',
    output_json: str | Path = 'docs/metrics/clinical_analysis_report.json',
    verbose: bool = True,
):
    """Run complete validated sinus analysis pipeline."""
    
    def log(msg=""):
        if verbose:
            print(msg)
    
    log("=" * 80)
    log("           COMPREHENSIVE SINUS CT ANALYSIS")
    log("           Using Validated Methods")
    log("=" * 80)
    
    # Load volume
    nifti_path = Path(nifti_path)
    if not nifti_path.exists():
        raise FileNotFoundError(f"NIfTI file not found: {nifti_path}")
    
    log(f"\n📂 Loading: {nifti_path}")
    img = nib.load(str(nifti_path))
    volume_raw = img.get_fdata().astype(np.float32)
    spacing = img.header.get_zooms()[:3]
    
    log(f"   Volume shape: {volume_raw.shape}")
    log(f"   Voxel spacing: {spacing} mm")
    
    # Load metadata
    meta = {}
    meta_path = Path(meta_path)
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        log(f"   Patient ID: {meta.get('patient_id', 'Unknown')}")
        log(f"   Study Date: {meta.get('study_date', 'Unknown')}")
    
    # ========================================================================
    # 1. HU CALIBRATION
    # ========================================================================
    log("\n" + "=" * 80)
    log("1. HU CALIBRATION (Air/Bone Anchor Method)")
    log("=" * 80)
    
    volume_calibrated, calib_meta = calibrate_volume(volume_raw)
    
    log(f"   Air anchor: {calib_meta['air_anchor']['measured_hu']:.1f} HU → "
        f"{calib_meta['air_anchor']['expected_hu']} HU")
    log(f"   Bone anchor: {calib_meta['bone_anchor']['measured_hu']:.1f} HU → "
        f"{calib_meta['bone_anchor']['expected_hu']} HU")
    
    if calib_meta['correction']:
        log(f"   Correction: slope={calib_meta['correction']['slope']:.4f}, "
            f"intercept={calib_meta['correction']['intercept']:.2f}")
        log(f"   ✓ Calibration applied")
    else:
        log(f"   ✓ No correction needed (already calibrated)")
    
    # ========================================================================
    # 2. ADAPTIVE TISSUE SEGMENTATION
    # ========================================================================
    log("\n" + "=" * 80)
    log("2. ADAPTIVE TISSUE SEGMENTATION")
    log("=" * 80)
    
    threshold_dict = adaptive_threshold_air_tissue(volume_calibrated)
    air_threshold = threshold_dict['air_threshold']
    log(f"   Adaptive air threshold: {air_threshold:.1f} HU")
    log(f"   Air peak: {threshold_dict['air_peak']:.1f} HU")
    log(f"   Tissue peak: {threshold_dict['tissue_peak']:.1f} HU")
    
    # Compute volumes
    voxel_volume_mm3 = np.prod(spacing)
    air_mask = volume_calibrated < air_threshold
    tissue_mask = (volume_calibrated >= -100) & (volume_calibrated <= 100)
    
    air_volume_ml = air_mask.sum() * voxel_volume_mm3 / 1000
    tissue_volume_ml = tissue_mask.sum() * voxel_volume_mm3 / 1000
    total_volume_ml = air_volume_ml + tissue_volume_ml
    
    log(f"   Air volume: {air_volume_ml:.1f} mL ({100*air_volume_ml/total_volume_ml:.1f}%)")
    log(f"   Soft tissue: {tissue_volume_ml:.1f} mL ({100*tissue_volume_ml/total_volume_ml:.1f}%)")
    
    # ========================================================================
    # 3. OMC PATENCY MEASUREMENT
    # ========================================================================
    log("\n" + "=" * 80)
    log("3. OMC PATENCY (Multi-Candidate Corridor Method)")
    log("=" * 80)
    
    omc_result = measure_omc_patency_coronal(
        volume_calibrated,
        spacing,
        air_threshold=air_threshold,
    )
    
    log(f"\n   LEFT OMC:")
    log(f"      Air fraction: {omc_result['left']['air_fraction']*100:.1f}%")
    log(f"      Classification: {omc_result['left']['classification']}")
    log(f"      Confidence: {omc_result['left']['confidence']:.2f}")
    log(f"      Best candidate: {omc_result['left']['best_candidate']}")
    
    log(f"\n   RIGHT OMC:")
    log(f"      Air fraction: {omc_result['right']['air_fraction']*100:.1f}%")
    log(f"      Classification: {omc_result['right']['classification']}")
    log(f"      Confidence: {omc_result['right']['confidence']:.2f}")
    log(f"      Best candidate: {omc_result['right']['best_candidate']}")
    
    # Classification summary
    if (omc_result['left']['classification'] != 'Patent' or 
        omc_result['right']['classification'] != 'Patent'):
        log(f"\n   ⚠️  OMC obstruction detected - impaired sinus drainage")
    else:
        log(f"\n   ✓ OMC patent bilaterally - normal drainage")
    
    # ========================================================================
    # 4. SCLEROSIS DETECTION
    # ========================================================================
    log("\n" + "=" * 80)
    log("4. SCLEROSIS DETECTION (Z-Score Method)")
    log("=" * 80)
    
    # Get reference bone statistics
    ref_median, ref_std = estimate_reference_bone_stats(volume_calibrated)
    log(f"   Reference bone (hard palate):")
    log(f"      Median: {ref_median:.0f} HU")
    log(f"      Std dev: {ref_std:.0f} HU")
    
    # Build sinus wall shell
    cavity_mask = volume_calibrated < air_threshold
    shell_mask = build_sinus_wall_shell(cavity_mask, shell_thickness=2)
    shell_volume_ml = shell_mask.sum() * voxel_volume_mm3 / 1000
    
    log(f"\n   Sinus wall shell:")
    log(f"      Shell volume: {shell_volume_ml:.1f} mL")
    
    # Compute sclerosis
    sclerosis_result = compute_sclerosis_zscore(
        volume_calibrated,
        shell_mask,
        reference_bone_hu=(ref_median, ref_std),
        z_threshold=2.0,
    )
    
    sclerotic_pct = sclerosis_result['sclerotic_fraction'] * 100
    wall_mean_hu = volume_calibrated[shell_mask > 0].mean() if shell_mask.sum() > 0 else 0
    
    log(f"      Mean wall HU: {wall_mean_hu:.0f} HU")
    log(f"      Sclerotic fraction: {sclerotic_pct:.1f}%")
    log(f"      Sclerotic clusters: {sclerosis_result['n_clusters']}")
    
    # Interpret
    if sclerotic_pct < 5:
        interp = "Normal"
    elif sclerotic_pct < 15:
        interp = "Mild chronic changes"
    elif sclerotic_pct < 30:
        interp = "Moderate chronic osteitis"
    else:
        interp = "Severe chronic osteitis"
    
    log(f"      Interpretation: {interp}")
    
    # ========================================================================
    # 5. RETENTION CYST DETECTION
    # ========================================================================
    log("\n" + "=" * 80)
    log("5. RETENTION CYST DETECTION (Strict Anatomical Rules)")
    log("=" * 80)
    
    cyst_result = detect_retention_cysts_strict(
        volume_calibrated,
        cavity_mask,
        spacing,
    )
    
    cysts = cyst_result['cysts']
    log(f"   Detected: {len(cysts)} retention cyst(s)")
    
    if len(cysts) > 0:
        log(f"\n   Details:")
        for i, cyst in enumerate(cysts, 1):
            log(f"      Cyst {i}:")
            log(f"         Volume: {cyst['volume_mm3']:.2f} mm³")
            log(f"         Location: {cyst['centroid']}")
            log(f"         Mean HU: {cyst['mean_hu']:.1f}")
    
    if len(cysts) > 2:
        log(f"\n   ⚠️  Elevated cyst count suggests chronic inflammation")
    else:
        log(f"\n   ✓ Cyst count within normal range (0-2)")
    
    # ========================================================================
    # 6. LUND-MACKAY CLINICAL SCORING
    # ========================================================================
    log("\n" + "=" * 80)
    log("6. LUND-MACKAY CLINICAL SCORING")
    log("=" * 80)
    
    lm_standard = compute_lund_mackay(volume_calibrated, conservative=False)
    lm_conservative = compute_lund_mackay(volume_calibrated, conservative=True)
    
    log(f"\n   Standard scoring:")
    log(f"      LM-20 (sinuses only): {lm_standard['totals']['lm20']}/20")
    log(f"      LM-24 (with OMC): {lm_standard['totals']['lm24']}/24")
    
    log(f"\n   Conservative scoring:")
    log(f"      LM-20 (sinuses only): {lm_conservative['totals']['lm20']}/20")
    log(f"      LM-24 (with OMC): {lm_conservative['totals']['lm24']}/24")
    
    # Interpret
    lm24 = lm_standard['totals']['lm24']
    if lm24 <= 4:
        severity = "Normal/Mild"
    elif lm24 <= 10:
        severity = "Moderate"
    else:
        severity = "Severe"
    
    log(f"\n   Severity classification: {severity}")
    
    # ========================================================================
    # 7. DEEP SINUS ANALYSIS
    # ========================================================================
    log("\n" + "=" * 80)
    log("7. DEEP SINUS ANALYSIS (Sphenoid & Posterior Ethmoid)")
    log("=" * 80)
    
    # Sphenoid volume
    sphenoid_metrics = measure_sphenoid_volume(volume_calibrated, spacing, air_threshold=air_threshold)
    
    log(f"\n   Sphenoid sinus:")
    log(f"      Total volume: {sphenoid_metrics['sphenoid_volume_ml']:.1f} mL")
    log(f"      Left: {sphenoid_metrics['left_volume_ml']:.1f} mL, Right: {sphenoid_metrics['right_volume_ml']:.1f} mL")
    
    pneum_grades = ["Absent", "Conchal", "Presellar", "Sellar"]
    log(f"      Pneumatization: {pneum_grades[sphenoid_metrics['pneumatization_grade']]}")
    log(f"      Air fraction: {sphenoid_metrics['air_fraction']*100:.1f}%")
    
    # Sphenoid opacification check
    sphenoid_opac = check_sphenoid_opacification(volume_calibrated, spacing, air_threshold=air_threshold)
    
    opac_labels = ["Clear", "Partial", "Complete"]
    log(f"\n   Sphenoid opacification:")
    log(f"      Left: {opac_labels[sphenoid_opac['left_opacification_grade']]} ({sphenoid_opac['left_air_fraction']*100:.1f}% air)")
    log(f"      Right: {opac_labels[sphenoid_opac['right_opacification_grade']]} ({sphenoid_opac['right_air_fraction']*100:.1f}% air)")
    
    if sphenoid_opac['fluid_detected']:
        log(f"      ⚠️  Fluid level detected")
    
    # Posterior ethmoid
    post_eth_metrics = measure_posterior_ethmoid_volume(volume_calibrated, spacing, air_threshold=air_threshold)
    
    log(f"\n   Posterior ethmoid:")
    log(f"      Total volume: {post_eth_metrics['posterior_ethmoid_volume_ml']:.1f} mL")
    log(f"      Left: {post_eth_metrics['left_volume_ml']:.1f} mL, Right: {post_eth_metrics['right_volume_ml']:.1f} mL")
    log(f"      Estimated cell count: {post_eth_metrics['cell_count_estimate']}")
    log(f"      Air fraction: {post_eth_metrics['air_fraction']*100:.1f}%")
    
    # Skull base
    skull_base_metrics = measure_skull_base_thickness(volume_calibrated, spacing)
    
    log(f"\n   Skull base (sphenoid roof):")
    log(f"      Mean thickness: {skull_base_metrics['mean_thickness_mm']:.2f} mm")
    log(f"      Minimum thickness: {skull_base_metrics['minimum_thickness_mm']:.2f} mm")
    log(f"      Bone mean HU: {skull_base_metrics['bone_hu_mean']:.0f}")
    
    if skull_base_metrics['minimum_thickness_mm'] < 1.0 and skull_base_metrics['minimum_thickness_mm'] > 0:
        log(f"      ⚠️  Thin skull base detected (<1mm)")
    
    # ========================================================================
    # 8. OROPHARYNGEAL ANALYSIS (if coverage permits)
    # ========================================================================
    log("\n" + "=" * 80)
    log("8. OROPHARYNGEAL ANALYSIS (Tonsils & Airway)")
    log("=" * 80)
    
    # Tonsil volumes
    tonsil_metrics = measure_tonsil_volumes(volume_calibrated, spacing)
    
    if tonsil_metrics['has_coverage']:
        log(f"\n   Palatine tonsils:")
        log(f"      Left: {tonsil_metrics['left_tonsil_volume_ml']:.2f} mL")
        log(f"      Right: {tonsil_metrics['right_tonsil_volume_ml']:.2f} mL")
        log(f"      Total: {tonsil_metrics['total_tonsil_volume_ml']:.2f} mL")
        
        if tonsil_metrics['asymmetry_ratio'] > 2.0:
            log(f"      ⚠️  Significant asymmetry (ratio: {tonsil_metrics['asymmetry_ratio']:.1f})")
        
        # Brodsky grade
        if tonsil_metrics['total_tonsil_volume_ml'] > 0.5:
            brodsky_metrics = compute_brodsky_grade(volume_calibrated, spacing)
            log(f"\n   Airway obstruction:")
            log(f"      Brodsky grade: {brodsky_metrics['brodsky_grade']}/4")
            log(f"      Obstruction: {brodsky_metrics['obstruction_pct']:.1f}%")
            log(f"      Minimum airway: {brodsky_metrics['minimum_airway_diameter_mm']:.1f} mm")
            
            if brodsky_metrics['brodsky_grade'] >= 3:
                log(f"      ⚠️  Severe obstruction (Grade 3-4)")
        else:
            brodsky_metrics = {'brodsky_grade': 0, 'obstruction_pct': 0.0, 'minimum_airway_diameter_mm': 0.0, 'maximum_tonsil_span_mm': 0.0}
        
        # Oropharyngeal airway
        airway_metrics = measure_oropharyngeal_airway(volume_calibrated, spacing, air_threshold=air_threshold)
        log(f"\n   Oropharyngeal airway:")
        log(f"      Minimum diameter: {airway_metrics['minimum_diameter_mm']:.1f} mm")
        log(f"      Mean diameter: {airway_metrics['mean_diameter_mm']:.1f} mm")
        log(f"      Airway volume: {airway_metrics['airway_volume_ml']:.1f} mL")
        
        if airway_metrics['minimum_diameter_mm'] < 5.0 and airway_metrics['minimum_diameter_mm'] > 0:
            log(f"      ⚠️  Narrow airway (<5mm)")
    else:
        log(f"\n   ⚠️  Oropharynx not included in scan coverage")
        tonsil_metrics = {'has_coverage': False}
        brodsky_metrics = None
        airway_metrics = None
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    log("\n" + "=" * 80)
    log("SUMMARY OF FINDINGS")
    log("=" * 80)
    
    findings = []
    
    # OMC findings
    if omc_result['left']['air_fraction'] < 0.12:
        findings.append(f"Left OMC {omc_result['left']['classification']} ({omc_result['left']['air_fraction']*100:.1f}%)")
    if omc_result['right']['air_fraction'] < 0.12:
        findings.append(f"Right OMC {omc_result['right']['classification']} ({omc_result['right']['air_fraction']*100:.1f}%)")
    
    # Sclerosis findings
    if sclerotic_pct >= 5:
        findings.append(f"Sclerotic bone changes ({sclerotic_pct:.1f}%)")
    
    # Cyst findings
    if len(cysts) > 2:
        findings.append(f"Elevated retention cyst count ({len(cysts)})")
    
    # Deep sinus findings
    if sphenoid_opac['left_opacification_grade'] >= 2 or sphenoid_opac['right_opacification_grade'] >= 2:
        findings.append(f"Sphenoid sinus opacification detected")
    
    if sphenoid_opac['fluid_detected']:
        findings.append(f"Sphenoid fluid level present")
    
    # Tonsil findings
    if tonsil_metrics.get('has_coverage') and tonsil_metrics.get('asymmetry_ratio', 0) > 2.0:
        findings.append(f"Tonsillar asymmetry (ratio: {tonsil_metrics['asymmetry_ratio']:.1f})")
    
    if brodsky_metrics and brodsky_metrics.get('brodsky_grade', 0) >= 3:
        findings.append(f"Severe tonsillar obstruction (Grade {brodsky_metrics['brodsky_grade']}/4)")
    
    if findings:
        log("\n   Key Findings:")
        for finding in findings:
            log(f"      • {finding}")
    else:
        log("\n   ✓ No significant pathology detected")
    
    # ========================================================================
    # SAVE RESULTS
    # ========================================================================
    log("\n" + "=" * 80)
    log("SAVING RESULTS")
    log("=" * 80)
    
    # Build comprehensive results dictionary
    results = {
        'analysis_timestamp': datetime.now().isoformat(),
        'patient_id': meta.get('patient_id', 'Unknown'),
        'study_date': meta.get('study_date', 'Unknown'),
        'series_description': meta.get('series_description', ''),
        'scan_parameters': {
            'dimensions': list(volume_raw.shape),
            'spacing_mm': [float(s) for s in spacing],
            'manufacturer': meta.get('manufacturer', 'Unknown'),
        },
        'calibration': {
            'air_anchor_measured_hu': float(calib_meta['air_anchor']['measured_hu']),
            'bone_anchor_measured_hu': float(calib_meta['bone_anchor']['measured_hu']),
            'correction_applied': calib_meta['applied'],
        },
        'volumetric': {
            'air_volume_ml': float(air_volume_ml),
            'soft_tissue_volume_ml': float(tissue_volume_ml),
            'air_fraction': float(air_volume_ml / total_volume_ml),
            'adaptive_air_threshold_hu': float(air_threshold),
        },
        'metrics': {
            'omc_patency': {
                'left_score': float(omc_result['left']['air_fraction'] * 100),
                'left_status': omc_result['left']['classification'],
                'right_score': float(omc_result['right']['air_fraction'] * 100),
                'right_status': omc_result['right']['classification'],
                'method': 'Multi-candidate corridor',
            },
            'bony_changes': {
                'sclerotic_fraction_pct': float(sclerotic_pct),
                'wall_volume_ml': float(shell_volume_ml),
                'bone_mean_hu': float(wall_mean_hu),
                'reference_bone_median': float(ref_median),
                'reference_bone_std': float(ref_std),
                'n_sclerotic_clusters': int(sclerosis_result['n_clusters']),
                'method': 'Z-score (wall shell vs reference bone)',
            },
            'retention_cysts': len(cysts),
            'cyst_details': [
                {
                    'volume_mm3': float(c['volume_mm3']),
                    'centroid': [float(x) for x in c['centroid']],
                    'mean_hu': float(c['mean_hu']),
                }
                for c in cysts
            ],
            'deep_sinuses': {
                'sphenoid': sphenoid_metrics,
                'sphenoid_opacification': sphenoid_opac,
                'posterior_ethmoid': post_eth_metrics,
                'skull_base': skull_base_metrics,
            },
            'oropharynx': {
                'tonsils': tonsil_metrics if tonsil_metrics.get('has_coverage') else None,
                'brodsky': brodsky_metrics if brodsky_metrics else None,
                'airway': airway_metrics if airway_metrics else None,
            },
            'lund_mackay': lm_standard,
            'lund_mackay_conservative': lm_conservative,
        },
        'findings': findings,
    }
    
    # Save to JSON
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"\n✓ Results saved to: {output_json}")
    
    # ========================================================================
    # VALIDATION REFERENCE
    # ========================================================================
    log("\n" + "=" * 80)
    log("VALIDATION REFERENCE")
    log("=" * 80)
    log("\n   Ground truth validation: tests/test_orlando_normal.py")
    log("   Expected for normal scan:")
    log("      • OMC patency: >12% (Patent)")
    log("      • Sclerosis: <5%")
    log("      • Cysts: 0-2")
    log("      • Lund-Mackay: 0-4 (Mild)")
    
    log("\n" + "=" * 80)
    log("ANALYSIS COMPLETE")
    log("=" * 80)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive sinus CT analysis using validated methods',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (default paths)
  python %(prog)s
  
  # Specify custom paths
  python %(prog)s --nifti data/processed/my_scan.nii.gz --output docs/metrics/my_results.json
  
  # Quiet mode (minimal output)
  python %(prog)s --quiet
        """
    )
    
    parser.add_argument(
        '--nifti',
        default='data/processed/sinus_ct.nii.gz',
        help='Path to calibrated NIfTI volume'
    )
    parser.add_argument(
        '--meta',
        default='docs/last_run_meta.json',
        help='Path to scan metadata JSON'
    )
    parser.add_argument(
        '--output',
        default='docs/metrics/clinical_analysis_report.json',
        help='Output JSON path for results'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output'
    )
    
    args = parser.parse_args()
    
    try:
        run_comprehensive_analysis(
            nifti_path=args.nifti,
            meta_path=args.meta,
            output_json=args.output,
            verbose=not args.quiet,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
