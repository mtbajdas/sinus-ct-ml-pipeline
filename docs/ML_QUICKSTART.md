# ML & Quantitative Analysis - Quick Start Guide

This guide covers the new ML modeling and quantitative analysis capabilities added to the sinus CT pipeline.

## What's New

### 1. Synthetic Data Generation (`src/synthetic_generator.py`)
Generate realistic training data with controlled pathology patterns:

```bash
# Generate 50 mixed pathology samples
python src/synthetic_generator.py \
  --output-dir data/synthetic \
  --num-samples 50 \
  --pathology mixed \
  --severity mixed \
  --seed 42
```

**Pathology types**: `normal`, `mucosal` (thickening), `fluid` (air-fluid levels), `opacified` (complete)

**Severity levels**: `mild`, `moderate`, `severe`

### 2. MONAI 3D U-Net Training (`src/train_segmentation.py`)
Train deep learning models for automated sinus segmentation:

```bash
python src/train_segmentation.py \
  --config configs/monai_unet_config.yaml \
  --data-dir data/synthetic \
  --output-dir models/sinus_unet_v1 \
  --train-split 0.8
```

**Requirements**: 
- GPU recommended (CUDA-capable)
- Adjust `max_epochs` in `configs/monai_unet_config.yaml` for quick testing

### 3. Quantitative Analysis (`src/quantitative_analysis.py`)
Extract comprehensive metrics from CT scans:

```bash
python src/quantitative_analysis.py \
  --image data/processed/sinus_ct.nii.gz \
  --output docs/metrics/quantitative_report.json \
  --patient-id 19420531 \
  --study-date 20250418
```

**Metrics extracted**:
- Volumetric: Total sinus volume, air vs tissue breakdown
- Texture: PyRadiomics features (entropy, GLCM, GLRLM)
- Asymmetry: Left-right symmetry scoring
- Per-sinus volumes (if multi-label mask provided)

### 4. Interactive Notebooks

**Data Exploration** (`notebooks/01_data_exploration.ipynb`):
- HU distribution analysis
- Anatomical slice visualization
- ROI identification
- Training patch extraction

**Complete ML Workflow** (`notebooks/02_complete_ml_workflow.ipynb`):
- End-to-end pipeline demonstration
- Synthetic data → Training → Inference → Analysis
- Longitudinal tracking setup
- 3D visualization integration

## Quick Workflow

### For Training a Model:

1. **Generate synthetic data**:
   ```bash
   python src/synthetic_generator.py --num-samples 100 --output-dir data/synthetic
   ```

2. **Train model** (requires GPU):
   ```bash
   python src/train_segmentation.py --data-dir data/synthetic --output-dir models/run1
   ```

3. **Run inference** on real data:
   ```bash
   python src/pipeline.py \
     --dicom-dir data/raw/5301/5303 \
     --seg-weights models/run1/best_model.pth \
     --mask-output data/processed/pred_mask.nii.gz
   ```

### For Analysis Only:

1. **Process DICOM to NIfTI**:
   ```bash
   python src/pipeline.py --dicom-dir data/raw/5301/5303 --output-nifti data/processed/ct.nii.gz
   ```

2. **Run quantitative analysis**:
   ```bash
   python src/quantitative_analysis.py --image data/processed/ct.nii.gz --output docs/metrics/report.json
   ```

3. **Generate 3D visualization**:
   ```bash
   python src/visualize_3d.py --nifti data/processed/ct.nii.gz --output docs/viz.html
   ```

## Longitudinal Tracking

To track changes over time:

1. Run analysis on each timepoint with unique output names:
   ```bash
   python src/quantitative_analysis.py \
     --image data/processed/scan_2024_01.nii.gz \
     --output docs/metrics/report_2024_01.json \
     --study-date 20240115
   
   python src/quantitative_analysis.py \
     --image data/processed/scan_2025_04.nii.gz \
     --output docs/metrics/report_2025_04.json \
     --study-date 20250418
   ```

2. Use the longitudinal tracking notebook to visualize trends

## Synthetic Data Details

The generator creates anatomically-plausible CT volumes with:

- **Normal anatomy**: Skull, brain, nasal cavity, 7 sinus regions
- **Mucosal thickening**: Configurable thickness (2-8mm)
- **Air-fluid levels**: Gravity-dependent fluid accumulation
- **Complete opacification**: Chronic sinusitis simulation

Each sample includes:
- Image: `data/synthetic/images/sample_XXX_pathology_severity.nii.gz`
- Mask: `data/synthetic/masks/sample_XXX_pathology_severity.nii.gz`

## Model Architecture

3D U-Net configuration (see `configs/monai_unet_config.yaml`):
- **Input**: Single-channel CT (HU range: -1000 to 400)
- **Output**: 2 classes (background vs sinus/pathology)
- **Patch size**: 96×96×96
- **Channels**: [16, 32, 64, 128, 256]
- **Loss**: Dice + Cross-Entropy

## Clinical Metrics Reference

### Normal Sinus Volumes (Literature Values)
- Maxillary: 12-25 mL each
- Frontal: 4-10 mL each  
- Ethmoid: 3-6 mL each
- Sphenoid: 5-8 mL total

### Pathology Thresholds
- **Mucosal thickening**: >3mm considered abnormal
- **Air fraction**: <50% suggests significant disease
- **Asymmetry**: >30% warrants clinical attention

## Troubleshooting

**GPU out of memory during training**:
- Reduce `batch_size` in config (try 1)
- Reduce `patch_size` to `[64, 64, 64]`
- Use `--downsample` flag in visualization

**PyRadiomics feature extraction fails**:
- Ensure mask has at least one positive voxel
- Check that image and mask have compatible dimensions
- Try regenerating mask with different threshold

**Synthetic data looks unrealistic**:
- Adjust sinus region centers in `synthetic_generator.py`
- Modify HU intensity ranges for different tissues
- Increase Gaussian smoothing sigma for more blur

## Next Development Steps

1. **Multi-class segmentation**: Label each sinus separately (7 classes)
2. **Ostial patency scoring**: Quantify drainage pathway obstruction
3. **Symptom correlation**: Link metrics to clinical outcomes
4. **DICOM SR export**: Generate structured reports for PACS
5. **Web dashboard**: Streamlit app for easy analysis

## Integration with Existing Pipeline

All new tools integrate seamlessly with the original pipeline:

```bash
# Full end-to-end with all features
python src/pipeline.py \
  --dicom-dir data/raw/my_ct \
  --output-nifti data/processed/ct.nii.gz \
  --seg-weights models/sinus_unet.pth \
  --mask-output data/processed/mask.nii.gz \
  --radiomics-json docs/metrics/features.json \
  --view-step 20
```

This single command:
1. Loads DICOM series
2. Converts to NIfTI with HU calibration
3. Runs 3D U-Net segmentation
4. Extracts PyRadiomics features
5. Shows slice previews for QA
6. Saves all metadata

All outputs are timestamped and tracked in `docs/last_run_meta.json`.
