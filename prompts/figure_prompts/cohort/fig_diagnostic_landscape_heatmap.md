# Figure: TIGRFAM diagnostic landscape

- **id:** `fig_diagnostic_landscape_heatmap`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_diagnostic_landscape_heatmap.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/diagnostics_long.csv`
- **columns used:** sid, diagnostic_name, present
- **row filter:** all strains × 4 diagnostics
- **derived fields:** pivot strain × diagnostic, values = present

## Plot
- **type:** binary heatmap (present/absent)
- **x:** diagnostic_name (ansamycin/thiopeptide/enediyne/nucleoside)   **y:** sid   **color:** present (0/1)
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Diagnostic TIGRFAM presence across the cohort (n = 18). Ansamycin currently unexercised.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Spotlight the enediyne column on the slide for a warhead-leads talk.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
