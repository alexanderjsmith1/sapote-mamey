# Synthetic tree-track example

Every value, name and tree distance here is synthetic. Nothing in this folder is an experimental result, a taxonomic assignment or an activity claim. The 48-hour and 72-hour selections are separate. Do not pool them.

## Files

| File | Use |
|---|---|
| `tree.newick` | The tree to draw against. |
| `metadata.tsv` | Maps each tip to a strain, label and role. |
| `single.json` | Adapter config with one track (48 h). |
| `grouped.json` | Adapter config with several tracks. |
| `factory_48.json`, `factory_72.json` | Figure Factory configs. They use `observations.csv` and fixed synthetic selections, with `render_with_r: false`. |
| `factory_48/`, `factory_72/` | Receipts the adapter configs point to. |
| `observations.csv` | Synthetic assay values for the factory configs. |

## Run it

Nothing is written inside `examples/`. Choose an output folder that does not exist yet, outside the bundle:

```bash
python3 tools/build_tree_tracks.py --config examples/tree_tracks/grouped.json --out /path/to/new-track-output
```

It prints nothing and exits 0 on success. The folder then holds `tracks.tsv`, `series.tsv` and `track_adapter_receipt.json`. A refusal prints `TREE_TRACK_REFUSED` and exits 2. Draw the figure with the R command in [the tree-track guide](../../docs/TREE_ASSAY_TRACK_RENDERING.md).

To change a config, copy only that JSON file to a work folder. Set its `input_root` to the original `examples/tree_tracks/` folder so it still finds the supplied receipts. To rebuild the factory outputs, read the [Figure Factory contract](../../docs/BIOASSAY_FIGURE_FACTORY.md) first. Its path rules differ from the adapter's.

## What to expect

The adapter does not read `tree.newick`. The R renderer does, and it needs the tree tips to match `metadata.tsv` exactly. In `tracks.tsv` a query tip that was not measured and every reference or outgroup tip are both blank. The table does not tell them apart; the `role` column does. The renderer keeps them apart: a query with no value is marked x (`NOT_MEASURED`), a reference or outgroup tip has no mark (`NOT_APPLICABLE`), a recorded zero is a dot, and positive and negative values are bars. `OUT_PREFIX.cell_states.tsv` lists the state of every cell. A data-ready Figure Factory receipt means the data are prepared, not that a figure was drawn. A drawn figure is a display check, not assay or phylogeny approval.
