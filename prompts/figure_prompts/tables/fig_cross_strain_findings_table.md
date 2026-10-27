# Figure: Findings across isolates findings table (claim-tagged)

- **id:** `fig_cross_strain_findings_table`
- **category:** tables
- **audience:** manuscript + presentation
- **output:** `fig_cross_strain_findings_table.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/cross_strain_findings.csv`
- **columns used:** finding, metric, value, claim_status, note
- **row filter:** all findings
- **derived fields:** REQUIRES the cross-strain analysis overlay (Cross_Strain_Findings sheet) to have been generated; this CSV is emitted by export_figure_ready.py only when that sheet is present. It is a synthesis product, not a raw canonical sheet.

## Plot
- **type:** formatted table; color the claim_status cell
- **x:** —   **y:** —   **color:** claim_status (GROUNDED/FLAG/CAVEAT/PRIORITY/UNEXERCISED)
- **order:** by #   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Findings across isolates from the bound synthesis sheet with its explicit claim-status labels. Report any non-reproduction conclusion and count only when separately supported; export does not revalidate these findings.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Color-code claim_status consistently with the deck theme.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
