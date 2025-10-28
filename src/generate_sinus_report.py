"""
DEPRECATED: generate_sinus_report.py

This script is kept for backward compatibility. It now forwards to the unified
generate_report.py, which produces a single comprehensive PDF including sinus,
skull, temporal bones, and brain sections.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from generate_report import create_report


def main():
    parser = argparse.ArgumentParser(
        description='[DEPRECATED] Use generate_report.py instead – unified Head CT report'
    )
    parser.add_argument('--comprehensive', default='docs/metrics/comprehensive_head_analysis.json')
    parser.add_argument('--clinical', default='docs/metrics/clinical_analysis_report.json')
    parser.add_argument('--quant', default='docs/metrics/quantitative_analysis.json')
    parser.add_argument('--meta', default='docs/last_run_meta.json')
    parser.add_argument('--output', default='docs/report/comprehensive_report.pdf')

    args = parser.parse_args()

    # Forward to unified report generator
    create_report(
        comprehensive_path=Path(args.comprehensive),
        clinical_path=Path(args.clinical),
        quantitative_path=Path(args.quant),
        meta_path=Path(args.meta),
        output_path=Path(args.output),
    )


if __name__ == '__main__':
    main()
