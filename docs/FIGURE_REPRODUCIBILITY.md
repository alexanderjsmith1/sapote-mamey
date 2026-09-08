# Figure Reproducibility — data + recipe travel with every figure

Companion to `FIGURE_STYLE.md`. That rule says a figure carries data only (interpretation goes in the
caption). This rule says **every figure also ships with the data it was plotted from and a way to
regenerate it after an edit** — so a figure can be presented alongside its data, and a last-minute change
(e.g. a PI decides to drop a strain or a BGC) is a CSV edit + replot, never a re-derivation by hand.

## What ships with each figure
1. **The plotted data** — either a per-figure CSV, or one sheet per figure in `Sapote_Figure_Data.xlsx`.
   This is the exact data behind the bars/points, in editable form.
2. **A recipe** — what the figure shows and how to regenerate it after adding/removing data
   (e.g. `normalization_recipe.md`).
3. **The clean PNG** — FIGURE_STYLE-compliant (no overlays/arrows; color + legend carry the signal).

## The edit-then-replot pattern (reference implementation)
`tools/build_normalization_matrix.py` is the model every figure tool should follow:
- It writes an **editable source CSV** (`normalization_per_strain.csv` — one row per strain) plus the
  derived ranking/matrix CSVs and the figures.
- `--replot` reads the (possibly edited) source CSV and regenerates everything **without** recomputing
  from the cohort. Delete a strain's row, run `--replot`, and that strain vanishes from every output
  consistently — the exact "PI drop a data point at the last minute" workflow.
- Drop `--replot` to rebuild from the full cohort instead (picks up newly banked strains).

## Requirement for future figure tools
When `tools/build_figures.py` is built, every figure it emits must come with: the editable source CSV (or a
sheet in the figure-data workbook), a replot path that respects edits to that CSV, and a recipe entry. No
figure should be a dead-end PNG whose data can't be recovered or edited.
