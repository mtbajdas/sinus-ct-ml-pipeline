"""
Generate an interactive 3D visualization of sinus CT volumes.

Workflow:
1. Load a NIfTI file (output of pipeline.py).
2. Optionally apply smoothing / downsampling to reduce mesh size.
3. Run marching cubes to extract an iso-surface at the desired HU level.
4. Render using Plotly Mesh3d for quick inspection in a browser window.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import nibabel as nib
import numpy as np
import plotly.graph_objects as go
from skimage import measure
from skimage.transform import downscale_local_mean

logger = logging.getLogger(__name__)


def load_volume(nifti_path: Path) -> tuple[np.ndarray, tuple[float, float, float]]:
    if not nifti_path.exists():
        raise FileNotFoundError(f"NIfTI not found: {nifti_path}")
    img = nib.load(str(nifti_path))
    data = img.get_fdata().astype(np.float32)
    spacing = img.header.get_zooms()[:3]
    logger.info("Loaded %s with shape %s and spacing %s", nifti_path, data.shape, spacing)
    return data, spacing


def preprocess(volume: np.ndarray, downsample: int | None = None) -> np.ndarray:
    if downsample and downsample > 1:
        factors = (downsample, downsample, downsample)
        volume = downscale_local_mean(volume, factors)
        logger.info("Downsampled volume by %sx -> new shape %s", downsample, volume.shape)
    return volume


def to_mesh(volume: np.ndarray, spacing: tuple[float, float, float], iso_value: float) -> tuple[np.ndarray, np.ndarray]:
    v_min, v_max = float(volume.min()), float(volume.max())
    if not (v_min <= iso_value <= v_max):
        raise ValueError(f"Iso level {iso_value} outside volume range [{v_min:.1f}, {v_max:.1f}]")
    verts, faces, _normals, _values = measure.marching_cubes(
        volume, level=iso_value, spacing=spacing, allow_degenerate=False
    )
    logger.info("Marching cubes produced %d vertices / %d faces", len(verts), len(faces))
    return verts, faces


def render_mesh(
    verts: np.ndarray,
    faces: np.ndarray,
    title: str,
    output_html: Path,
) -> None:
    mesh = go.Mesh3d(
        x=verts[:, 0],
        y=verts[:, 1],
        z=verts[:, 2],
        i=faces[:, 0],
        j=faces[:, 1],
        k=faces[:, 2],
        color="lightblue",
        opacity=0.5,
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.3),
    )
    fig = go.Figure(data=[mesh])
    fig.update_layout(scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z"), title=title)
    fig.write_html(str(output_html))
    logger.info("Wrote interactive mesh to %s", output_html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="3D sinus visualization")
    parser.add_argument("--nifti", type=Path, required=True, help="Path to NIfTI volume")
    parser.add_argument("--iso", type=float, default=-300.0, help="Iso-value (HU) for marching cubes surface")
    parser.add_argument(
        "--downsample",
        type=int,
        default=2,
        help="Integer factor for local-mean downsampling prior to meshing (use 1 to disable)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/interactive_mesh.html"),
        help="Destination HTML file for the Plotly scene",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logger verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    volume, spacing = load_volume(args.nifti)
    volume = preprocess(volume, downsample=args.downsample if args.downsample > 1 else None)
    verts, faces = to_mesh(volume, spacing, args.iso)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    render_mesh(verts, faces, f"Iso={args.iso} HU", args.output)


if __name__ == "__main__":
    main()
