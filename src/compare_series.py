"""
Multi-Series Comparison - Analyze different acquisition protocols from same scan
Helps identify which series gives best pathology visualization
"""
import argparse
from pathlib import Path
import json
import nibabel as nib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from pipeline import load_dicom_series


def analyze_series_differences(raw_root: Path, output_dir: Path):
    """
    Compare different DICOM series from same CT scan session.
    Identifies optimal series for specific anatomical features.
    """
    series_folders = sorted([d for d in raw_root.iterdir() if d.is_dir()])
    
    print(f"Found {len(series_folders)} series in scan:")
    
    results = []
    
    for sf in series_folders:
        print(f"\nAnalyzing series: {sf.name}")
        
        try:
            volume, affine, meta = load_dicom_series(sf)
            
            # Analyze HU characteristics
            air_voxels = (volume < -400).sum()
            soft_tissue = ((volume > -100) & (volume < 100)).sum()
            bone_voxels = (volume > 200).sum()
            
            results.append({
                'series': sf.name,
                'num_slices': meta['num_slices'],
                'spacing_z': meta['spacing'][2],
                'hu_min': float(volume.min()),
                'hu_max': float(volume.max()),
                'hu_mean': float(volume.mean()),
                'hu_std': float(volume.std()),
                'air_fraction': air_voxels / volume.size,
                'tissue_fraction': soft_tissue / volume.size,
                'bone_fraction': bone_voxels / volume.size,
                'series_uid': meta['series_uid'],
            })
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Create comparison table
    df = pd.DataFrame(results)
    
    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / 'series_comparison.csv'
    df.to_csv(csv_path, index=False)
    
    # Generate comparison plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('DICOM Series Comparison - Same CT Scan', fontsize=14, fontweight='bold')
    
    series_names = df['series'].astype(str)
    
    # HU range comparison
    axes[0, 0].bar(range(len(df)), df['hu_max'] - df['hu_min'], alpha=0.7)
    axes[0, 0].set_xticks(range(len(df)))
    axes[0, 0].set_xticklabels(series_names, rotation=45, ha='right')
    axes[0, 0].set_ylabel('HU Range')
    axes[0, 0].set_title('Intensity Dynamic Range')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    # Slice count
    axes[0, 1].bar(range(len(df)), df['num_slices'], alpha=0.7, color='coral')
    axes[0, 1].set_xticks(range(len(df)))
    axes[0, 1].set_xticklabels(series_names, rotation=45, ha='right')
    axes[0, 1].set_ylabel('Number of Slices')
    axes[0, 1].set_title('Series Resolution')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # Tissue fractions
    width = 0.25
    x = np.arange(len(df))
    axes[1, 0].bar(x - width, df['air_fraction']*100, width, label='Air', alpha=0.7)
    axes[1, 0].bar(x, df['tissue_fraction']*100, width, label='Soft Tissue', alpha=0.7)
    axes[1, 0].bar(x + width, df['bone_fraction']*100, width, label='Bone', alpha=0.7)
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(series_names, rotation=45, ha='right')
    axes[1, 0].set_ylabel('Fraction (%)')
    axes[1, 0].set_title('Tissue Distribution')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    # Slice thickness
    axes[1, 1].bar(range(len(df)), df['spacing_z'], alpha=0.7, color='steelblue')
    axes[1, 1].set_xticks(range(len(df)))
    axes[1, 1].set_xticklabels(series_names, rotation=45, ha='right')
    axes[1, 1].set_ylabel('Slice Thickness (mm)')
    axes[1, 1].set_title('Z-Axis Resolution')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plot_path = output_dir / 'series_comparison.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    
    # Generate recommendations
    print(f"\n{'='*80}")
    print("SERIES SELECTION RECOMMENDATIONS")
    print('='*80)
    
    # Best for soft tissue detail
    best_tissue = df.loc[df['tissue_fraction'].idxmax()]
    print(f"\n✅ Best for SOFT TISSUE visualization: {best_tissue['series']}")
    print(f"   - {best_tissue['tissue_fraction']*100:.2f}% tissue fraction")
    
    # Best for bone detail
    best_bone = df.loc[df['bone_fraction'].idxmax()]
    print(f"\n✅ Best for BONE/SCLEROSIS analysis: {best_bone['series']}")
    print(f"   - {best_bone['bone_fraction']*100:.2f}% bone fraction")
    
    # Highest resolution
    thinnest_slice = df.loc[df['spacing_z'].idxmin()]
    print(f"\n✅ Highest RESOLUTION: {thinnest_slice['series']}")
    print(f"   - {thinnest_slice['spacing_z']:.2f}mm slice thickness")
    print(f"   - {thinnest_slice['num_slices']} slices")
    
    # Most slices
    most_slices = df.loc[df['num_slices'].idxmax()]
    print(f"\n✅ Most COMPREHENSIVE coverage: {most_slices['series']}")
    print(f"   - {most_slices['num_slices']} slices")
    
    print(f"\n{'='*80}")
    print(f"Results saved to:")
    print(f"  - {csv_path}")
    print(f"  - {plot_path}")
    print('='*80)
    
    return df


def main():
    parser = argparse.ArgumentParser(description="Compare DICOM series from same CT scan")
    parser.add_argument('--raw-root', type=Path, default=Path('data/raw/5301'),
                        help='Directory containing multiple series folders')
    parser.add_argument('--output-dir', type=Path, default=Path('docs/series_comparison'),
                        help='Output directory for comparison results')
    args = parser.parse_args()
    
    analyze_series_differences(args.raw_root, args.output_dir)


if __name__ == '__main__':
    main()
