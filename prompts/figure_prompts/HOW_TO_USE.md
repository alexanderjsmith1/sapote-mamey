# HOW_TO_USE — figure-prompt library

This folder is a menu of figure recipes. Hand one to an assistant or build it yourself.
Each `.md` is a self-contained spec: what figure, from which data, how encoded, with a suggested
caption and a separate list of overlay ideas to add downstream.

## Workflow
1. Produce the tidy data first: `python tools/export_figure_ready.py <master_workbook.xlsx>`
   → creates `figure_ready/` with the CSVs these prompts reference.
2. Pick a prompt from a category folder (or `_INDEX.md`).
3. Treat the prompt as a specification and select the documented bundle renderer for the figure type via `docs/FIGURES_START_HERE.md`. Use only the bundle route or an explicitly owner-approved staged patch; an unsupported encoding remains a renderer hold. A prompt is not an automatic renderer. Check each **Data** block against the actual source headers and row scope.
4. Read `FIGURE_CONVENTIONS.md` once; it is inherited by all prompts (especially: no arrows on
   data points — overlays go on the slide).
5. Add emphasis (arrows, callouts, logos) downstream in PowerPoint / BioRender, using each
   prompt's **Overlay suggestions**.

## Renderer choice
`tools/plot_examples.py` draws only its three reference figures. For any other recipe, use the approved renderer for that figure type from `docs/FIGURES_START_HERE.md`. If none fits, hold the figure. Keep the renderer settings, input hashes and your visual review with the delivered files.

## Categories
- `cohort/` — broad cross-genome views (the Sapote-Mamey signature: many genomes at once).
- `per_strain/` — single-strain figures for a deep-dive package or a spotlight slide.
- `novelty/` — KCB-dark / MIBiG-anchor / novelty figures.
- `ecological/` — TFBS and ecological-signal figures (Module 11 territory).
- `tables/` — slide-ready formatted tables (still "figures" for a deck).

## Modifying for consistency
Propose changes to `FIGURE_CONVENTIONS.md` and the affected prompt **Data**/**Plot** blocks together with the owning renderer/style contract. A local recipe edit does not approve a new rendering default. Keep slugs and column names stable and bind any changed roster or denominator.

## Export schema and evidence limits
Read the emitted `DATA_DICTIONARY.md` and actual CSV headers before plotting. CSV keys include `strain`, `assembly_tier`, `assembly_bp` and `boundary`; older recipe names are not aliases accepted by the exporter. Keep schema field names distinct from public isolate wording. `kcb_top_present=0` means no top-hit text was exported; missing and `NOT_APPLICABLE` values also become zero. It does not prove a completed no-match search or new chemistry. Bind search provenance and coverage separately and keep unsearched/unbound cases unknown. `diagnostics_long.csv` is isolate-level context: it has no locus key and cannot identify the diagnostic-bearing BGC. Per-locus attribution needs a source-bound join on `strain / full node-or-contig / region / BGC alias`; do not broadcast aggregate markers to every candidate.

## Numeric completeness for the reference plot set
`tools/plot_examples.py` needs nonempty strain_summary.csv, class_prevalence.csv and class_by_strain.csv with their actual headers and a bound, unique isolate roster. Every plotted N50 must be finite and positive for the log axis, and the loss/count fields must be finite source-derived values. A workbook header/structural PASS does not establish that these values exist. A missing A3 correction value leaves corrected count and fragmentation loss uncomputed; do not substitute zero. Resolve those holds before this three-figure reference run. Other recipes may handle missingness explicitly, but must report any admitted subset and its denominator.
