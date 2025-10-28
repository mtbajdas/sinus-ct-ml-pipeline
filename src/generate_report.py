"""
Comprehensive Head CT Analysis Report Generator

Generates a single PDF that consolidates sinus, skull, ear (temporal bones), and brain
metrics using both the clinical sinus analysis JSON and the comprehensive head
analysis JSON produced by HeadCTAnalyzer.
"""
from __future__ import annotations

from pathlib import Path
import json
import argparse
from datetime import datetime
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            with path.open() as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def create_report(
    comprehensive_path: str | Path = 'docs/metrics/comprehensive_head_analysis.json',
    clinical_path: str | Path = 'docs/metrics/clinical_analysis_report.json',
    quantitative_path: str | Path = 'docs/metrics/quantitative_analysis.json',
    meta_path: str | Path = 'docs/last_run_meta.json',
    output_path: str | Path = 'docs/report/comprehensive_report.pdf',
):
    """Generate a unified PDF report with all available metrics."""
    comprehensive_path = Path(comprehensive_path)
    # Back-compat fallback
    if not comprehensive_path.exists():
        alt = comprehensive_path.parent / 'full_head_analysis.json'
        if alt.exists():
            comprehensive_path = alt

    clinical_path = Path(clinical_path)
    quantitative_path = Path(quantitative_path)
    meta_path = Path(meta_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load data sources
    comp = _load_json(comprehensive_path)
    clin = _load_json(clinical_path)
    quant = _load_json(quantitative_path)
    meta = _load_json(meta_path)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='DataValue',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=10,
        textColor=colors.HexColor('#2c3e50')
    ))

    story = []

    # Header
    title = Paragraph('Comprehensive Head CT Quantitative Analysis Report', styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.2*inch))

    # Scan metadata
    comp_meta = comp.get('metadata', {})
    scan_date = meta.get('study_date', 'Unknown')
    patient_id = meta.get('patient_id', 'Unknown')
    series_desc = meta.get('series_description', 'N/A')
    spacing = comp_meta.get('spacing_mm', meta.get('spacing', 'N/A'))
    vol_shape = comp_meta.get('volume_shape', meta.get('dimensions', 'N/A'))
    roi_provider = comp_meta.get('roi_provider', 'Unknown')

    story.append(Paragraph(f"<b>Scan Date:</b> {scan_date}", styles['Normal']))
    story.append(Paragraph(f"<b>Patient ID:</b> {patient_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Series:</b> {series_desc}", styles['Normal']))
    story.append(Paragraph(f"<b>ROI Provider:</b> {roi_provider}", styles['Normal']))
    story.append(Paragraph(f"<b>Voxel Spacing (mm):</b> {spacing}", styles['Normal']))
    story.append(Paragraph(f"<b>Volume Shape (z,y,x):</b> {vol_shape}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # SECTION: OMC Patency (from clinical report)
    story.append(Paragraph('<b>Ostiomeatal Complex (OMC) Patency</b>', styles['Heading2']))
    story.append(Paragraph(
        'Air fraction within standardized ROI corridors at mid-facial level. '
        'Values represent percentage of voxels below air threshold (−400 HU).',
        styles['Normal']
    ))
    story.append(Spacer(1, 0.1*inch))

    omc = clin.get('metrics', {}).get('omc_patency', {})
    omc_data = [
        ['Side', 'Air Fraction (%)', 'Status', 'Reference Range'],
        ['Left OMC', f"{omc.get('left_score', 0):.1f}%", omc.get('left_status', 'Unknown'), '> 12% (Patent)'],
        ['Right OMC', f"{omc.get('right_score', 0):.1f}%", omc.get('right_status', 'Unknown'), '> 12% (Patent)'],
    ]
    omc_table = Table(omc_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
    omc_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
    ]))
    story.append(omc_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        '<i>Classification thresholds: Patent (>12%), Indeterminate (8–12%), Obstructed (<8%). '
        'Based on multi-candidate corridor method with ROI optimization.</i>',
        styles['Normal']
    ))
    story.append(Spacer(1, 0.3*inch))

    # SECTION: Bone Analysis (from clinical report)
    story.append(Paragraph('<b>Sinus Bone Analysis</b>', styles['Heading2']))
    bone = clin.get('metrics', {}).get('bony_changes', {})
    bone_data = [
        ['Measurement', 'Value', 'Reference Range'],
        ['Sclerotic Fraction', f"{bone.get('sclerotic_fraction_pct', 0):.1f}%", '< 5% (Normal)'],
        ['Mean Wall HU', f"{bone.get('bone_mean_hu', 0):.0f} HU", '400–700 HU'],
        ['Reference Bone HU', f"{bone.get('reference_bone_median', 0):.0f} HU", '≈1200 HU (Cortical)'],
    ]
    bone_table = Table(bone_data, colWidths=[2.5*inch, 2*inch, 2*inch])
    bone_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e67e22')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
    ]))
    story.append(bone_table)
    story.append(Spacer(1, 0.3*inch))

    # SECTION: Retention Cysts (from clinical report)
    story.append(Paragraph('<b>Retention Cysts</b>', styles['Heading2']))
    cyst_count = clin.get('metrics', {}).get('retention_cysts', 0)
    story.append(Paragraph(f'<b>Detected Count:</b> {cyst_count}', styles['Normal']))
    story.append(Spacer(1, 0.1*inch))

    # SECTION: Volumetric (from quantitative_analysis)
    story.append(Paragraph('<b>Sinus Volumetric Analysis</b>', styles['Heading2']))
    vol_data = [['Tissue Type', 'Volume (mL)', 'Percentage']]
    vol_metrics = quant.get('volumetric', {})
    if vol_metrics:
        air_vol = vol_metrics.get('air_volume_ml', 0)
        tissue_vol = vol_metrics.get('soft_tissue_volume_ml', 0)
        total = (air_vol or 0) + (tissue_vol or 0)
        vol_data.extend([
            ['Air Cavities', f"{air_vol:.1f}", f"{(100*air_vol/total) if total else 0:.1f}%"],
            ['Soft Tissue', f"{tissue_vol:.1f}", f"{(100*tissue_vol/total) if total else 0:.1f}%"],
            ['Total', f"{total:.1f}", '100%'],
        ])
    else:
        vol_data.append(['Data not available', '-', '-'])
    vol_table = Table(vol_data, colWidths=[2.5*inch, 2*inch, 2*inch])
    vol_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16a085')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
    ]))
    story.append(vol_table)
    story.append(Spacer(1, 0.3*inch))

    # SECTION: Lund–Mackay (from clinical report)
    lm = clin.get('metrics', {}).get('lund_mackay', {})
    if lm:
        story.append(Paragraph('<b>Lund–Mackay Staging</b>', styles['Heading2']))
        by_region = lm.get('by_region', {})
        lm_data = [
            ['Sinus Region', 'Left Score', 'Right Score'],
            ['Maxillary', by_region.get('maxillary', {}).get('L', '-'), by_region.get('maxillary', {}).get('R', '-')],
            ['Anterior Ethmoid', by_region.get('ant_ethmoid', {}).get('L', '-'), by_region.get('ant_ethmoid', {}).get('R', '-')],
            ['Posterior Ethmoid', by_region.get('post_ethmoid', {}).get('L', '-'), by_region.get('post_ethmoid', {}).get('R', '-')],
            ['Sphenoid', by_region.get('sphenoid', {}).get('L', '-'), by_region.get('sphenoid', {}).get('R', '-')],
            ['Frontal', by_region.get('frontal', {}).get('L', '-'), by_region.get('frontal', {}).get('R', '-')],
        ]
        omc_scores = lm.get('omc', {})
        if omc_scores:
            lm_data.append(['OMC Obstruction', omc_scores.get('L', '-'), omc_scores.get('R', '-')])
        lm_table = Table(lm_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        lm_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8e44ad')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ]))
        story.append(lm_table)
        story.append(Spacer(1, 0.3*inch))

    # SECTION: Deep Sinuses (from comprehensive JSON if present, else clinical->metrics.deep_sinuses)
    deep = comp.get('deep_sinuses') or clin.get('metrics', {}).get('deep_sinuses', {})
    if deep:
        story.append(Paragraph('<b>Deep Sinus Analysis</b>', styles['Heading2']))
        sphenoid = deep.get('sphenoid', {})
        sphenoid_opacity = deep.get('sphenoid_opacification', {})
        if sphenoid:
            sphenoid_data = [
                ['Sphenoid Metric', 'Value', 'Interpretation'],
                ['Total Volume', f"{sphenoid.get('sphenoid_volume_ml', 0):.1f} mL", 'Normal: 5–10 mL'],
                ['Left Volume', f"{sphenoid.get('left_volume_ml', 0):.1f} mL", ''],
                ['Right Volume', f"{sphenoid.get('right_volume_ml', 0):.1f} mL", ''],
                ['Pneumatization Grade', sphenoid.get('pneumatization_grade', '-') , '0–3 (Conchal→Postsellar)'],
                ['Air Fraction', f"{sphenoid.get('air_fraction', 0)*100:.1f}%", 'Normal: >90%'],
            ]
            if sphenoid_opacity:
                grade_map = {0: 'Clear', 1: 'Partial', 2: 'Complete'}
                left_grade = sphenoid_opacity.get('left_opacification_grade', -1)
                right_grade = sphenoid_opacity.get('right_opacification_grade', -1)
                left_opacity = grade_map.get(left_grade, '-')
                right_opacity = grade_map.get(right_grade, '-')
                sphenoid_data.append(['Opacification', f"L: {left_opacity}, R: {right_opacity}", ''])
            sphenoid_table = Table(sphenoid_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
            sphenoid_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16a085')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ]))
            story.append(sphenoid_table)
            story.append(Spacer(1, 0.15*inch))
        post_eth = deep.get('posterior_ethmoid', {})
        if post_eth:
            post_eth_data = [
                ['Posterior Ethmoid Metric', 'Value', 'Notes'],
                ['Total Volume', f"{post_eth.get('posterior_ethmoid_volume_ml', 0):.1f} mL", ''],
                ['Estimated Cell Count', post_eth.get('cell_count_estimate', '-') , ''],
                ['Air Fraction', f"{post_eth.get('air_fraction', 0)*100:.1f}%", 'Normal: >80%'],
            ]
            post_eth_table = Table(post_eth_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
            post_eth_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16a085')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ]))
            story.append(post_eth_table)
            story.append(Spacer(1, 0.15*inch))
        skull_base = deep.get('skull_base', {})
        if skull_base:
            skull_data = [
                ['Skull Base Metric', 'Value', 'Interpretation'],
                ['Mean Thickness', f"{skull_base.get('mean_thickness_mm', 0):.2f} mm", 'Normal: 1–3 mm'],
                ['Min Thickness', f"{skull_base.get('minimum_thickness_mm', 0):.2f} mm", 'Integrity check'],
                ['Bone Volume', f"{skull_base.get('bone_volume_ml', 0):.1f} mL", 'Bone-only mask'],
                ['Bone Mean HU', f"{skull_base.get('bone_hu_mean', 0):.0f} HU", ''],
            ]
            skull_table = Table(skull_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
            skull_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16a085')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ]))
            story.append(skull_table)
            story.append(Spacer(1, 0.1*inch))

    # SECTION: Skull Structures (from comprehensive JSON)
    skull_structures = comp.get('skull_structures', {})
    skull = skull_structures.get('skull') if isinstance(skull_structures, dict) else None
    if skull:
        story.append(Paragraph('<b>Skull Structures</b>', styles['Heading2']))
        skull_data = [
            ['Structure', 'Volume (mL)', 'Mean HU', 'Voxels'],
            ['Skull', f"{skull.get('volume_ml', 0):.1f}", f"{skull.get('mean_hu', 0):.0f}", f"{skull.get('voxel_count', 0)}"],
        ]
        skull_table = Table(skull_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        skull_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ]))
        story.append(skull_table)
        story.append(Spacer(1, 0.3*inch))

    # SECTION: Temporal Bones (from comprehensive JSON)
    temporal = comp.get('temporal_bones', {})
    story.append(Paragraph('<b>Temporal Bones (Mastoid Air Cells)</b>', styles['Heading2']))
    if temporal and 'error' not in temporal:
        for side in ['left', 'right']:
            if side in temporal and 'error' not in temporal[side]:
                t = temporal[side]
                t_data = [
                    [f"{side.capitalize()} Metric", 'Value', 'Reference'],
                    ['Total Volume', f"{t.get('total_volume_ml', 0):.1f} mL", '—'],
                    ['Pneumatization', f"{t.get('pneumatization_pct', 0):.1f}%", 'Normal: 40–60%'],
                    ['Mastoid Air Volume', f"{t.get('air_volume_ml', 0):.1f} mL", '—'],
                    ['Soft Tissue', f"{t.get('soft_tissue_pct', 0):.1f}%", '< 10%'],
                    ['Mean Bone HU', f"{t.get('mean_bone_hu', 0):.0f} HU", '—'],
                ]
                t_table = Table(t_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
                t_table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#d35400')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 9),
                    ('ALIGN', (1,0), (1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ]))
                story.append(t_table)
                story.append(Spacer(1, 0.15*inch))
        # Screening notes
        scr = temporal.get('mastoiditis_screening', {})
        notes = scr.get('notes', [])
        if notes:
            story.append(Paragraph('Findings:', styles['Italic']))
            for n in notes:
                story.append(Paragraph(f'• {n}', styles['Normal']))
        elif temporal.get('note'):
            story.append(Paragraph(temporal['note'], styles['Normal']))
    else:
        note = temporal.get('note', 'Temporal bones not segmented or not in scan') if isinstance(temporal, dict) else 'Not available'
        story.append(Paragraph(f'<i>{note}</i>', styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # SECTION: Brain (from comprehensive JSON)
    brain = comp.get('brain', {})
    story.append(Paragraph('<b>Brain Structures</b>', styles['Heading2']))
    if brain and 'error' not in brain:
        b = brain.get('brain', {})
        if b:
            b_data = [
                ['Brain Metric', 'Value', 'Reference'],
                ['Total Volume', f"{b.get('total_volume_ml', 0):.0f} mL", 'Adult: 1200–1400 mL'],
                ['Mean HU', f"{b.get('mean_hu', 0):.1f}", 'Normal: 30–35 HU'],
                ['CSF Fraction', f"{b.get('csf_fraction_pct', 0):.1f}%", 'Normal: 10–15%'],
                ['White Matter Vol', f"{b.get('white_matter_volume_ml', 0):.0f} mL", '—'],
                ['Gray Matter Vol', f"{b.get('gray_matter_volume_ml', 0):.0f} mL", '—'],
            ]
            b_table = Table(b_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
            b_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ]))
            story.append(b_table)
            story.append(Spacer(1, 0.15*inch))
        # Abnormality screening notes
        scr = brain.get('abnormality_screening', {})
        notes = scr.get('notes', [])
        if notes:
            story.append(Paragraph('Findings:', styles['Italic']))
            for n in notes:
                story.append(Paragraph(f'• {n}', styles['Normal']))
        elif brain.get('note'):
            story.append(Paragraph(brain['note'], styles['Normal']))
    else:
        note = brain.get('note', 'Brain not segmented or not in scan') if isinstance(brain, dict) else 'Not available'
        story.append(Paragraph(f'<i>{note}</i>', styles['Normal']))
    story.append(Spacer(1, 0.4*inch))

    # SECTION: Methods & Notes (concise)
    story.append(Paragraph('<b>Methods (Operational)</b>', styles['Heading2']))
    methods = (
        'Axial CT series processed into NIfTI preserving voxel spacing. Air threshold −400 HU; '
        'soft tissue −100..100 HU; bone >200 HU. TotalSegmentator used when available for skull/brain/ears; '
        'sinus ROIs based on standardized corridors. Deep sinus analysis measures sphenoid/ethmoid and skull base.'
    )
    story.append(Paragraph(methods, styles['Normal']))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph('<b>Notes</b>', styles['Heading2']))
    story.append(Paragraph(
        'This report is an objective summary of automated measurements with reference ranges. '
        'Clinical interpretation should be performed by qualified professionals in context of symptoms and exam.',
        styles['Normal']
    ))

    # Build PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )
    doc.build(story)

    print(f"\u2713 Generated comprehensive report: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Generate unified Head CT analysis PDF report')
    parser.add_argument('--comprehensive', default='docs/metrics/comprehensive_head_analysis.json', help='Path to comprehensive JSON (from HeadCTAnalyzer)')
    parser.add_argument('--clinical', default='docs/metrics/clinical_analysis_report.json', help='Path to clinical sinus JSON')
    parser.add_argument('--quant', default='docs/metrics/quantitative_analysis.json', help='Path to quantitative sinus JSON')
    parser.add_argument('--meta', default='docs/last_run_meta.json', help='Path to scan metadata JSON')
    parser.add_argument('--output', default='docs/report/comprehensive_report.pdf', help='Output PDF path')

    args = parser.parse_args()

    create_report(
        comprehensive_path=args.comprehensive,
        clinical_path=args.clinical,
        quantitative_path=args.quant,
        meta_path=args.meta,
        output_path=args.output,
    )


if __name__ == '__main__':
    main()
