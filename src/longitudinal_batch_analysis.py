"""
Longitudinal Batch Analysis - Process Multiple DICOM Series
Generates comparative clinical reports across timepoints for ENT presentation
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from pipeline import load_dicom_series, save_nifti
from clinical_investigation import run_clinical_investigation


def process_all_series(
    raw_root: Path,
    output_root: Path,
    series_prefix: str = '530',
):
    """
    Process all DICOM series matching pattern in raw_root.
    
    Args:
        raw_root: Path to data/raw/5301/ containing series folders
        output_root: Path to save processed NIfTI files and reports
        series_prefix: Filter series folders starting with this prefix
    """
    # Find all series folders
    series_folders = sorted([
        d for d in raw_root.iterdir() 
        if d.is_dir() and d.name.startswith(series_prefix)
    ])
    
    if not series_folders:
        raise ValueError(f"No series folders found in {raw_root} with prefix {series_prefix}")
    
    print(f"Found {len(series_folders)} series to process:")
    for sf in series_folders:
        print(f"  - {sf.name}")
    
    results = []
    
    for series_folder in series_folders:
        print(f"\n{'='*80}")
        print(f"Processing series: {series_folder.name}")
        print('='*80)
        
        try:
            # Convert DICOM to NIfTI
            volume, affine, meta = load_dicom_series(series_folder)
            
            # Create output paths
            nifti_path = output_root / 'processed' / f'{series_folder.name}.nii.gz'
            meta_path = output_root / 'metadata' / f'{series_folder.name}_meta.json'
            png_path = output_root / 'analysis' / f'{series_folder.name}_clinical.png'
            json_path = output_root / 'analysis' / f'{series_folder.name}_clinical.json'
            
            # Save NIfTI
            nifti_path.parent.mkdir(parents=True, exist_ok=True)
            save_nifti(volume, affine, nifti_path)
            
            # Save metadata
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
            
            # Run clinical investigation
            report = run_clinical_investigation(
                nifti_path=nifti_path,
                meta_path=meta_path,
                out_png=png_path,
                out_json=json_path,
                quiet=False,
            )
            
            # Extract key metrics for comparison
            results.append({
                'series': series_folder.name,
                'patient_id': meta['patient_id'],
                'study_date': meta['study_date'],
                'num_slices': meta['num_slices'],
                'findings_count': len(report['findings']),
                'retention_cysts': report['metrics']['retention_cysts'],
                'omc_left': report['metrics']['omc_patency']['left_score'],
                'omc_right': report['metrics']['omc_patency']['right_score'],
                'sclerotic_pct': report['metrics']['bony_changes']['sclerotic_fraction_pct'],
                'nasopharynx_airway_pct': report['metrics']['nasopharynx']['airway_fraction_pct'],
                'mucosal_2mm_tissue_pct': report['metrics']['mucosal_thickening']['2']['soft_tissue_fraction'] * 100,
            })
            
            print(f"✅ Completed: {series_folder.name}")
            
        except Exception as e:
            print(f"❌ Error processing {series_folder.name}: {e}")
            results.append({
                'series': series_folder.name,
                'error': str(e),
            })
    
    # Generate comparative summary
    summary_path = output_root / 'longitudinal_summary.csv'
    df = pd.DataFrame(results)
    df.to_csv(summary_path, index=False)
    print(f"\n✅ Summary saved to: {summary_path}")
    
    # Generate visualization if we have valid results
    valid_results = [r for r in results if 'error' not in r]
    if len(valid_results) > 1:
        generate_trend_plots(valid_results, output_root / 'trends.png')
    
    return results


def generate_trend_plots(results, output_path):
    """Generate multi-panel trend plots for key metrics."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Longitudinal Sinus Analysis - Trend Overview', fontsize=16, fontweight='bold')
    
    df = pd.DataFrame(results)
    df['series_num'] = df['series'].str.extract(r'(\d+)').astype(int)
    df = df.sort_values('series_num')
    
    # OMC Patency
    axes[0, 0].plot(df['series_num'], df['omc_left'], 'o-', label='Left', linewidth=2, markersize=8)
    axes[0, 0].plot(df['series_num'], df['omc_right'], 's-', label='Right', linewidth=2, markersize=8)
    axes[0, 0].axhline(40, color='red', linestyle='--', alpha=0.5, label='Critical threshold')
    axes[0, 0].set_ylabel('OMC Patency Score (0-100)')
    axes[0, 0].set_title('Ostiomeatal Complex Drainage')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Retention Cysts
    axes[0, 1].bar(df['series_num'], df['retention_cysts'], alpha=0.7, color='coral')
    axes[0, 1].set_ylabel('Number of Cysts')
    axes[0, 1].set_title('Retention Cysts Detection')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # Sclerotic Bone
    axes[0, 2].plot(df['series_num'], df['sclerotic_pct'], 'o-', color='darkred', linewidth=2, markersize=8)
    axes[0, 2].axhline(5, color='orange', linestyle='--', alpha=0.5, label='Mild threshold')
    axes[0, 2].set_ylabel('Sclerotic Bone (%)')
    axes[0, 2].set_title('Chronic Bone Changes')
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)
    
    # Nasopharynx Patency
    axes[1, 0].plot(df['series_num'], df['nasopharynx_airway_pct'], 'o-', color='steelblue', linewidth=2, markersize=8)
    axes[1, 0].axhline(40, color='red', linestyle='--', alpha=0.5, label='Obstruction threshold')
    axes[1, 0].set_ylabel('Airway Patency (%)')
    axes[1, 0].set_title('Nasopharyngeal Airway')
    axes[1, 0].set_xlabel('Series Number')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Mucosal Thickening
    axes[1, 1].plot(df['series_num'], df['mucosal_2mm_tissue_pct'], 'o-', color='green', linewidth=2, markersize=8)
    axes[1, 1].axhline(30, color='orange', linestyle='--', alpha=0.5, label='Abnormal threshold')
    axes[1, 1].set_ylabel('Soft Tissue Fraction (%)')
    axes[1, 1].set_title('Mucosal Thickening (2mm layer)')
    axes[1, 1].set_xlabel('Series Number')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    # Total Findings Count
    axes[1, 2].bar(df['series_num'], df['findings_count'], alpha=0.7, color='mediumpurple')
    axes[1, 2].set_ylabel('Number of Findings')
    axes[1, 2].set_title('Total Clinical Findings')
    axes[1, 2].set_xlabel('Series Number')
    axes[1, 2].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Trend plots saved to: {output_path}")


