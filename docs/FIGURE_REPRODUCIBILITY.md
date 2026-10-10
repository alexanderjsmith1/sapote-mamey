# Figure Reproducibility — data + recipe travel with every figure

Companion to `FIGURE_STYLE.md`. That rule says a figure carries data only (interpretation goes in the
caption). This rule says **every figure also ships with the data it was plotted from and a way to
regenerate it after an edit** — so a figure can be presented alongside its data, and a last-minute change
(e.g. a PI decides to drop a strain or a BGC) can be a versioned selection/edit plus replot when the chosen renderer provides that path; source binding and denominator policy must be rechecked.

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

## Implemented reference versus delivery requirement

The normalization example is a specific replot implementation, not a guarantee every bundle renderer supports arbitrary CSV edits. `--replot` reads `normalization_per_strain.csv` from `--out-dir` and derives ranking/matrix/figures there, overwriting fixed files. It does not issue source/config/output hash receipts or recertify an altered cohort manifest. A row deletion changes the denominator and any correlations/ranking. Keep the original source CSV, hash the edited selection/version, retain its exclusion rationale and rebuild into a fresh review copy before accepting revised figures.

The source counts product classes by substring membership, not a globally exclusive taxonomy. Classes with total count below five are omitted from the ranking/matrix. Per-denominator correlation cells are blank when fewer than ten eligible rows or zero variance applies; blank is not zero or demonstrated absence of association. Source contig count zero is coerced to at least one before log transformation, and some upstream missing fields default to zero. Audit that missingness before scientific interpretation. Correlation/regime labels are descriptive heuristics, not causal fragmentation correction or automatic valid-normalizer selection.

Current normalization PNG saves request 160 dpi and have no vector companion; they need a separate publication artwork/delivery check. The tool still calls the bank reader guard before either branch, even `--replot`, so dependency/source-access preconditions are not implied away by that option. A source CSV and recipe are necessary review material but do not alone prove lossless source coverage, exact identity or reproducible library versions. Carry source/renderer/arguments/environment hashes and typed exclusions with the output. [R redraws](R_FIGURE_WORKFLOWS.md) likewise require fresh receipt bindings.

Source owner: `tools/build_normalization_matrix.py:72–117,121–173`.
