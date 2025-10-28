"""
Quick test to see what ear/brain structures are available in your CT scan.

Run this to discover:
1. Which structures TotalSegmentator can segment from your scan
2. What volumes/measurements are possible
3. Coverage extent (does scan include full brain?)
"""
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.roi_provider import create_roi_provider


def test_structure_availability():
    """Test what structures are available in your CT scan."""
    
    print("="*80)
    print("EAR & BRAIN STRUCTURE AVAILABILITY TEST")
    print("="*80)
    print()
    
    # Load your CT
    nifti_path = Path('data/processed/sinus_ct.nii.gz')
    if not nifti_path.exists():
        print(f"❌ CT scan not found: {nifti_path}")
        print("   Run pipeline.py first to generate the NIfTI file")
        return
    
    print(f"Loading {nifti_path}")
    nii = nib.load(nifti_path)
    volume = nii.get_fdata()
    spacing = nii.header.get_zooms()
    
    print(f"Volume shape: {volume.shape}")
    print(f"Spacing: {spacing} mm")
    print(f"Physical size: {volume.shape[0]*spacing[0]:.0f} x {volume.shape[1]*spacing[1]:.0f} x {volume.shape[2]*spacing[2]:.0f} mm")
    print()
    
    # Create TotalSegmentator provider
    print("Initializing TotalSegmentator...")
    try:
        provider = create_roi_provider('totalsegmentator')
        print("✓ TotalSegmentator available")
    except ImportError as e:
        print(f"❌ TotalSegmentator not installed: {e}")
        print("   Install with: pip install totalsegmentator")
        return
    print()
    
    # Test structures of interest
    test_structures = [
        # Ear structures
        ('temporal_bone_left', 'Left temporal bone'),
        ('temporal_bone_right', 'Right temporal bone'),
        
        # Brain structures
        ('brain', 'Brain parenchyma'),
        ('brainstem', 'Brainstem'),
        ('pituitary_gland', 'Pituitary gland'),
        
        # Reference structures
        ('skull', 'Skull'),
        ('sphenoid_sinus', 'Sphenoid sinus'),
    ]
    
    print("Testing structure availability (this takes 30-60 seconds on CPU)...")
    print("Note: First run generates segmentation, subsequent runs use cache")
    print()
    
    voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    
    results = []
    for struct_name, display_name in test_structures:
        print(f"Testing: {display_name}...", end=' ', flush=True)
        
        try:
            mask = provider.get_roi_mask(volume, spacing, struct_name)
            
            if mask is not None and mask.sum() > 0:
                volume_ml = mask.sum() * voxel_volume_mm3 / 1000
                roi_hu = volume[mask > 0]
                mean_hu = roi_hu.mean()
                
                # Get bounding box
                coords = np.argwhere(mask)
                z_min, z_max = coords[:, 0].min(), coords[:, 0].max()
                z_range_mm = (z_max - z_min) * spacing[0]
                
                print(f"✓ Found")
                print(f"    Volume: {volume_ml:.1f} mL")
                print(f"    Mean HU: {mean_hu:.0f}")
                print(f"    Z-range: slices {z_min}-{z_max} ({z_range_mm:.0f} mm)")
                
                results.append({
                    'name': display_name,
                    'found': True,
                    'volume_ml': volume_ml,
                    'mean_hu': mean_hu,
                    'z_range': (z_min, z_max),
                })
            else:
                print("❌ Not found in scan")
                results.append({
                    'name': display_name,
                    'found': False,
                })
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'name': display_name,
                'found': False,
                'error': str(e),
            })
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    # Categorize results
    ear_structures = [r for r in results if 'temporal' in r['name'].lower()]
    brain_structures = [r for r in results if any(x in r['name'].lower() for x in ['brain', 'pituitary'])]
    
    print("👂 EAR STRUCTURES:")
    found_ear = [s for s in ear_structures if s['found']]
    if found_ear:
        for s in found_ear:
            print(f"  ✓ {s['name']}: {s['volume_ml']:.1f} mL")
    else:
        print("  ❌ No ear structures found")
        print("     Scan may not extend to temporal bones")
    print()
    
    print("🧠 BRAIN STRUCTURES:")
    found_brain = [s for s in brain_structures if s['found']]
    if found_brain:
        for s in found_brain:
            print(f"  ✓ {s['name']}: {s['volume_ml']:.1f} mL")
    else:
        print("  ❌ No brain structures found")
        print("     Scan likely focused on sinuses only (common)")
    print()
    
    # Coverage assessment
    print("📏 SCAN COVERAGE ASSESSMENT:")
    all_found = [r for r in results if r['found']]
    if all_found:
        all_z_coords = []
        for r in all_found:
            if 'z_range' in r:
                all_z_coords.extend(r['z_range'])
        
        if all_z_coords:
            z_min = min(all_z_coords)
            z_max = max(all_z_coords)
            coverage_mm = (z_max - z_min) * spacing[0]
            
            print(f"  Slice range: {z_min} to {z_max} (of {volume.shape[0]} total)")
            print(f"  Coverage: {coverage_mm:.0f} mm")
            
            # Interpretation
            if z_max - z_min > 150:  # More than 150 slices
                print(f"  → Extensive coverage: Should include brain, sinuses, and temporal bones")
            elif z_max - z_min > 100:
                print(f"  → Good coverage: Likely includes sinuses and upper skull")
            else:
                print(f"  → Limited coverage: Focused on sinus region (typical for sinus CT)")
    print()
    
    # Recommendations
    print("="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print()
    
    if any(s['found'] for s in ear_structures):
        print("✅ You can analyze EAR structures:")
        print("   - Temporal bone volume and density")
        print("   - Mastoid air cell pneumatization")
        print("   - Left-right asymmetry")
        print("   - Potential mastoiditis screening")
        print()
        print("   See: docs/EAR_BRAIN_EXPANSION.md for code examples")
        print()
    
    if any(s['found'] for s in brain_structures):
        print("✅ You can analyze BRAIN structures:")
        print("   - Total brain volume")
        print("   - White/gray matter distribution (HU-based)")
        print("   - Density abnormalities")
        print("   - Atrophy screening")
        print()
        print("   See: docs/EAR_BRAIN_EXPANSION.md for code examples")
        print()
    
    if not any(s['found'] for s in ear_structures + brain_structures):
        print("ℹ️  Your scan is focused on SINUSES (typical):")
        print("   - Full sinus analysis available (maxillary, frontal, ethmoid, sphenoid)")
        print("   - Skull base analysis")
        print("   - Oropharynx/airway analysis")
        print()
        print("   For ear/brain analysis, you would need a scan with wider coverage")
        print("   (e.g., 'head CT' vs 'sinus CT')")
        print()
    
    print("="*80)
    print()


if __name__ == '__main__':
    test_structure_availability()
