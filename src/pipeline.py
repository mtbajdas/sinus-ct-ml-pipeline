"""
Sinus CT ML pipeline scaffold.

Capabilities:
1. Load DICOM series into numpy volume.
2. Convert and persist to NIfTI for downstream tooling.
3. Quick slice viewer for sanity checking.
4. Placeholders for segmentation and radiomics hooks.
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pydicom


logger = logging.getLogger(__name__)


def load_dicom_series(dicom_dir: Path, series_uid: str | None = None) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Load a folder of DICOM slices into a 3D numpy volume sorted by z-position.

    Returns:
        volume: ndarray [num_slices, height, width] in original intensity scale.
        affine: 4x4 matrix describing voxel spacing/orientation for NIfTI export.
        meta:   selected DICOM metadata for downstream reference.
    """
    if not dicom_dir.is_dir():
        raise FileNotFoundError(f"DICOM folder not found: {dicom_dir}")

    dicom_files = sorted(p for p in dicom_dir.rglob("*") if p.is_file())
    slices: List[pydicom.dataset.FileDataset] = []
    for file in dicom_files:
        if file.suffix.lower() not in {".dcm", ""}:
            continue
        try:
            ds = pydicom.dcmread(str(file), stop_before_pixels=False)
            slices.append(ds)
        except Exception as exc:  # pragma: no cover - defensive parsing
            logger.debug("Skipping non-DICOM file %s (%s)", file.name, exc)

    if not slices:
        raise ValueError(
            f"No DICOM slices detected under {dicom_dir}. "
            "Ensure you pointed to the folder that contains the numbered series directories."
        )

    from collections import defaultdict

    series_map: Dict[str, List[pydicom.dataset.FileDataset]] = defaultdict(list)
    for ds in slices:
        series_map[getattr(ds, "SeriesInstanceUID", "unknown")].append(ds)

    if series_uid:
        if series_uid not in series_map:
            available = ", ".join(series_map.keys())
            raise ValueError(f"Requested series UID {series_uid} not found. Available: {available}")
        chosen_uid = series_uid
    else:
        chosen_uid = max(series_map.items(), key=lambda item: len(item[1]))[0]

    selected = series_map[chosen_uid]

    selected.sort(
        key=lambda s: float(
            getattr(s, "ImagePositionPatient", [0.0, 0.0, float(s.InstanceNumber)])[2]
        )
    )

    volume = np.stack([s.pixel_array for s in selected]).astype(np.int16)
    slope = float(getattr(selected[0], "RescaleSlope", 1.0))
    intercept = float(getattr(selected[0], "RescaleIntercept", 0.0))
    volume = volume.astype(np.float32) * slope + intercept
    spacing_xy = [float(x) for x in getattr(selected[0], "PixelSpacing", [1.0, 1.0])]
    spacing_z = float(getattr(selected[0], "SliceThickness", 1.0))
    pixel_spacing = np.array(spacing_xy + [spacing_z], dtype=float)
    affine = np.eye(4)
    affine[:3, :3] = np.diag(pixel_spacing)

    meta = {
        "patient_id": getattr(selected[0], "PatientID", "unknown"),
        "study_date": getattr(selected[0], "StudyDate", "unknown"),
        "modality": getattr(selected[0], "Modality", "CT"),
        "spacing": pixel_spacing.tolist(),
        "num_slices": len(selected),
        "series_uid": chosen_uid,
        "rescale_slope": slope,
        "rescale_intercept": intercept,
    }

    logger.info(
        "Loaded DICOM series %s with %d slices (shape=%s spacing=%s)",
        chosen_uid,
        meta["num_slices"],
        volume.shape,
        meta["spacing"],
    )
    return volume, affine, meta