def generate_ent_summary_report(results, output_path):
    """Generate a concise ENT-focused summary document."""
    valid_results = [r for r in results if 'error' not in r]
    
    report = []
    report.append("# LONGITUDINAL SINUS ANALYSIS - ENT SUMMARY")
    report.append("="*80)
    report.append(f"Analysis Date: {datetime.now().strftime('%B %d, %Y')}")
    report.append(f"Number of Scans Analyzed: {len(valid_results)}")
    report.append("")
    
    if valid_results:
        df = pd.DataFrame(valid_results)
        
        report.append("## KEY FINDINGS SUMMARY")
        report.append("-"*80)
        
        # OMC Analysis
        omc_left_mean = df['omc_left'].mean()
        omc_right_mean = df['omc_right'].mean()
        report.append(f"\n### Ostiomeatal Complex (OMC) Patency")
        report.append(f"- LEFT average: {omc_left_mean:.1f}% ({'OBSTRUCTED' if omc_left_mean < 40 else 'NARROWED' if omc_left_mean < 60 else 'PATENT'})")
        report.append(f"- RIGHT average: {omc_right_mean:.1f}% ({'OBSTRUCTED' if omc_right_mean < 40 else 'NARROWED' if omc_right_mean < 60 else 'PATENT'})")
        
        # Chronic Changes
        sclerosis_mean = df['sclerotic_pct'].mean()
        report.append(f"\n### Chronic Inflammatory Markers")
        report.append(f"- Sclerotic bone changes: {sclerosis_mean:.1f}% ({'SIGNIFICANT' if sclerosis_mean > 5 else 'MINIMAL'})")
        
        # Retention Cysts
        total_cysts = df['retention_cysts'].sum()
        report.append(f"- Total retention cysts detected: {total_cysts}")
        
        # Nasopharynx
        nasopharynx_mean = df['nasopharynx_airway_pct'].mean()
        report.append(f"- Nasopharyngeal airway: {nasopharynx_mean:.1f}% patent ({'OBSTRUCTED' if nasopharynx_mean < 40 else 'PATENT'})")
        
        report.append("\n## CLINICAL INTERPRETATION")
        report.append("-"*80)
        
        # Generate clinical summary based on metrics
        if omc_left_mean < 40 or omc_right_mean < 40:
            report.append("\n⚠️ **BILATERAL OMC OBSTRUCTION DETECTED**")
            report.append("   → High risk for recurrent maxillary/frontal sinusitis")
            report.append("   → Consider FESS (Functional Endoscopic Sinus Surgery)")
        
        if sclerosis_mean > 5:
            report.append("\n⚠️ **CHRONIC OSTEITIS PRESENT**")
            report.append("   → Indicates long-standing inflammatory process (>6 months)")
            report.append("   → Suggests need for sustained anti-inflammatory therapy")
        
        if total_cysts > 0:
            report.append(f"\n⚠️ **RETENTION CYSTS IDENTIFIED ({total_cysts} total)**")
            report.append("   → Evidence of chronic mucous gland obstruction")
            report.append("   → Correlates with recurrent sinus issues")
        
        report.append("\n## RECOMMENDATIONS")
        report.append("-"*80)
        report.append("1. ENT consultation for functional endoscopic evaluation")
        report.append("2. Allergy testing to identify environmental triggers")
        report.append("3. Consider CT-guided biopsy if atypical findings present")
        report.append("4. Long-term nasal steroid therapy + saline irrigation")
        report.append("5. Follow-up imaging in 3-6 months to track progression")
        
        report.append("\n" + "="*80)
        report.append("END OF REPORT")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"\n✅ ENT summary report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Batch longitudinal analysis of DICOM series")
    parser.add_argument('--raw-root', type=Path, default=Path('data/raw/5301'),
                        help='Root directory containing DICOM series folders')
    parser.add_argument('--output-root', type=Path, default=Path('data/longitudinal'),
                        help='Output directory for processed files and reports')
    parser.add_argument('--series-prefix', default='530',
                        help='Filter series folders by prefix')
    args = parser.parse_args()
    
    results = process_all_series(args.raw_root, args.output_root, args.series_prefix)
    generate_ent_summary_report(results, args.output_root / 'ENT_SUMMARY_REPORT.md')
    
    print(f"\n{'='*80}")
    print("BATCH ANALYSIS COMPLETE")
    print('='*80)
    print(f"Processed {len(results)} series")
    print(f"Output directory: {args.output_root}")
    print("\nNext steps:")
    print("1. Review: data/longitudinal/ENT_SUMMARY_REPORT.md")
    print("2. View trends: data/longitudinal/trends.png")
    print("3. Check details: data/longitudinal/longitudinal_summary.csv")


if __name__ == '__main__':
    main()
"""
DEPRECATED MODULE
-----------------
This script was created under the assumption of multiple longitudinal scans.
The current dataset contains multiple series from a single scan session.

Please use the single-scan workflow:
    - docs/SINGLE_SCAN_ENT_PLAN.md
    - src/compare_series.py
    - src/clinical_investigation.py

This module intentionally raises at import to prevent accidental use.
"""

raise RuntimeError(
        "longitudinal_batch_analysis.py is deprecated for this repository; use the single-scan tools instead."
)
