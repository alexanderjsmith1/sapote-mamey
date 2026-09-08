# FIGURES_START_HERE — how to make Sapote–Mamey figures (read before plotting anything)

**Current bundle:** Sapote–Mamey v9.7.408 · Mamey engine 1.9.148 (see `BUILD_STAMP.txt`; this line is checked by
`tools/seal_sweep.py`).

**If you are about to hand-write matplotlib for a Sapote–Mamey figure: stop and read this first.**
The bundle already has the figure you want, with a stable ID, an exact data source, and a locked
house style. Re-inventing it produces an off-palette one-off that breaks the coherent set.

## The 30-second map
1. **Catalog of every figure:** `prompts/figure_prompts/_INDEX.md` — the named figures
   (cohort / per_strain / novelty / ecological / tables) + the deliverable-map recipes. Each row
   names the figure ID and its exact `figure_ready/` data source.
2. **Global house rules (read once, inherited by all):** `prompts/figure_prompts/FIGURE_CONVENTIONS.md`
   — palette, legend placement, no-arrows-on-data rule, typography, claim-safe captions.
3. **How the workflow runs:** `prompts/figure_prompts/HOW_TO_USE.md`.
4. **Per-figure spec:** open the matching `.md` in `prompts/figure_prompts/<category>/` — it gives
   the data file, columns, row filter, plot type, suggested caption, and downstream-overlay notes.

## The data contract (do this once per cohort/strain set)
Every figure plots from tidy `figure_ready/*.csv`, NOT from the workbook directly. Generate them:
```
python tools/export_figure_ready.py <master_workbook.xlsx> [figure_ready/]
```
This needs a master workbook with `A2_Strain_Registry`, `A3_Run_Manifest`, and `B1_BGC_Master`
sheets. (For an ad-hoc 1–2 strain set without that workbook, emit the CSVs by hand to the same
column contract — see `_INDEX.md` data-source column lists. `tools/plot_examples.py` is the
reference renderer that proves the CSVs are plot-ready.)

The tidy CSVs: `strain_summary, bgc_inventory, bgc_class_long, class_by_strain, class_prevalence,
diagnostics_long, other_breakdown, cross_strain_findings`.

## Rendering — two routes
- **Engine route (preferred, always house-consistent):**
  `python -m mamey render-figures --package <pkg> --outdir figures/ --top-n 10`
  and the dedicated builders in `tools/` (see inventory below). The native DAPR/RG-GMCI set reads
  the master workbook through a schema adapter (coded `A2_/C1_/C2_/D1_` names + legacy fallbacks);
  if it returns `NO_DATA` the cohort simply hasn't been through a Sapote scoring pass yet (the DAPR
  lead sheets are still empty scaffolds), which is distinct from a `NO_FIGURES` read failure.
- **Prompt route (when you want a specific figure or are an LLM):** open the figure's `.md` spec,
  follow its Data + Plot blocks, inherit `FIGURE_CONVENTIONS.md`. Emit a clean PNG **plus** the
  companion `_data.csv` and a caption line in a `*_Captions.md`.

## The non-negotiable house rules (from FIGURE_CONVENTIONS.md + FIGURE_STYLE.md)
- **Palette is LOCKED (blues-led):** primary `#2c6fbb` (blue); secondary/categorical green family
  `#a8ddb5 / #52a878 / #1d6e44`; sequential-ordinal 3-blue ramp `#cfe0f3 / #7fa9d6 / #3a6ea5`;
  assembly tiers GOOD `#2a9d5a` / MODERATE `#e0a030` / POOR `#cc4444`; heatmaps `viridis`; binary
  present/absent `Blues`. Orange is retired as a series color. Don't pick your own colors.
- **Heatmap normalization:** when one row's max is >5× the median row max, default to row-normalized
  or log1p and say which in the title — a raw-scale heatmap that saturates on one outlier row hides
  all its other signal.
