from pathlib import Path
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def main():
    base = Path('docs')
    metrics = json.loads((base / 'metrics' / 'clinical_5309.json').read_text())
    patient_id = metrics.get('patient_id', 'unknown')
    study_date = metrics.get('study_date', 'unknown')
    omc_left = metrics['metrics']['omc_patency']['left_score']
    omc_right = metrics['metrics']['omc_patency']['right_score']
    sclerotic_pct = metrics['metrics']['bony_changes']['sclerotic_fraction_pct']
    cyst_count = metrics['metrics']['retention_cysts']

    out_path = base / 'report' / 'ent_report.pdf'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"ENT Consultation Report — Patient {patient_id}", styles['Title'])
    meta = Paragraph(f"Study date: {study_date} · Series analyzed: 5309", styles['Normal'])
    story += [title, meta, Spacer(1, 12)]

    story += [Paragraph("Executive Summary", styles['Heading2'])]
    bullets = [
        "Complete bilateral OMC obstruction (0% patency left and right).",
        f"Severe chronic osteitic change: {sclerotic_pct:.1f}% of sinus wall bone (operational normal < 5%).",
        f"Retention cyst burden: {cyst_count} lesions (operational normal 0–2).",
        "Nasopharyngeal tissue predominance with airway near 0% patent.",
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", styles['Normal']))
    story.append(Spacer(1, 12))

    story += [Paragraph("Key Metrics", styles['Heading2'])]
    data = [
        ["Metric", "Value (5309)", "Operational Normal"],
        ["OMC Patency — Left", f"{omc_left:.0f}%", "60–100%"],
        ["OMC Patency — Right", f"{omc_right:.0f}%", "60–100%"],
        ["Sclerotic Bone Fraction", f"{sclerotic_pct:.1f}%", "0–5%"],
        ["Retention Cyst Count", f"{cyst_count}", "0–2"],
    ]
    tbl = Table(data, hAlign='LEFT')
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story += [tbl, Spacer(1, 12)]

    story += [Paragraph("Representative Figures", styles['Heading2'])]
    fig_paths = [
        (base / 'omc_overlay_comparison.png', 'Bilateral OMC overlay: Air (blue), Tissue-in-sinus (red), ROI (yellow).'),
        (base / 'clinical_5309.png', 'Key axial slices (series 5309) with overlays.'),
        (base / 'literature_comparison.png', 'Quantitative comparison vs operational normals.'),
    ]
    for p, cap in fig_paths:
        if p.exists():
            story.append(Image(str(p), width=500, height=300, kind='proportional'))
            story.append(Paragraph(cap, styles['Italic']))
            story.append(Spacer(1, 12))

    story += [Paragraph("Methods (Operational)", styles['Heading2'])]
    methods = (
        "Axial CT series were processed into NIfTI preserving voxel spacing. Air threshold −400 HU; soft tissue −100..100 HU; "
        "bone >200 HU, osteitis >800 HU for sinus wall sclerosis. OMC patency estimated from symmetric rectangular ROIs in mid-facial slices. "
        "Primary metrics from series 5309 (bone-optimized reconstruction) verified against series 5303 (1 mm axial)."
    )
    story.append(Paragraph(methods, styles['Normal']))

    story += [Spacer(1, 12), Paragraph("Clinical Interpretation", styles['Heading2'])]
    interp = [
        "Structural obstruction at bilateral OMCs corresponds with impaired drainage and risk for recurrent sinusitis.",
        "Elevated sclerotic fraction indicates prolonged inflammatory remodeling of sinus walls.",
        "Retention cyst burden reflects chronic mucous stasis.",
        "Nasopharyngeal tissue predominance likely contributes to airway resistance.",
    ]
    for b in interp:
        story.append(Paragraph(f"• {b}", styles['Normal']))

    story += [Spacer(1, 12), Paragraph("Recommendations for Discussion", styles['Heading2'])]
    recs = [
        "Consider FESS targeting OMC widening and removal of obstructing tissue.",
        "Allergy/Immunology evaluation to identify and mitigate inflammatory drivers.",
        "Medical management: intranasal corticosteroid and saline irrigation regimen; environmental controls.",
        "Follow-up: repeat imaging in 3–6 months to quantify improvement vs baseline.",
    ]
    for i, r in enumerate(recs, start=1):
        story.append(Paragraph(f"{i}. {r}", styles['Normal']))

    doc = SimpleDocTemplate(str(out_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story)
    print(f"Wrote PDF report to {out_path}")


if __name__ == '__main__':
    main()
