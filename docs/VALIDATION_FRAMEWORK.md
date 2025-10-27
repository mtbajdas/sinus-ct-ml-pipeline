# Validation Framework for Clinical Findings

## Overview
This framework enables testing the clinical investigation pipeline on synthetic CT data to validate that findings detection works as expected.

## Components

### 1. Refactored Clinical Investigation Module (`src/clinical_investigation.py`)
- **Function**: `run_clinical_investigation(nifti_path, meta_path, out_png, out_json, quiet=False)`
- **Purpose**: Runs all 8 analysis steps and returns structured report
- **CLI**: Supports argparse for custom paths and quiet mode
- **Returns**: Clinical report dict with metrics and findings

### 2. Pytest Test Suite (`tests/test_clinical_investigation.py`)
- **Tests**:
  - `test_normal_anatomy_has_no_cysts_and_low_sclerosis`: Validates baseline synthetic anatomy
  - `test_mucosal_thickening_detectable_at_6mm`: Verifies OMC metrics are computed
- **Fixtures**: Uses `SyntheticSinusGenerator` to create controlled test cases
- **Assertions**: Validates metric ranges, file creation, report structure

### 3. CLI Validator (`src/validate_findings.py`)
- **Scenarios**: normal, mucosal_severe (6mm), opacified_left_maxillary
- **Output**: `docs/metrics/validation_summary.json`
- **Usage**: `python src/validate_findings.py`
- **Purpose**: Quick visual confirmation of pipeline behavior

### 4. Notebook Cell (added to `notebooks/03_clinical_investigation.ipynb`)
- **Location**: Bottom of notebook
- **Action**: Runs validator script and displays summary table
- **Purpose**: Interactive exploration of validation results

## Running Tests

### Pytest (automated)
```bash
C:/Users/mtbaj/sinus-ct-ml-pipeline/.venv/Scripts/python.exe -m pytest -q
```

Expected output:
```
..
2 passed in ~17s
```

### CLI Validator (manual)
```bash
python src/validate_findings.py
```

Expected output:
```
Validation complete. Summary:
- normal: cysts=0, OMC(L/R)=57.9/57.7, sclerosis=5.5%
- mucosal_severe: cysts=0, OMC(L/R)=7.9/7.9, sclerosis=4.8%
- opacified_left_maxillary: cysts=0, OMC(L/R)=54.3/57.7, sclerosis=5.5%

Saved: docs\metrics\validation_summary.json
```

### Notebook (interactive)
1. Open `notebooks/03_clinical_investigation.ipynb`
2. Scroll to bottom
3. Run the "Validation: Test with Synthetic Scenarios" cell
4. View formatted results table

## Validation Criteria

### Normal Anatomy
- ✅ No retention cysts detected
- ✅ Sclerotic fraction within 0-100%
- ✅ Soft tissue fractions within 0-1 range
- ✅ OMC scores computed (0-100)
- ✅ Output files created (PNG + JSON)

### Mucosal Thickening (6mm)
- ✅ OMC patency scores reduced vs normal
- ✅ All metrics structurally valid
- ✅ Report contains expected fields

## Dependencies
- pytest (added to `requirements.txt`)
- nibabel, numpy, scipy, matplotlib, pandas (existing)
- SyntheticSinusGenerator for test data generation

## Quality Gates
- ✅ **Unit Tests**: 2/2 passing
- ✅ **Lint**: No errors in refactored module
- ✅ **Integration**: Validator runs successfully on 3 scenarios
- ✅ **Documentation**: This README + inline docstrings

## Next Steps for Enhancement
1. Add more pathology scenarios (fluid levels, bilateral disease)
2. Compare metrics against literature reference values
3. Add regression tests for metric stability
4. Implement longitudinal tracking across multiple scans
