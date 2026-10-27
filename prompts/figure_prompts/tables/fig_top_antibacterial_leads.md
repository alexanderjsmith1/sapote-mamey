# Figure: Top antibacterial candidate leads

- **id:** `fig_top_antibacterial_leads`
- **category:** tables
- **audience:** presentation
- **output:** `fig_top_antibacterial_leads.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `workbook sheet C1_DAPR_Antibacterial (Sapote judgment) — provisional render seeds from bgc_inventory + bgc_class_long`
- **columns used:** inspect the selected workbook schema. Canonical C1/C2 uses strain, BGC_ID, contig, products, score, lead_tier and boundary; region and length_kb require a source-bound B1_BGC_Master or bgc_inventory join. Legacy judgment sheets use a different schema and need an explicit mapping.
- **row filter:** selected source-bound `C1_DAPR_Antibacterial` rows with actual score/rank and `status_note`. The canonical producer sorts source-derived scores with corrected-rank presence first and retains up to ten rows per channel. This is not completed author judgment or validated class-to-activity attribution; a class-filtered provisional table needs a separately declared approved producer.
- **derived fields:** REQUIRES the C1_DAPR_Antibacterial judgment sheet for the real ranking; the rendered contact-sheet version is a PROVISIONAL class-association seed only. Typed bioactivity metadata may be absent and is never a per-BGC assay claim.

## Plot
- **type:** formatted table
- **x:** —   **y:** —   **color:** class-basis cell
- **order:** by DAPR tier / provisional evidence score   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support. State the displayed row count separately from the cohort isolate count.

> Top antibacterial candidate leads with full BGC locators (n = <admitted_isolate_n> isolates). Class-level hypotheses; DAPR antibacterial ranking is a Sapote judgment step — provisional until populated.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Mark the wet-lab-prioritized row(s) on the slide once DAPR is run.

## Build note
This is a table specification, not an implemented `plot_examples.py` output.
`export_figure_ready.py` does not read/export the C1/C2 judgment sheets. Select
the actual workbook/board, schema and judgment status first; preserve complete
source-bound locus identities and use an approved table/render route. Requested
filenames and vector companions remain requirements to verify.

For canonical C1/C2 rows, bind region and length through the same source record using strain, BGC_ID and full contig, retaining the original workbook/package provenance. Do not shorten the displayed four-part locus identity. Source-derived score/rank is not a completed Sapote judgment; retain status_note and distinguish admitted author judgment from provisional class seeds.
