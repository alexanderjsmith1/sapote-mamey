# Figure: Per-strain cohort-context mini panel

- **id:** `fig_per_strain_cohort_context_panel`
- **category:** per_strain
- **audience:** presentation
- **output:** `fig_per_strain_cohort_context_panel.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv + class_by_strain.csv + bgc_inventory.csv`
- **columns used:** strain_summary: sid, corrected_bgcs; class_by_strain: sid, product_class; bgc_inventory: sid, kcb_top_present
- **row filter:** sid == <SID> (rank/shared computed across all strains in the export)
- **derived fields:** corrected_rank = rank of corrected_bgcs across cohort; shared/unique classes = this strain's classes vs all others; zero_KCB = count of kcb_top_present==0 for this sid

## Plot
- **type:** small multiples: 3–4 single-number "stat cards" + one rank bar
- **x:** —   **y:** —   **color:** —
- **order:** —   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Where <SID> sits in the 18-strain cohort: corrected-BGC rank, shared vs unique classes, KCB-dark region count.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Designed to drop next to a strain headshot/colony photo on a title slide.
- All values are computed from the canonical export (no special overlay sheet required).

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
