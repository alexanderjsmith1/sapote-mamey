# Bioassay Figure Factory

Bioassay figures begin with a canonical long-form observation table. Raw plate exports are not
uniform enough to interpret by filename or column position: a separate mapping step must state
what each well, plate, material, target, time point, replicate, and control represents.

## Plan before mapping

The same `figure-factory` command accepts a `bioassay_project_plan_v1` config. It inventories
hash-bound datasets as `RAW_OD`, `PRECOMPUTED_PERCENT_INHIBITION`, `MIC_TABLE`, `IN_VIVO`, or
`OTHER`; records plate format, material scope, targets, time points, dose coverage, replication,
controls, and availability of material amounts; then emits Markdown and JSON for user review.

The plan proposes relevant previews such as control/normalization QC, fraction-series activity,
maximum activity within a named fraction set, activity breadth and material yield, dose response,
MIC endpoints, target coverage, and selected tree overlays. It also asks which inputs were computed
by the user, which rows/plates should be omitted, how ambiguous targets should resolve, what the
caption should say, and whether descriptive summaries or a separately specified statistical model
are appropriate. This supports mixed projects without treating fraction-discovery screens as MIC
experiments.

The current Figure Factory kind is `bioassay_observation_summary_v1`, with config schema
`sapote.bioassay-figure-factory.v1`. It accepts a hash-bound CSV or TSV whose columns exactly match
[`examples/bioassay_observations_template.tsv`](../examples/bioassay_observations_template.tsv).

## Map a 96-well source plate into a 384-well dose layout

For a 384-well assay created by printing each 96-well source position into a 2-by-2 block at
120, 60, 30, and 15 micrograms per milliliter, use the explicit geometry profile before building
the observation table:

```bash
python tools/bioassay_plate_map.py list-profiles
python tools/bioassay_plate_map.py annotate \
  --profile 96_TO_384_QUADRANT_120_60_30_15 \
  --input plate_reader_export.csv --well-column Well_384 \
  --out plate_reader_export_mapped.tsv
```

The mapper preserves every input row. A destination well outside the selected profile receives
`mapping_state=UNMAPPED`, and the command reports `PASS_WITH_HOLDS`; it never assigns that row a
source well or concentration. The named profile must match the physical plate-transfer method.
It supplies geometry and dose fields only, so sample identity, controls, exclusions, timepoints,
targets, material lineage, and inhibition calculations still require explicit admission into the
observation table.

## What the observation table preserves

- 96-well, 384-well, or explicitly declared other plate layouts;
- experiment, plate, well, and replicate identity;
- crude extract, flash fraction, HPLC fraction, purified compound, or other material type;
- parent material and lineage state, so a serial “fraction plate” does not erase what the material is;
- available material amount, stock concentration, delivered amount, final assay concentration, and
  dose-record state; the 15/30/60/120 µg/mL series therefore remains distinct from an 80 or
  100 µg/mL single-dose assay;
- raw target label, target-resolution state, and a canonical target only when verified;
- recorded time point and percent inhibition without clipping;
- positive-control state, including missing controls, unresolved locations, and expected-OD normalization holds;
- explicit include, exclude, or hold disposition with a required reason for held/excluded rows;
- a portable source locator and exact input hash.

An included observation needs a valid or inapplicable control, numeric time point, and numeric
inhibition measurement. A missing positive control cannot be included by silently normalizing to an
expected value. An ambiguous *Candida* label remains ambiguous. Held and excluded observations stay
in the admitted output and its counts, but are not averaged into the figure summary.

## Build data or render with R

```json
{
  "schema_version": "sapote.bioassay-figure-factory.v1",
  "figure_kind": "bioassay_observation_summary_v1",
  "external_data_root": "/path/to/admitted/project-data",
  "observations": {
    "logical_locator": "bioassay/observations.tsv",
    "sha256": "<exact lowercase SHA-256>"
  },
  "output_dir": "bioassay_figure",
  "render_with_r": true,
  "rscript": "Rscript",
  "profile": "DOUBLE_COLUMN",
  "title": "Bioassay observations"
}
```

