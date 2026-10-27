# Figure: Core ecological signal (iron + osmolyte)

- **id:** `fig_core_ecological_signal_bar`
- **category:** ecological
- **audience:** presentation
- **output:** `fig_core_ecological_signal_bar.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_prevalence.csv`
- **columns used:** product_class, n_strains
- **row filter:** product_class in {ectoine, NI-siderophore, NRP-metallophore}
- **derived fields:** —

## Plot
- **type:** horizontal bar
- **x:** n_strains   **y:** product_class   **color:** single series
- **order:** by n_strains desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Exported annotation-class prevalence for the selected ectoine and siderophore/metallophore labels (n = <admitted_isolate_n> admitted isolates). Report observed counts, denominator and missing coverage. Use core or near-core only when those counts support the declared criterion; this is not measured ecological function or activity.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
The exporter supplies the named CSV fields. `tools/plot_examples.py` does not draw
this recipe; see [renderer choice](../HOW_TO_USE.md#renderer-choice).
