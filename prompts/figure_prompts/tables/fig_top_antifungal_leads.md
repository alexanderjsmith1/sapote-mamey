# Figure: Top antifungal candidate leads

- **id:** `fig_top_antifungal_leads`
- **category:** tables
- **audience:** presentation
- **output:** `fig_top_antifungal_leads.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `workbook sheet C2_DAPR_Antifungal (Sapote judgment) — provisional render seeds from bgc_inventory + bgc_class_long`
- **columns used:** sid, bgc_id (contig·region), class basis, edge_status, length_kb
- **row filter:** DAPR antifungal tier (Sapote). Provisional seed = BGCs in antifungal-associated classes (nucleoside [polyoxin/nikkomycin-like], polyene); note polyene macrolides often hide inside T1PKS and need DAPR judgment to surface
- **derived fields:** REQUIRES the C2_DAPR_Antifungal judgment sheet for the real ranking; the rendered contact-sheet version is a PROVISIONAL class-association seed only and will be short. Typed bioactivity metadata may be absent.

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
> Top antifungal candidate leads with full BGC locators (n = 18). Class-level hypotheses; DAPR antifungal ranking is a Sapote judgment step — provisional until populated.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
