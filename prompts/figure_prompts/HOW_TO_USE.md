# How to use the figure prompts

This folder is a menu of figure recipes. Each `.md` file is one spec: which figure,
from which data, how it is encoded, and a suggested caption. Hand one to an assistant
or follow it yourself. A prompt describes a figure. It does not draw one.

## Steps

1. Export tidy tables from your master workbook (the `.xlsx` that collects every
   strain's results):

   ```bash
   python tools/export_figure_ready.py path/to/master_workbook.xlsx
   ```

   This writes a `figure_ready/` folder next to the workbook, with the CSV files the
   prompts use and a `DATA_DICTIONARY.md`. The folder must be new or empty. If it
   exists with files in it, the tool stops with `FIGURE_EXPORT_REQUIRES_FRESH_OUTPUT`.
   Give a different folder as the second argument.
2. Pick a prompt from a category folder or from `_INDEX.md`.
3. Find the renderer for that figure type in [Figures start here](../../docs/FIGURES_START_HERE.md)
   and use it. If no renderer fits, stop and ask the maintainer. A prompt that needs
   a new kind of encoding is not drawn by hand.
4. Check the prompt's **Data** block against the real column names in your CSV files.
5. Read `FIGURE_CONVENTIONS.md` once. It applies to every prompt. The main rule is no
   arrows, callouts or highlights on the plot. Put interpretation in the caption. Put
   any emphasis on the slide, using the prompt's **Overlay suggestions**.
6. Look at the finished image before you use it. Keep the renderer settings and input
   file hashes with the figure.

`tools/plot_examples.py` draws only three reference figures. Run it as
`python tools/plot_examples.py figure_ready --out-dir <fresh-folder>`. Without `--out-dir` the
PNGs go into the `figure_ready` folder. An existing PNG of the same name is refused (exit 2,
`OUTPUT_REFUSED`), not replaced. It needs non-empty `strain_summary.csv`,
`class_prevalence.csv` and `class_by_strain.csv`, a unique list of strains, and a
positive, finite N50 for every strain (the axis is logarithmic). A missing correction
value stays uncomputed. Do not fill it with zero.

In the heatmap, each absent isolate/class row is unreported and drawn grey, even when other
classes are recorded for that isolate. An explicit zero row is shown as zero. Sparse data alone
does not establish that an unreported class was assessed.

## Categories

- `cohort/`: views across many genomes at once.
- `per_strain/`: one strain, for a deep-dive package or a spotlight slide.
- `novelty/`: figures about clusters with no known-cluster match, and about
  MIBiG (a public catalog of characterized clusters) anchors.
- `ecological/`: transcription-factor-binding-site and ecological-signal figures.
- `tables/`: slide-ready tables.
- `deliverable_maps/`: recipes that combine library figures into one named deliverable.

## Read the export correctly

- Column names are the ones in `DATA_DICTIONARY.md`, for example `strain`,
  `assembly_tier`, `assembly_bp` and `boundary`. Older names in a recipe are not
  accepted aliases.
- `kcb_top_present=0` means no top-hit text was exported. A missing value and
  `NOT_APPLICABLE` also become `0`. It does not show that a search found nothing, and
  it does not show new chemistry. Record the search and its coverage separately.
  Treat clusters that were not searched as unknown.
- `diagnostics_long.csv` describes whole strains. It has no cluster column, so it
  cannot say which cluster carries a marker. To assign a marker to a cluster, join on
  `strain / full node-or-contig / region / BGC alias`. Never copy a strain-level
  marker onto every cluster.
- A recipe that handles missing values itself must say which subset it plotted and
  the denominator.

## Change a prompt

Change `FIGURE_CONVENTIONS.md` and the affected prompt's **Data** and **Plot** blocks
together, with the renderer that draws them. Keep file names and column names
stable. Update any roster or denominator the change touches.
