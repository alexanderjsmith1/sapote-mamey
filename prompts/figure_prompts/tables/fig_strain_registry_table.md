# Figure: Strain registry table (slide-ready)

- **id:** `fig_strain_registry_table`
- **category:** tables
- **audience:** presentation
- **output:** `fig_strain_registry_table.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** sid, organism, assembly_grade, contigs, n50, raw_bgcs, corrected_bgcs
- **row filter:** all strains
- **derived fields:** —

## Plot
- **type:** formatted table (zebra rows, tier-colored grade cell)
- **x:** —   **y:** —   **color:** grade cell
- **order:** by corrected_bgcs desc   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Strain registry: assembly metrics and BGC counts (n = 18).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Keep to ≤12 rows per slide; split if more.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
