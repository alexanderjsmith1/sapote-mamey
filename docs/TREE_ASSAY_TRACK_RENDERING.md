# Selected assay tracks beside an existing tree

Draw bioassay values as bars beside the tips of a tree you already have. Two steps do it:

1. `tools/build_tree_tracks.py` reads your selected assay tracks and writes three files.
2. An R script draws those files against your Newick tree.

You choose the assays and tips. The tools do not pool assays, take a maximum, resolve taxonomy or guess which tip belongs to which strain.

## What you need

- A Newick tree.
- One bioassay track for each series you want to draw (`bioassay_tree_track.tsv`), with its Figure Factory receipt. Make them as described in [Select values for a tree](BIOASSAY_FIGURE_FACTORY.md#tree-and-mode-b-boundary). Each series keeps its own target, material, time point, dose and aggregation. Settle any open growth-control hold there first. Drawing a figure does not clear it.
- A metadata TSV that maps tree tips to strains.
- A config file that lists the tracks.
- R with `ape`, `ggtree`, `ggplot2` and `patchwork`.

### Metadata TSV

One row per tree tip, with these columns:

```
tip	strain	label	role
tip1	ABC-1	Query isolate 1	query
tip5	REF-1	Reference name as deposited	reference
tip6	OUT-1	Outgroup name as deposited	outgroup
```

- `tip` is the exact tip name in the Newick file. Every tree tip appears once.
- `role` is `query`, `reference` or `outgroup`. Only query tips carry assay values.
- `label` is the text shown on the figure. You supply it. The tools do not make up species names or type status.
- Text that starts like a spreadsheet formula is refused. Do not edit an identifier to get past that.

### Config file

```json
{
  "schema": "sapote.tree-tracks.v1",
  "input_root": ".",
  "metadata": {"path": "metadata.tsv", "sha256": "<hash of the file>"},
  "tracks": [
    {"column": "value_48", "label": "Selected 48 h", "colour": "#287D8E",
     "receipt": {"path": "factory_48/bioassay_figure_factory_receipt.json", "sha256": "<hash>"}}
  ]
}
```

- `input_root` is where the other paths start. A relative value is taken from the config file's folder. Paths cannot leave it.
- Each `sha256` must match the file on disk.
- `column` must be unique. It starts with a letter and uses letters, digits and underscores. It cannot be `tip`, `label` or `role`.
- `label` must be unique. `colour` is six-digit hex.

Runnable synthetic examples are in `examples/tree_tracks/` (`grouped.json`, `single.json`, `metadata.tsv`, `tree.newick`). Its [README](../examples/tree_tracks/README.md) says how to reproduce them without changing the originals.

## Step 1. Build the tracks

```bash
python3 tools/build_tree_tracks.py --config examples/tree_tracks/grouped.json \
  --out /path/to/new-track-output
```

Use a folder that does not exist yet. The tool refuses an existing one, even if empty. Keep the folder outside the bundle and outside your source evidence.

It prints nothing when it works and exits 0. Success is a new folder holding exactly three files:

- `tracks.tsv`: one row per tip, with a column per series;
- `series.tsv`: the column, label and colour of each series;
- `track_adapter_receipt.json`: the hashes and selections it used.

The receipt holds the status `PASS_EXACT_ADMITTED_VALUES`. Open it to confirm. If the tool refuses, it prints `TREE_TRACK_REFUSED` with the reason and exits 2. A badly shaped config can still end in a Python traceback.

## Step 2. Draw the figure

```bash
Rscript tools/render_tree_bar_groups.R TREE.newick TRACKS.tsv SERIES.tsv \
  OUT_PREFIX "Title" none none
```

Arguments, in order:

1. the Newick tree;
2. `tracks.tsv`;
3. `series.tsv`;
4. the output prefix, for example `/path/to/new-figure`;
5. the figure title;
6. optional: a numeric display threshold, or `none`;
7. optional: a numeric support threshold for internal-node labels, or `none`.

Leaving out argument 6 or 7 is the same as `none`: no threshold line, and no node labels. To give a support threshold, give argument 6 too (`none` is fine). A node label shows only if it is a number at or above the support threshold. The renderer does not know which method made the label.

`tools/render_tree_one_bar_row.R` takes the same arguments but needs exactly one series.

You get four files: `OUT_PREFIX.pdf`, `OUT_PREFIX.png`, `OUT_PREFIX.tip_order.tsv` and `OUT_PREFIX.cell_states.tsv`. The PDF is 10 inches high, the PNG is 160 dpi, and wide trees cap at 40 inches. The tree's tips must match the metadata tips exactly, or the renderer refuses with `TREE_TRACK_REFUSED`. It also refuses a prefix whose output files already exist.

What the picture shows:

- Topology and branch lengths are kept. Ladderizing only changes the display order.
- Each cell has one of four states, listed per tip and series in `OUT_PREFIX.cell_states.tsv`:
  - `OBSERVED`: a bar;
  - `RECORDED_ZERO`: a dot on the zero line;
  - `NOT_MEASURED`: a query tip with no value, marked with a small gray x on the zero line;
  - `NOT_APPLICABLE`: a reference or outgroup tip, which carries no assay value. It has no mark.
- The subtitle states this key. Negative values are kept, and nothing is clipped to 0 to 100.
- Reference and outgroup bars are refused.

## Check the result

A clean R exit is not a visual check. Open the PNG. Look at label legibility and at blank cells. Large trees need this most.

Keep these together: the config, the metadata, the producer receipts, the three track files, and the figure files. Also record the hash of the Newick, the R script and the arguments you used. The adapter receipt is written before the figure exists, so it does not cover the figure.

These are strain-level readouts. They do not point to a biosynthetic locus. Several series side by side do not mean the materials or assays are interchangeable. A 16S tree is placement context, not a species identification.

## If something goes wrong

- **Step 1 left a partial folder.** Keep it for diagnosis. Fix the cause and use a new folder. There is no resume. Use one writer at a time.
- **Step 2 failed after writing some files.** The PDF, PNG and tip-order file are written one after another. Move the partial set aside and use an unused prefix.
- **Files moved.** The receipt records the config hash and relative paths, but not the resolved `input_root`. Keep the config path, its hash and the root with the receipt so a later reader can find the sources.

What each tool checks:

- The adapter checks hashes, the track roster and finite values. It never sees the Newick.
- The R script checks tips, roles, columns and values. It does not check branch lengths, rooting or support method.
- A hand-edited `tracks.tsv` skips the adapter's checks. Use the adapter's output.

Both `tools/render_tree_*` wrappers call `tools/tree_track_render.R`.