- **No arrows, callouts, circles, or interpretive text on the data.** Overlays are added downstream
  in PowerPoint / BioRender. Interpretation lives in the caption file, never in the PNG.
- **Legend in white space OUTSIDE the data area** (below the x-axis or right of the plot). Never
  overlap a legend with bars/points/cells.
- **Figure = data only; caption carries the claim.** A figure must be re-labelable without a
  rebuild. Captions are claim-safe: antiSMASH/KCB calls are class-level hypotheses ("candidate",
  "consistent with"), never assayed chemistry.
- **Figure IDs:** stable typable IDs (`COHORT-F1`, `DOT-D6`, `HM-…`, `SCAT-S3`); corner-baked ID is
  catalog/ordering only, manuscript figures carry the ID in the caption (or use a `--catalog` flag).
- Font DejaVu Sans (title 13 / axis 11 / tick 9 / value 8); top+right spines off; grid alpha 0.25;
  `savefig.dpi=200` for slides, also emit `.svg`/`.pdf` at 300 for print.
- Strain axis order = corrected-BGC rank from `strain_summary.csv`, so panels line up across figures.
- Exclude the universal classes (saccharide, fatty_acid, other, terpene) from shared/novel
  comparisons unless the figure is specifically about them.
- File naming: `fig_<slug>.png/.svg/.pdf`, snake_case, stable across runs.

## Full inventory (so nothing stays an easter egg)
**Prompt library:** `prompts/figure_prompts/` — `_INDEX.md`, `FIGURE_CONVENTIONS.md`, `HOW_TO_USE.md`,
+ category folders cohort/ per_strain/ novelty/ ecological/ tables/ and deliverable_maps/.

**Render modules (`mamey/`):** `cohort_figures`, `cohort_figures_d` (dot/bubble), `cohort_figures_g`
(rarity/novelty/architecture), `cohort_class_heatmap`, `cohort_figures_bridge` (auto-fire after a
multi-strain run), `cross_strain_figures`, `domain_figures`, `mamey_native_figures` (DAPR/RG-GMCI/
ecology/completeness set), `master_figure_atlas`, `collection_figures` (metadata-gated),
`figures_sapote`, `figures_extra`, `figures_split`, `figure_policy`, `cohort_figure_captions`,
`kcb_locusmap` (v9.7.338 — offline KnownClusterBlast query-vs-MIBiG comparative locus map,
`figures kcb-locusmap`; PNG + SVG + `_data.csv`, similarity not identity), `bigscape_figures`
(GCF network + clinker supporting figures).

**Build tools (`tools/`):** `export_figure_ready.py` (make the CSVs — START HERE), `plot_examples.py`
(reference renderer), `build_figures.py`, `build_overview_figures.py`, `build_panel_figure.py`,
`build_cross_strain_figures.py`, `build_master_figures.py` (`build_master_figure_atlas.py` was a
duplicate CLI shim, retired v9.7.213-audit; use this one — *build_bee_wasp_master_figures.py*,
previously listed here, does not exist anywhere in the tree and has been removed from this list),
`build_subset_panel.py`, `build_validation_panel.py`, `build_workflow_figure.py`,
`generate_bgc_atlas.py`, `build_thesis_diagrams.py`, `build_thesis_vignettes.py`.

**Tests (`tests/`):** the `test_*figure*` / `test_*cohort*` suite guards layout, overlap, label
safety, CSV schema, and policy — run them after touching any figure code.

## If you are an LLM and the user asks for a figure
1. Find the closest ID in `_INDEX.md`. Don't invent a new one if a match exists.
2. If `figure_ready/` is absent, build it (`export_figure_ready.py` or hand-emit the CSV contract).
3. Open the figure's `.md`, render per its Data/Plot blocks, inherit `FIGURE_CONVENTIONS.md`.
4. Emit PNG + `_data.csv` + a caption line. Offer the figure by name as a next-step path.
