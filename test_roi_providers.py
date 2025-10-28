"""
Test the new ROI provider architecture.

This demonstrates how to use both manual and TotalSegmentator providers.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from head_ct_analyzer import HeadCTAnalyzer
from core.roi_provider import create_roi_provider
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

print("="*80)
print("ROI PROVIDER ARCHITECTURE TEST")
print("="*80)
print()

# Test 1: Manual ROI Provider (current implementation)
print("TEST 1: Manual ROI Provider")
print("-"*80)

analyzer_manual = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='manual',
)

print(f"Provider: {analyzer_manual.roi_provider.name}")
print(f"Available structures: {analyzer_manual.roi_provider.get_available_structures()}")
print()

# Analyze deep sinuses
deep_sinus_results = analyzer_manual.analyze_deep_sinuses()
print("\nDEEP SINUS ANALYSIS:")
if deep_sinus_results.get('sphenoid'):
    print(f"  Sphenoid volume: {deep_sinus_results['sphenoid']['sphenoid_volume_ml']:.2f} mL")
    print(f"  Sphenoid air fraction: {deep_sinus_results['sphenoid']['air_fraction']*100:.1f}%")

if deep_sinus_results.get('posterior_ethmoid'):
    print(f"  Posterior ethmoid volume: {deep_sinus_results['posterior_ethmoid']['posterior_ethmoid_volume_ml']:.2f} mL")
    print(f"  Posterior ethmoid air fraction: {deep_sinus_results['posterior_ethmoid']['air_fraction']*100:.1f}%")

if deep_sinus_results.get('skull_base'):
    print(f"  Skull base mean thickness: {deep_sinus_results['skull_base']['mean_thickness_mm']:.2f} mm")
    print(f"  Skull base min thickness: {deep_sinus_results['skull_base']['minimum_thickness_mm']:.2f} mm")

print("\n" + "="*80)
print()

# Test 2: Try TotalSegmentator if available
print("TEST 2: TotalSegmentator Provider (if available)")
print("-"*80)

try:
    analyzer_totalseg = HeadCTAnalyzer(
        nifti_path='data/processed/sinus_ct.nii.gz',
        roi_provider_type='totalsegmentator',
    )
    
    print(f"✓ TotalSegmentator is available!")
    print(f"Provider: {analyzer_totalseg.roi_provider.name}")
    available = analyzer_totalseg.roi_provider.get_available_structures()
    print(f"Available structures: {len(available)}")
    print(f"  Sinuses: {[s for s in available if 'sinus' in s]}")
    print(f"  Bones: {[s for s in available if 'bone' in s or 'skull' in s or 'mandible' in s]}")
    print()
    
    # This would run TotalSegmentator segmentation
    print("Note: Running TotalSegmentator segmentation takes 30-60 seconds on CPU")
    print("      Set device='cuda' for GPU acceleration (~5-10 seconds)")
    
except ImportError:
    print("⚠️  TotalSegmentator not installed")
    print("   Install with: pip install totalsegmentator")
    print("   This enables automatic segmentation of 104 anatomical structures")

print("\n" + "="*80)
print()

# Test 3: Auto mode (tries TotalSegmentator, falls back to manual)
print("TEST 3: Auto Mode")
print("-"*80)

analyzer_auto = HeadCTAnalyzer(
    nifti_path='data/processed/sinus_ct.nii.gz',
    roi_provider_type='auto',
)

print(f"Auto-selected provider: {analyzer_auto.roi_provider.name}")
print()

print("="*80)
print("ARCHITECTURE BENEFITS:")
print("="*80)
print()
print("✓ Plug-and-play ROI providers")
print("  - Switch between manual and TotalSegmentator with one parameter")
print("  - Easy to add new providers (atlas-based, landmark-based)")
print()
print("✓ Centralized ROI logic")
print("  - All ROI placement in one place (core/roi_provider.py)")
print("  - Analysis functions don't need to know about ROI details")
print()
print("✓ Extensible to any head structure")
print("  - TotalSegmentator supports 104 structures")
print("  - Same interface for sinuses, skull, ears, brain, vessels")
print()
print("✓ Future-proof")
print("  - Add custom atlas registration provider")
print("  - Integrate deep learning landmark detection")
print("  - Mix providers (TotalSegmentator for some, manual for others)")
print()
