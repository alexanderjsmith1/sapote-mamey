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

The annotator retains the parsed row count, but that is not a byte-faithful copy of every original field. Existing `mapping_profile`, `source_well`, `destination_well`, `quadrant`, `final_concentration_ug_ml` and `mapping_state` columns are replaced by the selected profile's values. Keep the raw well column under a distinct name such as `Well_384` and preserve the original input separately. Formula-leading text may receive a leading apostrophe from the spreadsheet-safe writer; plain signed numbers are retained.

Input/output suffixes select the delimiter independently: `.tsv` or `.tab` means tabs, anything else means commas. Destination wells normalize case, surrounding/internal row-column whitespace and zero-padded column numbers within A–P / 1–24. A destination outside that grammar receives `mapping_state=UNMAPPED` with blank source/quadrant/concentration, and the command prints `PASS_WITH_HOLDS` while still returning zero. Header-only input with the selected well column can print `PASS` with no observations. Compare the source/output row roster and mapping states before adoption; zero exit is not a complete observed plate or source/measurement admission. Require unique nonblank headers and complete-width input rows: the current parser does not enforce those properties, and extra cells can be ignored on writing. The named profile must match the physical plate-transfer method.
It supplies geometry and dose fields only, so sample identity, controls, exclusions, timepoints,
targets, material lineage, and inhibition calculations still require explicit admission into the
observation table.

### Plate-map output and recovery

`--out` is a replacement destination, not a fresh-only publication contract. The mapper creates its parent and writes a unique temporary sibling, flushes it, then replaces the selected file. It can overwrite an existing mapped table or even the input if both paths name the same file. Use a fresh explicit output outside source evidence and the code bundle; this mapper has no source/output separation or bundle-root guard. Ordinary caught write failures remove the temporary file, but a process crash may leave a temporary sibling. Preserve prior outputs and inspect actual files/diagnostics before retrying. No source/output hash receipt is emitted; bind the input path/hash, selected profile, well column, output hash, row count and UNMAPPED count separately.

The separate `emit` command creates the profile's complete 384 source/destination-pair geometry table. `validate` checks that complete table's unique pair roster and exact profile/quadrant/concentration strings. It is not a validator for a partial assay export, repeated well measurements, sample identity or the canonical observation schema; duplicate pairs and incomplete coverage are refused. Its checks do not use `mapping_state`, so a geometry PASS cannot clear an observation hold.

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

## Aggregation, display and receipt qualifications

The summary mean weights each included **observation row** equally within its exact key. Experiment and replicate counts are descriptive; this is not an equal-experiment mean or independent biological-replicate analysis. Rows have unique observation IDs, but this does not independently verify distinct physical wells or replicate independence. The key also preserves parent/lineage state, target state, dose state, stock concentration and delivered amount. Ambiguous targets can remain included under valid control/measurement rules and are visually labeled; inclusion is not organism-resolution acceptance (`mamey/bioassay_figure_factory.py:408–525`).

The observation table records portable source locators and the factory binds the whole admitted-input file hash. It does not hash or read every raw file named by an observation's source locator. Retain the raw-source mapping and hashes separately; an input table's hash does not validate its source interpretation or experimental authority. Raw-column inventory and adjudication/ruling inputs, when supplied, have their own admission and hash contracts; their presence is not implied by a figure receipt.

The R view uses strain/material/type as row labels and target/timepoint/final-dose as columns. Those display keys omit some distinctions retained in summary keys (parent/lineage, stock/delivered dose and most target/dose states); distinct rows can consequently occupy the same visual cell. Inspect the summary for duplicate display coordinates and hold an ambiguous overplot before adoption. The sidecar remains authoritative for the retained groups. SVG/PNG canvas width is 7.2 inches for DOUBLE_COLUMN and 4.25 inches otherwise; height is `max(3.4,1.7 +0.34 × displayed material rows)` inches, PNG 300 dpi. There is no automatic readable-column density check or visual-QA receipt (`tools/sapote_bioassay_figure.R:41–73`).

`PASS_DATA_READY_R_NOT_REQUESTED` means data production without rendering. `PASS_FIGURE_FACTORY_RENDERED` means R returned 0 and both files exist; it does not test nonempty graphics, visual legibility or scientific validity. Output hashes bind emitted artifacts; the receipt excludes itself and lacks config/source-code/R-script/runtime-version hashes. Preserve those externally. The producer requires a new output directory, stages artifacts and renames it on success; exceptions remove its temporary stage. Stable inputs and a sole reviewed output writer remain assumptions, and leftover temporary stages after a process crash are not completed output (`729–812`).

Tree-track `OBSERVED` and `NOT_MEASURED` are material/target/time/dose-selected states, not locus activity or strain-wide absence. Preserve track hash, selection details and exact tree-tip crosswalk independently; plotting cannot clear upstream identity, control or acquisition holds.
