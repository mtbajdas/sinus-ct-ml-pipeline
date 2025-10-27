import argparse
from pathlib import Path
import numpy as np
import nibabel as nib
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


def analyze_omc(volume: np.ndarray):
    omc_z_range, omc_y_range, omc_x_left, omc_x_right = compute_omc_boxes(volume.shape)

    def _region(fr):
        z, y, x = fr
        return volume[z[0]:z[1], y[0]:y[1], x[0]:x[1]]

    left = _region((omc_z_range, omc_y_range, omc_x_left))
    right = _region((omc_z_range, omc_y_range, omc_x_right))

    def _stats(region):
        total = region.size
        air = (region < -400).sum() / total
        tissue = ((region > -100) & (region < 100)).sum() / total
        return air, tissue, region.mean()

    l_air, l_tissue, l_mean = _stats(left)
    r_air, r_tissue, r_mean = _stats(right)
    return {
        'left': {'air_fraction': float(l_air), 'tissue_fraction': float(l_tissue), 'mean_hu': float(l_mean)},
        'right': {'air_fraction': float(r_air), 'tissue_fraction': float(r_tissue), 'mean_hu': float(r_mean)},
        'ranges': {
            'z': list(omc_z_range), 'y': list(omc_y_range),
            'x_left': list(omc_x_left), 'x_right': list(omc_x_right)
        }
    }


def draw_overlay(volume: np.ndarray, out_png: Path):
    omc_z_range, omc_y_range, omc_x_left, omc_x_right = compute_omc_boxes(volume.shape)
    # pick a representative slice in OMC z-range
    z_idx = (omc_z_range[0] + omc_z_range[1]) // 2
    slice_img = volume[z_idx]
    air_mask = slice_img < -400

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.imshow(slice_img, cmap='gray', vmin=-1000, vmax=400)
    ax.imshow(air_mask, cmap='Blues', alpha=0.35)

    def _draw_box(y_range, x_range, color):
        y0, y1 = y_range
        x0, x1 = x_range
        # draw rectangle
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=color, linewidth=2)

    _draw_box(omc_y_range, omc_x_left, 'red')
    _draw_box(omc_y_range, omc_x_right, 'red')
    ax.set_title(f'OMC ROI overlay (z={z_idx})')
    ax.axis('off')
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description='OMC ROI verification overlay and stats')
    ap.add_argument('--nifti', required=True, help='Path to NIfTI volume')
    ap.add_argument('--out', required=True, help='Output PNG path for overlay')
    args = ap.parse_args()

    img = nib.load(args.nifti)
    vol = img.get_fdata().astype(np.float32)
    stats = analyze_omc(vol)
    print('OMC stats:')
    print(stats)
    draw_overlay(vol, Path(args.out))
    print(f'Overlay saved to {args.out}')


if __name__ == '__main__':
    main()
