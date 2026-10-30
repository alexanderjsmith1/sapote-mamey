# Make a bioassay summary figure

Turn recorded assay observations into a summary table and an R-rendered heatmap.
You need the measurements, plate/sample mapping, controls and source hashes.


Start with the [observation template](../examples/bioassay_observations_template.tsv).
Each row records its plate/well, material and parent, target, dose, time point,
replicate, control state, measurement and source. Keep held/excluded rows with
their reasons; only included rows enter the summary.

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
Check unique nonblank headers, complete rows, row counts and every `UNMAPPED`
state. `PASS_WITH_HOLDS` returns zero, and an empty table can pass.
The mapping supplies geometry and dose fields; sample identities, controls and
measurements still need to come from the experiment records.

The separate `emit` and `validate` commands handle a complete geometry table.
They do not validate a partial assay export or its measurements.

## Convert existing per-well measurements

Fill a copy of the [profile example](../examples/bioassay_admitted_profile_example.json)
with your table paths, columns, material types, target states, dose states and
calibration/control declarations. Then use fresh outputs:

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

Save this as `inputs/EXAMPLE-figure.json`. Replace the SHA-256 text with
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

The data root is relative to the command's working directory; the output is
relative to the config file. Set `render_with_r` to false for data only.
`DOUBLE_COLUMN` selects 7.2 inches; the other profile uses 4.25 inches.

```bash
python mamey_run.py figure-factory --config inputs/EXAMPLE-figure.json
```

The factory emits observations, grouped summaries, caption/methods metadata and
a receipt. Rendering uses `tools/sapote_bioassay_figure.R` and produces 300-DPI PNG
plus SVG. `PASS_DATA_READY_R_NOT_REQUESTED` means data only;
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

## Select values for a tree

Provide `tree_track_selection` with one target and target state, time point,
final dose, material type, strain roster and selected material IDs.
`mean_inhibition_pct` needs one material per strain. The optional
`fraction_set_max` view needs a named material set and `active_threshold_pct`;
it selects among pooled material means and refuses a partly measured set.

The track keeps recorded zero as `OBSERVED` and missing measurement as
`NOT_MEASURED`. Bind it to the tree through an exact tip-to-strain crosswalk;
continue with [tree assay tracks](TREE_ASSAY_TRACK_RENDERING.md).
Locus-level activity needs a separate experimental link.

Raw-layout mappings, in-vivo observations and experiment-level selection need
their own supported schemas or policies. Keep ambiguous target labels visible.
The older `bioassay_to_activity_channel.py --recon` adapter is limited to its
original assay layout and cannot supply a general mapping.

<a id="plan-before-mapping"></a>
<a id="map-a-96-well-source-plate-into-a-384-well-dose-layout"></a>
<a id="plate-map-output-and-recovery"></a>
<a id="bring-admitted-per-well-tables-in"></a>
<a id="what-the-observation-table-preserves"></a>
<a id="build-data-or-render-with-r"></a>
<a id="tree-and-mode-b-boundary"></a>
<a id="current-residual"></a>
<a id="aggregation-display-and-receipt-qualifications"></a>