def save_nifti(volume: np.ndarray, affine: np.ndarray, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nifti = nib.Nifti1Image(volume, affine)
    nib.save(nifti, str(output_path))
    logger.info("Saved NIfTI to %s", output_path)
    return output_path


def view_slices(volume: np.ndarray, step: int = 10) -> None:
    """Iterate through axial slices for quick QA."""
    for idx in range(0, volume.shape[0], step):
        plt.imshow(volume[idx], cmap="gray")
        plt.title(f"Slice {idx}")
        plt.axis("off")
        plt.show()


@dataclass
class SegmentationResult:
    mask: np.ndarray
    metadata: Dict[str, Any]


class SegmentationModel:
    """Minimal MONAI 3D U-Net inference helper."""

    def __init__(
        self,
        weights_path: Path,
        device: str | None = None,
        roi_size: Tuple[int, int, int] = (96, 96, 96),
        sw_batch_size: int = 1,
        overlap: float = 0.25,
    ) -> None:
        import torch
        from monai.networks.nets import UNet

        if not weights_path.exists():
            raise FileNotFoundError(f"Segmentation weights not found: {weights_path}")

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.roi_size = roi_size
        self.sw_batch_size = sw_batch_size
        self.overlap = overlap
        self.torch = torch

        self.model = UNet(
            spatial_dims=3,
            in_channels=1,
            out_channels=2,
            channels=(16, 32, 64, 128, 256),
            strides=(2, 2, 2, 2),
        ).to(self.device)
        state = torch.load(str(weights_path), map_location=self.device)
        if "state_dict" in state:
            state = state["state_dict"]
        self.model.load_state_dict(state)
        self.model.eval()

    def _preprocess(self, volume: np.ndarray) -> np.ndarray:
        # Simple HU windowing to nasal tissue range [-1000, 400] -> [0, 1]
        clipped = np.clip(volume, -1000, 400)
        norm = (clipped + 1000.0) / 1400.0
        return norm.astype(np.float32)

    def predict(self, volume: np.ndarray) -> SegmentationResult:
        from monai.inferers import sliding_window_inference

        prepped = self._preprocess(volume)
        tensor = self.torch.from_numpy(prepped).unsqueeze(0).unsqueeze(0).to(self.device)

        with self.torch.no_grad():
            logits = sliding_window_inference(
                tensor,
                roi_size=self.roi_size,
                sw_batch_size=self.sw_batch_size,
                predictor=self.model,
                overlap=self.overlap,
            )
            probs = self.torch.softmax(logits, dim=1)
            mask = probs.argmax(dim=1).squeeze().cpu().numpy().astype(np.uint8)

        return SegmentationResult(mask=mask, metadata={"roi_size": self.roi_size})


def extract_radiomics_features(image_path: Path, mask_path: Path) -> Dict[str, float]:
    from radiomics import featureextractor

    extractor = featureextractor.RadiomicsFeatureExtractor()
    result = extractor.execute(str(image_path), str(mask_path))

    def _to_serializable(val: Any) -> Any:
        if isinstance(val, (np.generic,)):
            return np.asarray(val).item()  # pragma: no cover
        if isinstance(val, (np.ndarray,)):
            return val.tolist()
        return val

    return {k: _to_serializable(v) for k, v in result.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sinus CT pipeline utilities")
    parser.add_argument("--dicom-dir", type=Path, required=True, help="Folder with DICOM slices")
    parser.add_argument(
        "--output-nifti",
        type=Path,
        default=Path("data/processed/sinus_ct.nii.gz"),
        help="Destination NIfTI path",
    )
    parser.add_argument("--view-step", type=int, default=0, help="Slice step for viewer (0 disables)")
    parser.add_argument("--metadata-json", type=Path, default=Path("docs/last_run_meta.json"))
    parser.add_argument(
        "--series-uid",
        type=str,
        help="Optional SeriesInstanceUID to load (defaults to largest series under the folder)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logger verbosity",
    )
    parser.add_argument("--seg-weights", type=Path, help="Path to trained segmentation weights (MONAI/PyTorch).")
    parser.add_argument("--mask-output", type=Path, default=Path("data/processed/sinus_mask.nii.gz"))
    parser.add_argument(
        "--seg-roi",
        type=int,
        nargs=3,
        metavar=("X", "Y", "Z"),
        default=(96, 96, 96),
        help="Sliding-window ROI size for segmentation inference.",
    )
    parser.add_argument("--seg-overlap", type=float, default=0.25, help="Sliding-window overlap fraction.")
    parser.add_argument("--seg-batch", type=int, default=1, help="Sliding-window batch size.")
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda"],
        help="Device to run segmentation on (defaults to CUDA if available).",
    )
    parser.add_argument(
        "--radiomics-json",
        type=Path,
        help="Optional path to save PyRadiomics feature dictionary (requires a mask).",
    )
    parser.add_argument(
        "--radiomics-mask",
        type=Path,
        help="Use an existing mask for radiomics instead of generating one (overrides --mask-output).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

    volume, affine, meta = load_dicom_series(args.dicom_dir, series_uid=args.series_uid)
    save_nifti(volume, affine, args.output_nifti)

    generated_mask_path: Path | None = None
    if args.seg_weights:
        seg_model = SegmentationModel(
            args.seg_weights,
            device=args.device,
            roi_size=tuple(args.seg_roi),
            sw_batch_size=args.seg_batch,
            overlap=args.seg_overlap,
        )
        seg_result = seg_model.predict(volume)
        args.mask_output.parent.mkdir(parents=True, exist_ok=True)
        save_nifti(seg_result.mask.astype(np.uint8), affine, args.mask_output)
        meta["segmentation"] = {
            "weights": str(args.seg_weights),
            "mask_path": str(args.mask_output),
            **seg_result.metadata,
        }
        generated_mask_path = args.mask_output
        logger.info("Segmentation mask saved to %s", args.mask_output)

    if args.radiomics_json:
        mask_source = args.radiomics_mask or generated_mask_path or args.mask_output
        if not mask_source.exists():
            raise FileNotFoundError(
                f"Radiomics requested but mask {mask_source} does not exist. "
                "Provide --radiomics-mask or enable segmentation."
            )
        features = extract_radiomics_features(args.output_nifti, mask_source)
        args.radiomics_json.parent.mkdir(parents=True, exist_ok=True)
        args.radiomics_json.write_text(json.dumps(features, indent=2))
        logger.info("Radiomics features saved to %s", args.radiomics_json)
        meta["radiomics"] = {"feature_path": str(args.radiomics_json), "num_features": len(features)}

    if args.view_step > 0:
        view_slices(volume, step=args.view_step)

    args.metadata_json.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_json.write_text(json.dumps(meta, indent=2))
    logger.info("Metadata persisted to %s", args.metadata_json)


if __name__ == "__main__":
    main()
