# Figure: Priority-leads table

- **id:** `fig_top_leads_table`
- **category:** tables
- **audience:** presentation
- **output:** `fig_top_leads_table.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/diagnostics_long.csv + bgc_inventory.csv`
- **columns used:** diagnostics_long: sid, diagnostic_name, present; bgc_inventory: sid, bgc_id, contig, region, length_kb, edge_status
- **row filter:** diagnostics_long.present==1 for high-value diagnostics (e.g. enediyne); join to that strain's candidate BGCs
- **derived fields:** lead label = bgc_id (contig·region); priority ranked by diagnostic value then length_kb

## Plot
- **type:** formatted table
- **x:** —   **y:** —   **color:** diagnostic_name cell
- **order:** by strain   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Priority candidate leads with full BGC locators and the diagnostic that flagged them; class-level hypotheses pending wet-lab confirmation.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Color-code the diagnostic column consistently with the deck theme.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
