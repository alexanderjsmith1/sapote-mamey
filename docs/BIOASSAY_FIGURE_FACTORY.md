# Make a bioassay summary figure

Turn recorded assay observations into a summary table and an R-rendered heatmap.
This is the front door for bioassay figures. You need the measurements, the
plate/sample mapping, the controls and the source files.

## Overview

The work has three steps.

1. **Map the plate** (optional). If your raw export has only 384-well positions, add the
   source well and dose to each row. Skip this step when your per-well tables already
   carry dose and source well.
2. **Convert per-well tables to observations.** A profile file you write lists your
   tables and columns. The tool writes one observation table.
3. **Build the figure.** `figure-factory` reads the observation table and writes the
   summary, the caption data and the heatmap.

Two terms. A row is **admitted** when you declared it usable in the profile and its
control state is acceptable. A row is **held** when it is kept in the table with a
reason and left out of the summary. The **parent** is the material a fraction came
from, such as the crude extract.

Start with the [observation template](../examples/bioassay_observations_template.tsv).
Each row records its plate/well, material and parent, target, dose, time point,
replicate, control state, measurement and source. Only included rows enter the summary.

## Map the plate

List the available geometry profiles:

```bash
python tools/bioassay_plate_map.py list-profiles
```

Use a profile only when it matches the physical transfer. For the listed
96-to-384 quadrant layout, with raw wells in the default `Well_384` column:

```bash
python tools/bioassay_plate_map.py annotate \
  --profile 96_TO_384_QUADRANT_120_60_30_15 \
  --input inputs/EXAMPLE-plate.csv --out reviews/EXAMPLE-plate-mapped.tsv
```

Use a fresh output path: the mapper can overwrite an existing file, including
its input. It replaces its mapping columns, so preserve the raw export.
On success the tool prints one line and exits 0. A run with unmapped wells prints
`PLATE_MAP_PASS_WITH_HOLDS: rows with mapping_state=UNMAPPED: 1; output=...`.
That status also exits 0, and an empty table can pass. So compare the output row count
with the input row count and look at every row whose `mapping_state` is `UNMAPPED`.

The tool keeps your columns and appends `mapping_profile`, `source_well`,
`destination_well`, `quadrant`, `final_concentration_ug_ml` and `mapping_state`. For
example, `A2` maps to source well `A1`, quadrant `TR`, 60. The mapping supplies
geometry and dose only. Sample identities, controls and measurements still come from
the experiment records. To use the mapped file in the next step, name it as a table
in your profile.

The separate `emit` and `validate` commands handle a complete geometry table.
They do not validate a partial assay export or its measurements.

## Convert existing per-well measurements

The profile is a JSON file. Fill a copy of the [profile example](../examples/bioassay_admitted_profile_example.json)
with your table paths (relative to the profile file), columns, material types, target states, dose states and
calibration/control declarations. Then choose new output paths. Both `observations` and
`best-table` write the output table and `<out>.receipt.json`, and both must be new paths. If
either exists, the two collide, or either names an input (the profile, a per-well table the
profile names, or the observation table and its receipt), the command prints `OUTPUT_EXISTS_HOLD`,
exits 2 and writes nothing. An existing receipt is refused, not replaced:

```bash
python tools/bioassay_admitted_observations.py observations \
  --profile inputs/EXAMPLE-assay-profile.json --out reviews/EXAMPLE-observations.tsv
```

The command preserves recorded inhibition values, including negative values,
and writes a receipt with source/profile hashes and included/held counts.
Unmapped materials stay held; undeclared calibrations get `UNRECORDED` and stay
held. Check those counts
before plotting; a missing control cannot be supplied by an assumed expected value.

If you need the existing cross-platform best-reading summary:

```bash
python tools/bioassay_admitted_observations.py best-table \
  --observations reviews/EXAMPLE-observations.tsv --out reviews/EXAMPLE-best.tsv
```

Its defaults compare the best 96-well reading at any recorded dose with the best
384-well reading at final concentration 120, then apply a zero floor. Choose
`--dose-384` for a different selected concentration or `--no-floor` to keep
negative readings. Missing combinations have no row; they are not measured zeros.

## Build the figure

Run from the program folder. Save this as `inputs/EXAMPLE-figure.json`. Replace the SHA-256 text with
`output_sha256` from `reviews/EXAMPLE-observations.tsv.receipt.json`:

