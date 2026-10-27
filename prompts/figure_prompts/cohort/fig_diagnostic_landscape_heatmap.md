# Figure: TIGRFAM diagnostic landscape

- **id:** `fig_diagnostic_landscape_heatmap`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_diagnostic_landscape_heatmap.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/diagnostics_long.csv`
- **columns used:** strain, diagnostic_name, present
- **row filter:** admitted isolates and the four named diagnostics, with explicit source availability
- **derived fields:** pivot only source-validated values of present; retain unavailable cells separately. The exporter omits None cells and can coerce nonnumeric nonempty values to zero. Missing rows/cells are not measured absences; verify finite source counts and completed search scope before accepting a zero. This isolate-level table has no locus key.

## Plot
- **type:** heatmap of validated 0/1 diagnostic values plus a separate unavailable state
- **x:** diagnostic_name (ansamycin/thiopeptide/enediyne/nucleoside)   **y:** strain   **color:** present (0/1)
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Exported TIGRFAM diagnostic values across the admitted cohort (n = <admitted_isolate_n> isolates), with unavailable cells distinguished. State any diagnostic-specific search/exercise status only from its bound source receipt.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Spotlight the enediyne column on the slide for a warhead-leads talk.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
