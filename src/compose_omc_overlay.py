import argparse
from pathlib import Path
import numpy as np
import nibabel as nib
from scipy import ndimage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def compute_omc_boxes(shape):
    z, y, x = shape
    midline = x // 2
    omc_z_range = (z // 2 - 30, z // 2 - 10)
    omc_y_range = (y // 2 + 10, y // 2 + 40)
    omc_x_left = (midline - 25, midline - 5)
    omc_x_right = (midline + 5, midline + 25)
    return omc_z_range, omc_y_range, omc_x_left, omc_x_right


def overlay_for_series(nifti_path: Path, series_label: str):
    img = nib.load(str(nifti_path))
    vol = img.get_fdata().astype(np.float32)
    omc_z, omc_y, x_left, x_right = compute_omc_boxes(vol.shape)

    # Use a central slice in the OMC z-range
    z_idx = (omc_z[0] + omc_z[1]) // 2
    sl = vol[z_idx]

    # Air cavity map (HU < -400), smoothed with opening/closing in 3D
    air3d = vol < -400
    air3d = ndimage.binary_opening(air3d, structure=np.ones((3, 3, 3)))
    air3d = ndimage.binary_closing(air3d, structure=np.ones((5, 5, 5)))
    air2d = air3d[z_idx]

    # Soft-tissue in sinus region mask (tissue range intersecting air region)
    tissue2d = (sl > -100) & (sl < 100) & air2d

    # Compute OMC metrics for left/right boxes
    def _box_stats(xrng):
        region = sl[omc_y[0]:omc_y[1], xrng[0]:xrng[1]]
        air_region = air2d[omc_y[0]:omc_y[1], xrng[0]:xrng[1]]
        tissue_region = tissue2d[omc_y[0]:omc_y[1], xrng[0]:xrng[1]]
        total = region.size
        air_frac = float(air_region.sum()) / total
        tissue_frac = float(tissue_region.sum()) / total
        return air_frac, tissue_frac

    l_air, l_tissue = _box_stats(x_left)
    r_air, r_tissue = _box_stats(x_right)

    # Compose figure
    fig, ax = plt.subplots(1, 1, figsize=(7, 6))
    ax.imshow(sl, cmap='gray', vmin=-1000, vmax=400)
    ax.imshow(air2d, cmap='Blues', alpha=0.35)
    ax.imshow(tissue2d, cmap='Reds', alpha=0.45)

    def _rect(y_rng, x_rng, color):
        y0, y1 = y_rng
        x0, x1 = x_rng
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=color, linewidth=2)

    _rect(omc_y, x_left, 'yellow')
    _rect(omc_y, x_right, 'yellow')

    ax.set_title(f"{series_label} — OMC overlay (z={z_idx})")
    ax.axis('off')

    # Annotate metrics
    ax.text(x_left[0], omc_y[0]-5, f"L air {l_air*100:.0f}% | tissue {l_tissue*100:.0f}%", color='yellow', fontsize=9, va='bottom')
    ax.text(x_right[0], omc_y[0]-5, f"R air {r_air*100:.0f}% | tissue {r_tissue*100:.0f}%", color='yellow', fontsize=9, va='bottom')
    return fig


def main():
    ap = argparse.ArgumentParser(description='Build informative side-by-side OMC overlays from NIfTI volumes')
    ap.add_argument('--nifti-left', default='data/processed/sinus_ct.nii.gz')
    ap.add_argument('--nifti-right', default='data/processed/sinus_ct_5309.nii.gz')
    ap.add_argument('--out', default='docs/omc_overlay_comparison.png')
    args = ap.parse_args()

    fig_left = overlay_for_series(Path(args.nifti_left), 'Series 5303')
    fig_right = overlay_for_series(Path(args.nifti_right), 'Series 5309')

    # Stitch side-by-side
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, f in zip(axes, [fig_left, fig_right]):
        # draw the figure canvas to a numpy array (use RGBA buffer for compatibility)
        f.canvas.draw()
        w, h = f.canvas.get_width_height()
        buf = np.frombuffer(f.canvas.buffer_rgba(), dtype=np.uint8)
        img = buf.reshape(h, w, 4)[:, :, :3]
        ax.imshow(img)
        ax.axis('off')
        plt.close(f)

    fig.suptitle('Bilateral OMC Obstruction — Air (blue), Tissue-in-sinus (red), ROI (yellow)')
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
