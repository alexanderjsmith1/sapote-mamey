# Figure: Reported KnownClusterBlast top-hit presence per isolate

- **id:** `fig_kcb_dark_by_strain`
- **category:** novelty
- **audience:** manuscript + presentation
- **output:** `fig_kcb_dark_by_strain.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv`
- **columns used:** strain, kcb_top_present (1 = reported top-hit text present; 0 = absent text, including missing/NOT_APPLICABLE; completed-search status not encoded)
- **row filter:** source-bound BGC rows; report missing/unbound search coverage separately
- **derived fields:** per isolate: fraction with exported top-hit text present; do not classify zero as verified no-match without separately admitted completed-search evidence

## Plot
- **type:** horizontal bar
- **x:** % BGCs with reported top-hit text   **y:** strain   **color:** single series
- **order:** by % desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Reported KnownClusterBlast top-hit-text presence per isolate (n = <admitted_isolate_n> isolates); state admitted BGC/search denominators and missing or unbound coverage. Top-hit presence is similarity context, and exported zero is not proof of novel chemistry or a verified no-match search.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Discuss assembly/search-coverage associations only when supported by this set; do not retain a directional claim from the earlier no-top-hit metric.

## Build note
The exporter supplies the named CSV fields. `tools/plot_examples.py` does not draw
this recipe; see [renderer choice](../HOW_TO_USE.md#renderer-choice).