Run `python mamey_run.py figure-factory --config config.json`. With `render_with_r: false`, the
factory emits the admitted observations, grouped summary, caption/methods metadata, and receipt.
With `render_with_r: true`, it also runs `tools/sapote_bioassay_figure.R` and emits SVG and PNG.
The plotted canvas uses a short descriptive caption; detailed admission and interpretation states
travel in the sidecars and receipt.

The current plot groups only exact strain/material/target/time-point/dose combinations. It shows the
arithmetic mean, observation count, experiment count, and raw minimum/maximum in the sidecar. It
does not average unlike materials or doses.

## Tree and Mode B boundary

The factory marks tree integration as `REQUIRES_EXPLICIT_MATERIAL_TARGET_TIMEPOINT_SELECTION`.
That is intentional: a strain can have crude extract, flash-fraction, and HPLC-fraction results at
several time points, and taking an unscoped maximum would bias the tree overlay. A later selection receipt
must name the material scope, target, time point, aggregation, and included experiments before the
result becomes a strain-level tree track. A strain may join through a verified tree-tip crosswalk
even when only 16S, rather than a genome, is available.

Add `tree_track_selection` to the Figure Factory config to emit `bioassay_tree_track.tsv`:

```json
{
  "selection_id": "candida_auris_48h_flash",
  "target": "Candida auris",
  "target_state": "VERIFIED",
  "timepoint_hours": 48,
  "final_concentration_ug_ml": 120,
  "material_type": "FLASH_FRACTION",
  "aggregation": "mean_inhibition_pct",
  "strain_roster": ["strain-1", "strain-2"],
  "material_ids_by_strain": {
    "strain-1": "flash-fraction-7",
    "strain-2": "flash-fraction-12"
  }
}
```

For `mean_inhibition_pct`, every roster strain must have one explicitly selected material ID. A
missing measurement becomes
`NOT_MEASURED`, while a recorded zero remains `OBSERVED` with value `0`. The emitted columns match
the `BIOASSAY` annotation channel accepted by `tools/tree_bgc_overlay.py`; a separate exact tip
crosswalk still binds strain IDs to a GToTree or other tree. This track can also describe a 16S-only
strain once its EPA-ng placement is represented by a reviewed tip crosswalk.

For a chromatography-series overview, set `aggregation` to `fraction_set_max`, provide a list of
material IDs per strain, and declare `active_threshold_pct`. The factory selects the highest exact-
dose material mean for the tree value and writes `bioassay_tree_selection_details.tsv` with the
selected material, number of requested/measured/active fractions, threshold, and summed recorded
material amount. This makes “maximum activity” reviewable while retaining the breadth and yield of
the fraction series. A partially observed named set is refused because its apparent maximum does
not represent the requested set; a strain with no observations remains `NOT_MEASURED`. The factory
never compares or pools different final assay concentrations.

Mode B may cite a selected strain- or sample-level assay summary as context. It may not attribute
that result to an individual biosynthetic locus without a separately admitted experimental link.

## Current residual

The bundle still needs mapping profiles for the project's distinct raw 96- and 384-well layouts,
a generalized multi-target ggtree strip, an in-vivo observation schema, raw-plate mapping profiles,
and a policy for choosing among repeated experiments before selection. The older
`bioassay_to_activity_channel.py --recon`
path remains a narrow adapter for its original four-dose 48-hour fraction reconstruction; its
hard-coded assumptions must not be projected onto other assays.

Chemical structures are a separate reference-context layer. A structure for a known class member
or KnownClusterBlast comparator can be displayed when its source database record, structure
identifier, license, and relationship to the current evidence are recorded. Such a display does
not identify the assayed material or the product of a biosynthetic locus.
