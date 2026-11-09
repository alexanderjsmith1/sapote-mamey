# Figure Reproducibility — data + recipe travel with every figure

Companion to [FIGURE_STYLE.md](FIGURE_STYLE.md). That rule says a figure carries data only (interpretation goes in the
caption). This rule says **every figure also ships with the data it was plotted from and a way to
regenerate it after an edit**, so a figure can be shown alongside its data.

A last-minute change, such as dropping a strain or a BGC, is then an edited copy of that data plus a
replot, where the renderer has a replot path. After the change, recheck the source binding and the
denominator.

## What ships with each figure
1. **The plotted data** — a per-figure CSV holding the exact data behind the bars or points, in
   editable form. No bundle tool writes a figure-data workbook.
2. **A recipe** — what the figure shows and how to regenerate it after adding/removing data
   (e.g. `normalization_recipe.md`).
3. **The clean PNG** — FIGURE_STYLE-compliant (no overlays/arrows; color + legend carry the signal).

## The edit-then-replot pattern (reference implementation)
`tools/build_normalization_matrix.py` is the model every figure tool should follow:
- It writes an **editable source CSV** (`normalization_per_strain.csv` — one row per strain) plus the
  derived ranking/matrix CSVs and the figures.
- `--replot` reads the (possibly edited) source CSV and regenerates everything **without** recomputing
  from the cohort. The CSV must have one row per strain; a strain ID on two rows stops the replot.
  Delete a strain's only row, run `--replot`, and that strain drops out of every derived output —
  the last-minute drop workflow.
- Drop `--replot` to rebuild from the bank instead (picks up newly banked strains). The rebuild has one
  row per strain in the bank's strain roster. BGC rows whose strain ID is not in that roster are not
  counted; the tool prints their count by strain ID and writes it under "Coverage" in
  `normalization_recipe.md`.

## Requirement for new figure tools
A new or revised figure tool needs an editable source CSV, a replot path that respects edits to that
CSV, and a recipe entry. No figure should be a dead-end PNG whose data can't be recovered or edited.

`tools/build_figures.py` already meets this: it writes `<figure>_data.csv` beside each PNG and
`figures_recipe.md` in `--out-dir`, and `--replot` redraws from the edited CSVs.

## Limits of the normalization replot

The normalization example is one replot implementation. Other bundle renderers may not accept CSV edits the same way.

- `--replot` reads `normalization_per_strain.csv` from `--out-dir` and rewrites fixed file names there. It writes no source, config or output hash receipt.
- Deleting a row is a new selection. It changes the denominator, the correlations and the ranking. Keep the original CSV, hash the edited one, record why rows were dropped, and rebuild into a fresh review folder.
- Replot refuses a strain ID on more than one row. It does not check that values are finite or nonnegative, or bind rows to a source.
- Classes are counted by substring match, not by an exclusive taxonomy. Classes with a total count below five are left out. If none reaches five, the ranking and matrix CSVs have headers only, no figure is drawn, `normalization_recipe.md` records `NO_CLASS_MET_THRESHOLD`, and a PNG from an earlier run is not removed.
- A correlation cell is blank with fewer than ten eligible rows or zero variance. A NaN or infinite correlation gives a blank cell, the regime `not measurable` and no bar. Blank is not zero and not a measured lack of association.
- A contig count of zero is raised to one before the log transform, and some upstream missing fields default to zero. Check missingness before you interpret a result.
- Correlation and regime labels are descriptive. They do not correct for fragmentation or pick a valid normalizer.
- Derived CSVs are written before plotting and the recipe after, so a failed plot can leave a mixed set of old and new files.
- PNGs are saved at 160 dpi with no vector copy, so publication artwork needs its own check.
- The bank reader guard runs in both branches, `--replot` included.
- A source CSV and recipe do not show complete source coverage, exact identity or library versions. Keep source, renderer, argument and environment hashes and the exclusions with the output. [R redraws](R_FIGURE_WORKFLOWS.md) need their own receipt bindings too.

Source owner: `tools/build_normalization_matrix.py`.