```json
{
  "schema_version": "sapote.bioassay-figure-factory.v1",
  "figure_kind": "bioassay_observation_summary_v1",
  "external_data_root": "reviews",
  "observations": {
    "logical_locator": "EXAMPLE-observations.tsv",
    "sha256": "PASTE_OUTPUT_SHA256_FROM_RECEIPT"
  },
  "output_dir": "../reviews/EXAMPLE-bioassay",
  "render_with_r": true,
  "rscript": "Rscript",
  "profile": "DOUBLE_COLUMN",
  "title": "EXAMPLE bioassay observations"
}
```

Here the data root `reviews` is relative to the folder you run from. The output
`../reviews/EXAMPLE-bioassay` is relative to the config file, so it lands in the same
`reviews` folder. Set `render_with_r` to false for data only.
`DOUBLE_COLUMN` selects 7.2 inches; the other profile uses 4.25 inches.

```bash
python mamey_run.py figure-factory --config inputs/EXAMPLE-figure.json
```

The `output_dir` must not exist yet; the run stops with `FileExistsError` if it does.
It writes `bioassay_observations_admitted.tsv`, `bioassay_summary.tsv`,
`bioassay_caption_methods.json` and `bioassay_figure_factory_receipt.json`, plus
`bioassay_summary.png` and `bioassay_summary.svg` when R renders.

The factory emits observations, grouped summaries, caption/methods metadata and
a receipt. Rendering needs R (`Rscript`; see [prerequisites](PREREQUISITES.md)). It uses
`tools/sapote_bioassay_figure.R` and produces 300-DPI PNG plus SVG. `PASS_DATA_READY_R_NOT_REQUESTED` means data only;
`PASS_FIGURE_FACTORY_RENDERED` means R returned zero and both files exist.
Inspect the actual images, labels and density before using them.

Means weight observation rows equally, including rows from different experiments.
Read observation and experiment counts with the mean and raw range.
The summary keeps more grouping fields than the plot's row/column labels; check
for distinct summary rows sharing a displayed cell and hold an ambiguous overplot.

Keep the raw-source mapping/hashes separately: the factory binds the admitted
table, not every raw file named in its rows. Save the config, renderer/theme
versions and output hashes with the receipt. Retry a failed build in a fresh
destination after inspecting any remaining temporary files.

<a id="tree-and-mode-b-boundary"></a>
## Select values for a tree

To draw assay values beside a tree, add a `tree_track_selection` block to the
figure config. The factory writes one value per strain to `bioassay_tree_track.tsv`.
It refuses with `BIOASSAY_TREE_SELECTION_HOLD: missing ...` unless all of these keys are set:

| Key | Meaning |
|---|---|
| `selection_id` | A name for this selection |
| `target` | The target organism or label, as recorded |
| `target_state` | `VERIFIED`, `AS_RECORDED` or `AMBIGUOUS` |
| `timepoint_hours` | One time point, a positive number |
| `final_concentration_ug_ml` | One final dose, a positive number |
| `material_type` | `CRUDE_EXTRACT`, `FLASH_FRACTION`, `HPLC_FRACTION`, `PURIFIED_COMPOUND` or `OTHER` |
| `strain_roster` | The strains to draw, each listed once |
| `material_ids_by_strain` | The material ID chosen for each roster strain |

`aggregation` is optional. The default, `mean_inhibition_pct`, needs exactly one
material per strain. `fraction_set_max` takes a list of materials per strain, needs
`active_threshold_pct` (0 to 100), and refuses a partly measured set.

A complete working block is in
[`examples/tree_tracks/factory_48.json`](../examples/tree_tracks/factory_48.json).
Copy its `tree_track_selection` block into your figure config and replace the values.

The track keeps a recorded zero as `OBSERVED` and a missing measurement as
`NOT_MEASURED`. Bind it to the tree through an exact tip-to-strain crosswalk;
continue with [tree assay tracks](TREE_ASSAY_TRACK_RENDERING.md).
Locus-level activity needs a separate experimental link.

Raw-layout mappings, in-vivo observations and experiment-level selection need
their own supported schemas or policies. Keep ambiguous target labels visible.
The `bioassay_to_activity_channel.py --recon` adapter is a narrower route for one
assay layout; see [its workflow](BIOASSAY_ACTIVITY_CHANNEL_WORKFLOW.md).
