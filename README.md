# Sinus CT ML Pipeline

Scaffold for loading personal sinus CT scans, converting them to analysis-friendly formats, and preparing quantitative ML workflows (segmentation + radiomics). The code is intentionally modular so you can plug in MONAI models, PyRadiomics feature extraction, and Jupyter notebooks as the project grows.

## Repo layout

- `src/pipeline.py` – command-line utility to load DICOM folders, export NIfTI volumes, dump metadata, and optionally preview slices.
- `data/` – place raw DICOM series (`raw/`) and generated assets (e.g., `processed/sinus_ct.nii.gz`). Empty `.gitkeep` markers keep folders under version control.
- `models/` – store trained MONAI/PyTorch weights.
- `notebooks/` – exploratory analysis or training notebooks.
- `docs/` – reference material; the pipeline persists run metadata to `docs/last_run_meta.json`.
- `configs/` – future training/evaluation configs.

## Prerequisites

- Python 3.10+ recommended (tested on 3.11).
- CUDA-capable GPU optional but helpful for 3D segmentation training.
- (Optional) [3D Slicer](https://www.slicer.org/) for interactive visualization.

Install dependencies once you create and activate a virtual environment:

```bash
pip install -r requirements.txt
```

## Quick start

1. Copy your DICOM CT study into `data/raw/<study_name>`.
2. Run the pipeline to convert to NIfTI and capture metadata (adds optional segmentation + radiomics when you supply weights):

```bash
python src/pipeline.py ^
  --dicom-dir data/raw/my_ct ^
  --output-nifti data/processed/sinus_ct.nii.gz ^
  --metadata-json docs/last_run_meta.json ^
  --view-step 20 ^
  --seg-weights models/sinus_unet.pth ^
  --mask-output data/processed/sinus_mask.nii.gz ^
  --radiomics-json docs/metrics/sinus_features.json
```

Key outputs:

- `data/processed/sinus_ct.nii.gz` – ready for MONAI, PyRadiomics, or 3D Slicer.
- `docs/last_run_meta.json` – study metadata snapshot (spacing, patient ID, slice count).
- Optional matplotlib preview windows every `view-step` slices for QA.
- Intensities are automatically converted to Hounsfield Units using `RescaleSlope`/`RescaleIntercept`, so downstream thresholds (e.g., -400 HU for air cavities) behave consistently.
- If `--seg-weights` is provided, the MONAI U-Net inference helper runs a sliding-window pass, saves the predicted mask, and records provenance inside `docs/last_run_meta.json`.
- If `--radiomics-json` is provided, PyRadiomics extracts the default feature set (first-order, GLCM, etc.) using the generated mask (or `--radiomics-mask` if you point to an existing one) and writes a JSON report.

## Next steps

1. **Segmentation:** implement `SegmentationModel` in `src/pipeline.py` using MONAI (e.g., 3D U-Net) trained on an open sinus CT dataset; persist predicted masks alongside the NIfTI volume.
2. **Radiomics:** feed the exported image + mask into PyRadiomics to quantify mucosal volume, air-fraction ratios, and texture metrics for specific sinuses.
3. **Notebooks:** create exploratory workflows inside `notebooks/` to compare your scan’s metrics with published norms, track longitudinal changes, or visualize ostial narrowing.
4. **Automation:** add CLI flags or config files (drop under `configs/`) to run segmentation + radiomics end-to-end once models are in place.

### 3D visualization

Use the Plotly-based helper to generate an interactive sinus mesh:

```bash
python src/visualize_3d.py ^
  --nifti data/processed/sinus_ct.nii.gz ^
  --iso -300 ^
  --downsample 2 ^
  --output docs/interactive_mesh.html
```

- `--iso` controls which density surface to render (air ≈ -1000 HU, soft tissue ≈ 0 HU). Values around `-400` highlight air cavities, `0` highlights mucosal surfaces.
- `--downsample` speeds up marching cubes on 512³ volumes by averaging neighboring voxels; set to `1` for full resolution.
- Open the resulting HTML file in any browser to orbit, zoom, or slice through the reconstructed model.

### Segmentation + radiomics roadmap

- `configs/monai_unet_config.yaml` is a starter template for a MONAI 3D U-Net (single-channel CT, binary mask). Update dataset paths, label schema, and augmentations as you connect an open dataset.
- Train the model using MONAI (e.g., a slim training script or notebook) and save the weights to `models/sinus_unet.pth`. The CLI automatically loads this file when you pass `--seg-weights`.
- Feed `(image, mask)` pairs into PyRadiomics (already wired into `pipeline.py`) to capture mucosal volumes per sinus plus texture markers. Store these metrics in `docs/metrics/*.json` for longitudinal tracking.
- For experiments, spin up notebooks under `notebooks/` (Jupyter is already in `requirements.txt`) to compare your metrics against literature values or visualize ostial narrowing trends.

## Troubleshooting

- If the DICOM slices lack `ImagePositionPatient`, the loader falls back to `InstanceNumber`. Confirm slice order via the viewer.
- Some scanners output compressed DICOMs; install `pylibjpeg` if you encounter codec errors (`pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg`).
- Use `--log-level DEBUG` for verbose output during ingestion.
- PyRadiomics' build currently assumes numpy is already available. If `pip install -r requirements.txt` fails with `ModuleNotFoundError: No module named 'numpy'` while building PyRadiomics, run `pip install --no-build-isolation PyRadiomics==3.0.1` first, then re-run the requirements install.

## Clinical report and artifacts

- ENT handoff (structured Markdown): `docs/ENT_CONSULTATION_PACKAGE.md`
- Polished HTML report (embed-ready): `docs/report/ent_report.html`
- Key figures: `docs/omc_overlay_comparison.png`, `docs/clinical_5309.png`, `docs/literature_comparison.png`
- Interactive model: `docs/3d_model_5309.html`
- Metrics JSONs: `docs/metrics/clinical_5309.json`, `docs/metrics/clinical_analysis_report.json`

To regenerate the HTML report after updating metrics or figures:

```powershell
python src/generate_ent_report.py
```

Contributions and experiments welcome—this repository quantifies chronic sinus inflammation and frames ENT discussions with objective data.
