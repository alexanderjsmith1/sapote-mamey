# Figure: Per-strain BGC ranking (spotlight)

- **id:** `fig_per_strain_bgc_ranking`
- **category:** per_strain
- **audience:** presentation
- **output:** `fig_per_strain_bgc_ranking.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv`
- **columns used:** sid, bgc_id, region, length_kb, edge_status
- **row filter:** sid == <SID>; top 10 by length_kb
- **derived fields:** label = bgc_id (region)

## Plot
- **type:** horizontal bar
- **x:** length_kb   **y:** bgc_id (region)   **color:** edge_status
- **order:** by length_kb desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Largest candidate BGCs in <SID> by region length; colour = edge status (completeness).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Spotlight the flagship cluster on the slide (e.g. the megacluster) with a callout box.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
