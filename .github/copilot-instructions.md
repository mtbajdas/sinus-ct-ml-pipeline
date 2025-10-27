# Sinus CT ML Pipeline - AI Agent Instructions

## Project Overview
This is a modular medical imaging pipeline for analyzing personal sinus CT scans. Core workflow: DICOM → NIfTI → segmentation → radiomics feature extraction. The project scaffolds MONAI deep learning models and PyRadiomics quantitative analysis for tracking chronic sinus inflammation.

## Architecture & Data Flow

### Primary Pipeline (`src/pipeline.py`)
- **Input**: Raw DICOM series in `data/raw/<study_name>/`
- **Processing**: Automatic Hounsfield Unit conversion using `RescaleSlope`/`RescaleIntercept`
- **Outputs**: 
  - `data/processed/sinus_ct.nii.gz` (standardized volume)
  - `docs/last_run_meta.json` (study metadata with spacing, patient ID, slice count)
  - Optional: segmentation masks and radiomics features

### Key Integration Points
- **MONAI**: 3D U-Net segmentation via `SegmentationModel` class with sliding-window inference
- **PyRadiomics**: Feature extraction using generated/provided masks
- **Plotly**: 3D mesh visualization via marching cubes (`src/visualize_3d.py`)

## Critical Development Patterns

### Medical Imaging Conventions
- **Hounsfield Units**: Air ≈ -1000 HU, soft tissue ≈ 0 HU. Use `-400` to `-300` HU for air cavity visualization
- **Spacing**: Always preserve voxel spacing from DICOM headers for accurate geometric calculations
- **Slice Ordering**: DICOM series sorted by `ImagePositionPatient[2]` (z-position), fallback to `InstanceNumber`

### MONAI Model Integration
```python
# Standard preprocessing pipeline (hardcoded in SegmentationModel._preprocess)
clipped = np.clip(volume, -1000, 400)  # Nasal tissue range
norm = (clipped + 1000.0) / 1400.0     # [0, 1] normalization
```
- ROI size: `(96, 96, 96)` default for sliding-window inference
- Model architecture: 3D U-Net with channels `[16, 32, 64, 128, 256]`, binary output (background vs sinus/mucosa)

### File Organization Conventions
- **Models**: Store PyTorch weights as `models/sinus_unet.pth` (auto-detected by pipeline)
- **Configs**: YAML files in `configs/` follow MONAI patterns (see `monai_unet_config.yaml`)
- **Metadata**: Always persist run metadata to `docs/last_run_meta.json` for provenance tracking
- **Features**: Radiomics JSON outputs go to `docs/metrics/*.json`

## Essential Commands

### Basic Pipeline Execution
```bash
python src/pipeline.py --dicom-dir data/raw/my_ct --output-nifti data/processed/sinus_ct.nii.gz --view-step 20
```

### Full ML Pipeline (with trained model)
```bash
python src/pipeline.py --dicom-dir data/raw/my_ct --seg-weights models/sinus_unet.pth --radiomics-json docs/metrics/features.json
```

### 3D Visualization
```bash
python src/visualize_3d.py --nifti data/processed/sinus_ct.nii.gz --iso -300 --downsample 2
```

## Development Guidelines

### Adding New Models
- Implement models as classes with `predict()` method returning `SegmentationResult`
- Use MONAI's `sliding_window_inference` for 3D volumes
- Store model metadata in prediction results for provenance

### Working with DICOM Data
- Handle missing `ImagePositionPatient` gracefully (fallback to `InstanceNumber`)
- Install `pylibjpeg` packages for compressed DICOM support
- Use `--log-level DEBUG` for verbose DICOM parsing output

### PyRadiomics Integration
- Requires both image and mask NIfTI files
- Features auto-serialize to JSON with numpy type conversion
- Default feature set includes first-order, GLCM, GLRLM, GLSZM, GLDM, NGTDM

### Troubleshooting Patterns
- **PyRadiomics install**: If numpy import fails, run `pip install --no-build-isolation PyRadiomics==3.0.1` first
- **DICOM series selection**: Pipeline auto-selects largest series by slice count, override with `--series-uid`
- **Memory management**: Use `--downsample 2` for large volumes in visualization

## Testing Approach
- Use `--view-step N` for visual QA of slice ordering and intensity ranges
- Verify HU conversion by checking air (-1000) and soft tissue (0) regions
- Test segmentation models on known anatomical landmarks (nasal septum, sinuses)

## Extension Points
- Add new transforms in `configs/` following MONAI patterns
- Implement longitudinal tracking by comparing `docs/metrics/` outputs
- Create analysis notebooks in `notebooks/` for comparative studies with literature values