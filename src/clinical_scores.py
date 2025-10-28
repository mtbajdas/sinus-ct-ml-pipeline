"""
Clinical scoring utilities (e.g., Lund–Mackay) computed from threshold masks.

This implementation uses explainable HU-based masks and heuristic regional boxes
to approximate sinus subregions. It is intended as a prototype; clinicians may
adjust thresholds/regions.
"""
from __future__ import annotations

from typing import Dict, Tuple
import numpy as np


def _sinus_regions(volume_shape: Tuple[int, int, int]) -> Dict[str, Tuple[slice, slice, slice]]:
    """Approximate 3D boxes for each sinus region by side.

    Returns dict keys like 'maxillary_L', 'frontal_R', each mapping to (z, y, x) slices.
    """
    z, y, x = volume_shape
    zc = z // 2
    xc = x // 2

    # Axial bands (heuristic based on earlier visualization code)
    z_frontal = slice(max(zc - 50, 0), max(zc - 25, 1))
    z_ant_eth = slice(max(zc - 30, 0), max(zc - 15, 1))
    z_post_eth = slice(max(zc - 15, 0), max(zc - 5, 1))
    z_maxillary = slice(max(zc - 5, 0), min(zc + 15, z))
    z_sphenoid = slice(max(zc + 10, 0), min(zc + 30, z))

    # Lateral halves
    xL = slice(max(xc - 60, 0), max(xc - 1, 1))
    xR = slice(min(xc + 1, x), min(xc + 60, x))

    # Use broad anterior/posterior band; keep whole y to avoid brittle AP splitting
    y_band = slice(0, y)

    return {
        'frontal_L': (z_frontal, y_band, xL),
        'frontal_R': (z_frontal, y_band, xR),
        'ant_ethmoid_L': (z_ant_eth, y_band, xL),
        'ant_ethmoid_R': (z_ant_eth, y_band, xR),
        'post_ethmoid_L': (z_post_eth, y_band, xL),
        'post_ethmoid_R': (z_post_eth, y_band, xR),
        'maxillary_L': (z_maxillary, y_band, xL),
        'maxillary_R': (z_maxillary, y_band, xR),
        'sphenoid_L': (z_sphenoid, y_band, xL),
        'sphenoid_R': (z_sphenoid, y_band, xR),
    }


def _opacification_score(opac_frac: float, conservative: bool = False) -> int:
    """Map opacification fraction to Lund–Mackay 0/1/2.

    Default cut points: 0 if <10%, 1 if 10–50%, 2 if >=50%.
    Conservative cut points (reduce false positives): 0 if <20%, 1 if 20–70%, 2 if >=70%.
    """
    if conservative:
        if opac_frac < 0.20:
            return 0
        if opac_frac < 0.70:
            return 1
        return 2
    else:
        if opac_frac < 0.10:
            return 0
        if opac_frac < 0.50:
            return 1
        return 2


def compute_lund_mackay(volume: np.ndarray, conservative: bool = False) -> Dict[str, object]:
    """Compute a Lund–Mackay-like score from a 3D CT volume using HU thresholds.

    - Air mask: HU < -400 within sinus cavities (conservative: < -500 HU)
    - Opacification: soft tissue within air cavities (-100..100 HU; conservative: -50..50 HU)
    - Scoring per sinus (L/R for maxillary, ant/post ethmoid, frontal, sphenoid): 0/1/2 by opac% (<10/10-50/>50)
      Conservative cut points: 0/1/2 by opac% (<20/20-70/>=70)
    - OMC per side: 0 if patency >= 60%, else 2 (conservative: >= 70% for 0; classic LM treats OMC as 0 or 2)

    Returns:
        {
          'by_region': {'maxillary': {'L': int, 'R': int}, ...},
          'omc': {'L': int, 'R': int},
          'totals': {'lm20': int, 'lm24': int, 'left': int, 'right': int},
          'criteria': {
              'air_threshold': int,
              'soft_tissue_range': Tuple[int, int],
              'omc_patency_zero_threshold_pct': float,
              'opacification_cutpoints': Tuple[float, float]
          }
        }
    """
    air_th = -500 if conservative else -400
    st_lo, st_hi = (-50, 50) if conservative else (-100, 100)
    air_mask = volume < air_th
    soft_tissue = (volume > st_lo) & (volume < st_hi)
    # Restrict opacification to air spaces (tissue displacing air)
    opac_in_air = soft_tissue & air_mask

    regions = _sinus_regions(volume.shape)

    per = {
        'frontal': {'L': 0, 'R': 0},
        'ant_ethmoid': {'L': 0, 'R': 0},
        'post_ethmoid': {'L': 0, 'R': 0},
        'maxillary': {'L': 0, 'R': 0},
        'sphenoid': {'L': 0, 'R': 0},
    }

    for name, slcs in regions.items():
        region_air = air_mask[slcs]
        region_opac = opac_in_air[slcs]
        air_count = int(region_air.sum())
        opac_count = int(region_opac.sum())
        frac = (opac_count / air_count) if air_count > 0 else 0.0
        score = _opacification_score(frac, conservative=conservative)
        base, side = name.rsplit('_', 1)
        side_key = 'L' if side == 'L' else 'R'
        key_map = {
            'frontal': 'frontal',
            'ant': 'ant_ethmoid',
            'post': 'post_ethmoid',
            'maxillary': 'maxillary',
            'sphenoid': 'sphenoid',
            'ant_ethmoid': 'ant_ethmoid',
            'post_ethmoid': 'post_ethmoid',
        }
        tgt = key_map.get(base, base)
        if tgt in per:
            per[tgt][side_key] = score

    # OMC patency approx via same boxes used elsewhere
    z, y, x = volume.shape
    midline = x // 2
    omc_z = (z // 2 - 30, z // 2 - 10)
    omc_y = (y // 2 + 10, y // 2 + 40)
    omc_x_left = (midline - 25, midline - 5)
    omc_x_right = (midline + 5, midline + 25)

    def _patency(zr, yr, xr) -> float:
        region = volume[zr[0]:zr[1], yr[0]:yr[1], xr[0]:xr[1]]
        return float((region < air_th).sum()) / float(region.size) * 100.0 if region.size > 0 else 0.0

    pL = _patency(omc_z, omc_y, omc_x_left)
    pR = _patency(omc_z, omc_y, omc_x_right)
    omc_cut = 70.0 if conservative else 60.0
    omc = {'L': 0 if pL >= omc_cut else 2, 'R': 0 if pR >= omc_cut else 2}

    # Totals
    left20 = per['frontal']['L'] + per['ant_ethmoid']['L'] + per['post_ethmoid']['L'] + per['maxillary']['L'] + per['sphenoid']['L']
    right20 = per['frontal']['R'] + per['ant_ethmoid']['R'] + per['post_ethmoid']['R'] + per['maxillary']['R'] + per['sphenoid']['R']
    lm20 = left20 + right20
    left24 = left20 + omc['L']
    right24 = right20 + omc['R']
    lm24 = left24 + right24

    return {
        'by_region': per,
        'omc': omc,
        'totals': {
            'lm20': int(lm20),
            'lm24': int(lm24),
            'left': int(left24),
            'right': int(right24),
        },
        'omc_patency_pct': {'L': float(pL), 'R': float(pR)},
        'criteria': {
            'air_threshold': int(air_th),
            'soft_tissue_range': (int(st_lo), int(st_hi)),
            'omc_patency_zero_threshold_pct': float(omc_cut),
            'opacification_cutpoints': (0.20, 0.70) if conservative else (0.10, 0.50),
        },
    }
