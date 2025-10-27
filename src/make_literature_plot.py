import json
from pathlib import Path
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


NORMALS = {
    'OMC Patency (%)': (60, 100),
    'Sclerotic Bone (%)': (0, 5),
    'Retention Cysts (count)': (0, 2),
}


def main():
    ap = argparse.ArgumentParser(description='Create literature comparison plot for key metrics')
    ap.add_argument('--json', default='docs/metrics/clinical_5309.json')
    ap.add_argument('--out', default='docs/literature_comparison.png')
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text())
    omc_left = data['metrics']['omc_patency']['left_score']
    omc_right = data['metrics']['omc_patency']['right_score']
    sclerotic = data['metrics']['bony_changes']['sclerotic_fraction_pct']
    cysts = data['metrics']['retention_cysts']

    labels = ['OMC Left (%)', 'OMC Right (%)', 'Sclerotic Bone (%)', 'Retention Cysts']
    values = [omc_left, omc_right, sclerotic, cysts]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=['crimson' if v> (NORMALS['Sclerotic Bone (%)'][1] if 'Sclerotic' in lbl else (NORMALS['Retention Cysts (count)'][1] if 'Cysts' in lbl else 60)) else 'steelblue' for lbl, v in zip(labels, values)])

    # Draw normal ranges
    ax.axhspan(60, 100, color='green', alpha=0.1, label='Normal OMC range (60-100%)')
    ax.axhspan(0, 5, color='orange', alpha=0.1, label='Normal Sclerosis (0-5%)')
    ax.axhspan(0, 2, color='purple', alpha=0.08, label='Normal cysts (0-2)')

    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width()/2, v + 1, f"{v:.0f}" if isinstance(v, (int, float)) else str(v), ha='center', va='bottom', fontsize=9)

    ax.set_title('Your Metrics vs Literature Normal Ranges (Series 5309)')
    ax.set_ylabel('Value')
    ax.set_ylim(0, max(100, max(values) + 10))
    ax.legend(loc='upper right', fontsize=8)
    fig.tight_layout()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    main()
