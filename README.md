# Head CT Analysis Pipeline# Medical CT Analysis Pipeline



**Sinus + Brain CT Analysis** — Modular pipeline for quantitative head CT analysis with physics-based calibration and clinical validation. Focus areas: sinus pathology (OMC patency, sclerosis, cysts) and brain assessment (hemorrhage, midline shift, stroke).**Modular, Validated, Extensible** — A physics-based pipeline for quantitative CT image analysis with clinical validation. Currently implements sinus CT analysis with HU calibration, OMC patency measurement, and pathology detection. Designed for easy expansion to lung, liver, cardiac, brain, and musculoskeletal CT.



[![Validation](https://img.shields.io/badge/validation-passing-brightgreen)](tests/test_orlando_normal.py)[![Validation](https://img.shields.io/badge/validation-passing-brightgreen)](tests/test_orlando_normal.py)

[![Calibration](https://img.shields.io/badge/HU%20calibration-physics--based-blue)](src/calibration/)[![Calibration](https://img.shields.io/badge/HU%20calibration-physics--based-blue)](src/calibration/)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)[![Docs](https://img.shields.io/badge/docs-comprehensive-orange)](METHODS.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

---

## 🎯 Key Features

## 🎯 Key Features

### ✅ **Physics-Based Calibration**

### ✅ **Sinus Analysis (Current)**- Automatic HU drift correction using air/bone anchors

- **OMC Patency**: Multi-candidate corridor detection with clinical classification- Adaptive tissue thresholding via histogram analysis

- **Sclerosis Detection**: Z-score based wall thickening quantification- Per-scan calibration metadata tracking

- **Retention Cysts**: Strict anatomical rules for fluid-filled lesions

- **Mucosal Thickening**: Volumetric inflammation measurement### 🔬 **Validated Measurements**

- **Clinical Scoring**: Lund-Mackay with conservative variant- OMC patency with multi-candidate corridor search

- Sclerotic bone detection (z-score + wall shell)

### 🧠 **Brain Analysis (Future)**- Retention cyst detection (strict anatomical rules)

- **Hemorrhage Detection**: Acute blood identification (epidural, subdural, SAH, IPH, IVH)- Clinical scoring (Lund-Mackay with conservative variant)

- **Midline Shift**: Mass effect quantification (deviation from falx cerebri)

- **Stroke Assessment**: Hypodense region detection and volume estimation### 🧩 **Modular Architecture**

- **Ventricular Sizing**: CSF space measurement for hydrocephalus```

- **Skull/Bone**: Fracture detection, pneumocephalussrc/

├── calibration/          # HU correction, adaptive thresholds

### 🔧 **Core Infrastructure**├── metrics/              # Anatomical measurements, pathology detection

- **Physics-Based HU Calibration**: Air/bone anchor detection with linear correction├── reporting/            # Clinical report generation

- **Adaptive Thresholding**: Histogram-based tissue segmentation├── visualization/        # 3D rendering, interactive plots

- **3D Visualization**: Interactive Plotly mesh rendering└── core/                 # DICOM I/O, preprocessing utilities

- **Modular Design**: Clean separation between sinus and brain modules```



---### 📊 **Ground Truth Validated**

- Test harness with known-normal scan

## 🚀 Quick Start- 4/4 validation checks passing

- Aligns with radiologist reports

### Installation

```bash---

git clone https://github.com/mtbajdas/sinus-ct-ml-pipeline.git

cd sinus-ct-ml-pipeline## 🚀 Quick Start

pip install -r requirements.txt

```### Installation

```bash

### Sinus Analysis# Clone and setup

```bashgit clone https://github.com/mtbajdas/sinus-ct-ml-pipeline.git

# Basic pipeline with visualizationcd sinus-ct-ml-pipeline

python src/pipeline.py \pip install -r requirements.txt

  --dicom-dir data/raw/my_scan \```

  --output-nifti data/processed/sinus_ct.nii.gz \

  --view-step 20### Basic Pipeline

```bash

# Full clinical analysis# Convert DICOM to NIfTI with calibration

python src/clinical_investigation.py \python src/pipeline.py \

  --nifti data/processed/sinus_ct.nii.gz \  --dicom-dir data/raw/my_scan \

  --output docs/metrics/clinical.json  --output-nifti data/processed/sinus_ct.nii.gz \

  --view-step 20

# Generate ENT report```

python src/generate_ent_report.py

### Full Analysis with Reports

# 3D visualization```bash

python src/visualize_3d.py --nifti data/processed/sinus_ct.nii.gz --iso -300# Run complete clinical investigation

```python src/clinical_investigation.py \

  --nifti data/processed/sinus_ct.nii.gz \

### Validation  --output docs/metrics/clinical.json

```bash

python tests/test_orlando_normal.py# Generate ENT consultation report

```python src/generate_ent_report.py

```

**Expected:**

```### Validation Test

[PASS]: HU Calibration```bash

[PASS]: OMC Patency (Patent bilaterally: L=14.6%, R=18.9%)# Run validation against ground truth

[PASS]: Sclerotic Fraction (< 5%)python tests/test_orlando_normal.py

[PASS]: Retention Cysts (= 0)```

SUCCESS: ALL TESTS PASSED

```**Expected output:**

```

---[PASS]: HU Calibration

[PASS]: OMC Patency (Patent bilaterally)

## 📁 Repository Structure[PASS]: Sclerotic Fraction (< 5%)

[PASS]: Cyst Count (= 0)

```

src/SUCCESS: ALL TESTS PASSED - Pipeline agrees with clinical ground truth

├── calibration/              # HU correction & tissue segmentation```

│   ├── hu_calibration.py    # Physics-based HU calibration (180 lines)

│   └── adaptive_thresholds.py # Histogram-based thresholds (75 lines)---

├── sinus/                   # Sinus-specific analysis (CURRENT)

│   ├── anatomical.py        # OMC patency, wall shell, reference bone## 📁 Repository Structure

│   └── pathology.py         # Sclerosis, retention cysts

├── brain/                   # Brain-specific analysis (FUTURE)```

│   ├── hemorrhage.py        # Acute blood detectionsinus-ct-ml-pipeline/

│   ├── midline.py           # Shift measurement├── src/

│   ├── stroke.py            # Hypodense region segmentation│   ├── calibration/           # HU calibration modules

│   └── ventricles.py        # CSF space sizing│   │   ├── hu_calibration.py       # Air/bone anchor detection

├── reporting/               # Clinical report generation│   │   └── adaptive_thresholds.py  # Histogram-based segmentation

├── visualization/           # 3D rendering & plots│   ├── metrics/               # Measurement modules

└── core/                    # DICOM I/O & utilities│   │   ├── anatomical.py           # OMC patency, wall shell

│   │   └── pathology.py            # Sclerosis, cysts

docs/│   ├── reporting/             # Report generation

├── METHODS.md               # Technical methodology & algorithms│   ├── visualization/         # 3D rendering, plots

├── ML_QUICKSTART.md         # Machine learning training guide│   └── core/                  # DICOM I/O, utilities

└── metrics/                 # Quantitative analysis outputs├── tests/                     # Validation test suite

```│   └── test_orlando_normal.py      # Ground truth validation

├── notebooks/                 # Jupyter analysis notebooks

---│   └── 05_calibration_validation.ipynb

├── docs/                      # Reports, metrics, visualizations

## 🧪 Validation Results│   ├── validation/                 # Validation results

│   └── report/                     # Clinical reports

Ground truth validation on Orlando Health normal scan:├── METHODS.md                 # Technical documentation

- ✅ **HU Calibration**: Air anchor (-1000 HU), Bone anchor (700-900 HU)└── README.md                  # This file

- ✅ **OMC Patency**: Left 14.6% Patent, Right 18.9% Patent  ```

  _(Thresholds: Patent >12%, Indeterminate 8-12%, Obstructed <8%)_

- ✅ **Sclerotic Fraction**: 3.2% (< 5% normal threshold)---

- ✅ **Retention Cysts**: 0 detected

## 🔬 Current Analysis: Sinus CT

---

### Calibration Pipeline

## 🧠 Why Head CT Only?

### Calibration Pipeline

### Anatomical Focus1. **HU Anchor Detection**: Air (-1000 HU) and bone (1200 HU) anchors

- **Sinus + Brain**: Unified head region analysis2. **Linear Correction**: Two-point calibration if drift >50 HU

- **Shared Skull Base**: Combined ENT and neurology assessment3. **Adaptive Thresholds**: Histogram-based air/tissue separation

- **Clinical Overlap**: Many patients need both sinus and brain evaluation

### Clinical Measurements

### Technical Advantages- **OMC Patency**: Multi-candidate corridor search, validated to ground truth

- **Similar HU Ranges**: Air cavities, soft tissue, bone all present- **Sclerotic Bone**: Z-score method with wall shell analysis

- **Non-Contrast Protocol**: Most head CTs are non-contrast, simplifying analysis- **Retention Cysts**: Strict anatomical rules (wall-attached, convex, size-filtered)

- **Validation Depth**: Focused scope allows thorough clinical validation- **Clinical Scores**: Lund-Mackay (standard + conservative variants)



### Future Brain Modules### Validation Results

```

| Module | Purpose | Key Metrics | HU Range |✓ Air anchor: -990 HU (expected -1000 ± 50)

|--------|---------|-------------|----------|✓ Bone anchor: 1399 HU (expected 1200 ± 200)

| `hemorrhage.py` | Acute blood detection | Volume (mL), expansion risk | 50-80 (acute) |✓ OMC: Left 14.6% (Patent), Right 18.9% (Patent)

| `midline.py` | Mass effect | Deviation (mm) from falx | N/A (geometric) |✓ Sclerosis: 0.05% (< 5% target)

| `stroke.py` | Ischemic regions | Hypodense volume, ASPECTS | 20-35 (edema) |✓ Cysts: 0 detected

| `ventricles.py` | Hydrocephalus | Ventricular ratio | 0-20 (CSF) |```

| `skull.py` | Fractures, air | Bone windows, pneumocephalus | -1000 (air), >400 (bone) |

**Ground truth**: Orlando April 2025 scan, radiologist report: "essentially clear; trace mucus in right sphenoid"

---

---

## 📖 Documentation

## 🌐 Extension to Other CT Analyses

- **[METHODS.md](METHODS.md)**: Technical methodology, HU calibration formulas, OMC measurement, brain extension guides

- **[ML_QUICKSTART.md](docs/ML_QUICKSTART.md)**: MONAI training, PyRadiomics integrationThe modular architecture supports expansion to other anatomical regions. See [`METHODS.md`](METHODS.md) for detailed extension guides.

- **[REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md)**: Architecture migration guide

### 🫁 **Lung CT** (Planned)

---- **Nodule Detection**: 3D Hough transform, convexity filtering

- **Emphysema Quantification**: Low-attenuation area (-950 HU threshold)

## 🔬 Development Roadmap- **Airway Analysis**: Bronchial tree segmentation, wall thickness



### Sinus Module (Current)**Key Modules**:

- [x] HU calibration with air/bone anchors```python

- [x] OMC patency measurement (multi-candidate)src/metrics/lung/

- [x] Sclerosis detection (z-score + wall shell)  ├── nodules.py      # Sphere detection, CAD integration

- [x] Retention cyst detection (strict rules)  ├── emphysema.py    # LAA quantification

- [x] Clinical validation (Orlando normal scan)  └── airways.py      # Bronchial tree analysis

- [ ] MONAI segmentation model training```

- [ ] Longitudinal tracking (multi-scan comparison)

### 🫀 **Cardiac CT** (Planned)

### Brain Module (Future)- **Coronary Calcium Scoring**: Agatston method (>130 HU, ≥3 voxels)

- [ ] Hemorrhage detection (5 subtypes)- **Vessel Centerline Extraction**: Stenosis quantification

- [ ] Midline shift measurement- **Chamber Volumetrics**: LV/RV segmentation, ejection fraction

- [ ] Stroke segmentation (ASPECTS scoring)

- [ ] Ventricular sizing (Evans' index)**Key Modules**:

- [ ] Skull fracture detection```python

- [ ] Integrated sinus+brain reportssrc/metrics/cardiac/

  ├── calcium.py      # Agatston score (FDA-regulated)

---  ├── vessels.py      # Centerline, stenosis

  └── chambers.py     # Volumetrics, function

## 💻 Usage Examples```



### Import Modules### 🧠 **Brain CT** (Planned)

```python- **Hemorrhage Detection**: Hyperdense region analysis (>60 HU)

from calibration import calibrate_volume, adaptive_threshold_air_tissue- **Midline Shift**: Symmetry quantification

from sinus import measure_omc_patency_coronal, compute_sclerosis_zscore- **Stroke Protocol**: Acute blood detection, ASPECTS scoring

```

**Key Modules**:

### Basic Analysis```python

```pythonsrc/metrics/brain/

# Load and calibrate  ├── hemorrhage.py   # ICH detection

vol_calibrated, metadata = calibrate_volume(volume_raw, spacing)  ├── midline.py      # Shift quantification

  └── stroke.py       # ASPECTS, perfusion

# Measure OMC patency```

result = measure_omc_patency_coronal(

    vol_calibrated, ### 🦴 **Musculoskeletal CT** (Planned)

    spacing, - **Bone Density**: Opportunistic screening (L1-L4 vertebrae)

    z_slice=slice_idx,- **Fracture Detection**: Cortical breach identification

    threshold_patent=0.12,- **Joint Space**: Hip/knee degeneration metrics

    threshold_obstructed=0.08

)**Key Modules**:

print(f"Left: {result['left']['status']} ({result['left']['patency_pct']:.1f}%)")```python

```src/metrics/msk/

  ├── bone_density.py # HU-to-BMD conversion

### Future Brain Analysis  ├── fracture.py     # Cortical breach detection

```python  └── joints.py       # Space narrowing, osteophytes

from brain import detect_hemorrhage, measure_midline_shift```



# Hemorrhage detection### 🫘 **Abdominal CT** (Planned)

bleeds = detect_hemorrhage(vol_calibrated, spacing, threshold=50)- **Liver Segmentation**: Active contours, lesion detection

for bleed in bleeds:- **Renal Stones**: Density quantification

    print(f"{bleed['type']}: {bleed['volume_ml']:.1f} mL")- **Bowel Wall Thickness**: Inflammatory bowel disease tracking



# Midline shift**Key Modules**:

shift_mm = measure_midline_shift(vol_calibrated, spacing)```python

print(f"Midline deviation: {shift_mm:.1f} mm")src/metrics/abdomen/

```  ├── liver.py        # Segmentation, lesions, radiomics

  ├── kidney.py       # Stones, masses, function

---  └── bowel.py        # Wall thickness, obstruction

```

## 🤝 Contributing

---

1. Fork the repository

2. Create feature branch (`git checkout -b feature/brain-hemorrhage`)## 📚 Documentation

3. Add tests for new functionality

4. Ensure validation passes (`python tests/test_*.py`)- **[METHODS.md](METHODS.md)**: Comprehensive technical documentation

5. Submit pull request  - HU calibration algorithm

  - OMC measurement methodology

---  - Sclerosis and cyst detection

  - Extension guides for other CT analyses

## 📄 License  - Clinical validation results



MIT License - see [LICENSE](LICENSE) for details.- **[Validation Notebook](notebooks/05_calibration_validation.ipynb)**: Interactive debugging

  - HU anchor visualization

---  - Adaptive threshold histograms

  - OMC corridor placement

## 🔗 Related Resources  - Wall shell and sclerosis analysis



- **MONAI**: [monai.io](https://monai.io/) - Medical imaging deep learning---

- **PyRadiomics**: [pyradiomics.readthedocs.io](https://pyradiomics.readthedocs.io/) - Quantitative feature extraction

- **ITK-SNAP**: [itksnap.org](http://www.itksnap.org/) - Manual segmentation and validation## 🧪 Testing & Validation



---### Run Validation Suite

```bash

## ✉️ Contactpytest tests/

```

For questions or collaboration: [GitHub Issues](https://github.com/mtbajdas/sinus-ct-ml-pipeline/issues)

### Interactive Validation
```bash
jupyter notebook notebooks/05_calibration_validation.ipynb
```

### Validation Framework
- Ground truth: Radiologist-confirmed normal scan
- Automated pass/fail dashboard
- Calibration metadata tracking
- Visual debugging tools

---

## 🛠️ Development Roadmap

### ✅ Completed (v1.0)
- [x] Modular package structure
- [x] HU calibration with anchor detection
- [x] Adaptive tissue thresholding
- [x] OMC patency measurement (validated)
- [x] Sclerotic bone detection
- [x] Retention cyst detection
- [x] Ground truth validation harness
- [x] Comprehensive documentation

### 🚧 In Progress
- [ ] Multi-series comparison reporting
- [ ] 3D visualization improvements
- [ ] DICOM SR structured reporting

### 📋 Planned (v2.0)
- [ ] Lung CT module (nodule, emphysema, airways)
- [ ] Cardiac CT module (calcium scoring, vessels)
- [ ] Brain CT module (hemorrhage, midline shift)
- [ ] Universal DICOM loader (multi-organ support)
- [ ] REST API for batch processing

---

## 🤝 Contributing

Contributions welcome! This repository demonstrates:
- **Physics-based validation**: Calibration against known anchors
- **Clinical alignment**: Measurements match radiologist reports
- **Modular design**: Easy to extend to new anatomical regions
- **Comprehensive testing**: Ground truth validation suite

To contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/lung-nodules`)
3. Add tests for new functionality
4. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **Clinical Validation**: Orlando ENT consultation (April 2025)
- **Frameworks**: MONAI, PyRadiomics, scikit-image, Plotly
- **Inspiration**: ACR-AAPM Technical Standards, Radiological Society of North America

---

## 📞 Contact

Questions or collaboration inquiries? Open an issue or reach out via GitHub.

**Built for rigorous medical imaging analysis with extensibility in mind.**

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
