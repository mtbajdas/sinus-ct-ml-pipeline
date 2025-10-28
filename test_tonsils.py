from src.oropharynx.tonsil_metrics import measure_tonsil_volumes, compute_brodsky_grade
import nibabel as nib

nii = nib.load('data/processed/sinus_ct.nii.gz')
vol = nii.get_fdata()
spacing = nii.header.get_zooms()

print("Testing corrected oropharynx ROI (starting at 75% instead of 60%)...")
print()

tonsils = measure_tonsil_volumes(vol, spacing)
brodsky = compute_brodsky_grade(vol, spacing)

print('Tonsil volumes:')
print(f"  Left: {tonsils['left_tonsil_volume_ml']:.2f} mL")
print(f"  Right: {tonsils['right_tonsil_volume_ml']:.2f} mL")
print(f"  Total: {tonsils['total_tonsil_volume_ml']:.2f} mL")
print()

print('Brodsky grade:')
print(f"  Grade: {brodsky['brodsky_grade']}/4")
print(f"  Obstruction: {brodsky['obstruction_pct']:.1f}%")
print(f"  Min airway: {brodsky['minimum_airway_diameter_mm']:.1f} mm")
print(f"  Max tonsil span: {brodsky['maximum_tonsil_span_mm']:.1f} mm")
