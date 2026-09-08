# Figure: Top antibacterial candidate leads

- **id:** `fig_top_antibacterial_leads`
- **category:** tables
- **audience:** presentation
- **output:** `fig_top_antibacterial_leads.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `workbook sheet C1_DAPR_Antibacterial (Sapote judgment) — provisional render seeds from bgc_inventory + bgc_class_long`
- **columns used:** sid, bgc_id (contig·region), class basis, edge_status, length_kb
- **row filter:** DAPR antibacterial tier (Sapote). Provisional seed = BGCs in antibacterial-associated classes (thiopeptide, lanthipeptide*, azole-RiPP, blactam, glycopeptide, amglyccycl), ranked Interior-first then length
- **derived fields:** REQUIRES the C1_DAPR_Antibacterial judgment sheet for the real ranking; the rendered contact-sheet version is a PROVISIONAL class-association seed only. Typed bioactivity metadata may be absent and is never a per-BGC assay claim.

## Plot
- **type:** formatted table
- **x:** —   **y:** —   **color:** class-basis cell
- **order:** by DAPR tier / provisional evidence score   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Top antibacterial candidate leads with full BGC locators (n = 18). Class-level hypotheses; DAPR antibacterial ranking is a Sapote judgment step — provisional until populated.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Mark the wet-lab-prioritised row(s) on the slide once DAPR is run.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
