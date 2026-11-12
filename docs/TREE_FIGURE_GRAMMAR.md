# Tree figure display and provenance

Label every tip from explicit panel metadata that you can trace to a source. Display style does not
establish scientific acceptance. Terms are in the [glossary](GLOSSARY.md).

## Pick a route

| You have | Tool | Section |
|---|---|---|
| A placement tree from EPA-ng (query tips grafted onto a reference backbone) | `tools/build_placement_ggtree_inputs.py`, then `tools/ggtree_placement.R` | [Placement tree](#placement-tree) |
| A GToTree panel with a `figure_metadata.tsv` | `tools/bind_panel_metadata.py` | [Bind panel metadata](#bind-panel-metadata) |
| A tree and a metadata table, to draw a rectangular tree with tracks | `tools/ggtree_rect_heatmap.R` | [Rectangular tree](#rectangular-tree) |

Before you start:

- Write every output to a new, empty folder. These tools can overwrite files, and an error can leave partial files.
- Run from the bundle root.
- Do not invent a value. A missing metadata record is missing evidence, not biological absence.

## Labels

A query label can show the strain, the deposited host or collection location, and the accession.
A reference label shows the organism, the deposited isolation source and country, and the accession.
Keep the collection origin apart from any later handling location.

Reference tips use the form `<organism> <strain> [Type] [<accession>]`, as in
[Figure house rules](FIGURE_HOUSE_RULES.md). The accession goes in brackets. Put deposited source text in
parentheses or in the caption, and label it so it is not mistaken for an accession. Pull accessions out
before you read organism text. A culture collection code is not an accession. One accession repeated on a tip
is redundant. Two different accessions on one tip need reconciling.

## Placement tree

### Name the query tips

Give the helper an explicit list: `--query-tips FILE`, one exact tip name per line, as the names appear
in the graft tree. `tools/placement_display.py` takes the same option, checks it against the admitted
tree (refusing with the same codes before anything is written), uses it for its own query checks, and
passes it to the helper. The helper then treats exactly those tips as queries. It refuses a blank list, a
name listed twice (`QUERY_TIPS_DUPLICATE`) and a name that is not a tip of the tree
(`QUERY_TIPS_NOT_IN_TREE`), and it never renames a tip. Keep the list with the run's inputs; its
SHA-256 is recorded with the other metadata sources.

Without `--query-tips`, the helper falls back to a name rule: a tip is a query only when its name
starts with `AS` or `SID`, then an optional hyphen or underscore, then a digit
(`tools/build_placement_ggtree_inputs.py`, `_is_query`). Any other tip is treated as a reference. Do not
rename tips to fit that rule; a new name breaks the link to the original tree and roster. Use the list
instead. Check the `kind` column of `<prefix>_ggtree_annotation.tsv` for the queries it found. If it
found none, it skips the nearest-reference pruning.

### Prepare the inputs

Install Biopython (it comes with `pip install '.[figures]'`). Create the parent folder of the output prefix first.

```bash
python tools/build_placement_ggtree_inputs.py \
  --graft "/absolute/source/placement.newick" \
  --host-table "/absolute/source/strain_metadata.tsv" \
  --query-tips "/absolute/source/query_tips.txt" \
  --group "panel name" --neighbors 3 \
  --family-level --outgroup-substr "outgroup substring" \
  --out-prefix "/absolute/new_view/panel" \
  --rect-meta-out "/absolute/new_view/panel_rect_metadata.tsv"
```

The host table is a tab-separated file with a header row. Each row is one strain. The helper reads:

| Column (first match wins) | Holds |
|---|---|
| `Strain Number`, `tip_label` or `strain` | the strain name, matching the tip in the tree |
| `Host`, `host_common`, `host` or `host_raw` | the host label |
| `Location`, `location` or `location_raw` | the place |
| `Genbank Accession` or `genbank_accession` | the accession |

```
strain	host_common	location	genbank_accession
AS-NNNN	example host	example place	XX000000
```

This example is for a multi-genus panel with an outgroup you chose yourself. Run
`python tools/build_placement_ggtree_inputs.py --help` for all options.

What the options do:

- It keeps each recognized query, the outgroup tips and, by default, the three nearest references per query by patristic distance (distance along the tree).
- `--outgroup-substr` matches tip names case-insensitively. It does not check that the match is the right tip, so list every matched tip.
- With references from more than one genus, the helper refuses unless you pass `--family-level`.
- `--required-reference-table` names a reference species that is counted first in each query's quota.
- `--keep-all-refs` keeps every reference allowed by `--require-reference-metadata`. A `--neighbors` of zero or less acts as a minimum of one.
- `--ref-source-db` is an SQLite file of deposited isolation source and country. A `host` column is optional and is always labeled as host.

Success is exit code 0 and these files at your prefix:

- `<prefix>_pruned.nwk`
- `<prefix>_ggtree_annotation.tsv`
- `<prefix>_reference_selection.tsv`
- `<prefix>_metadata_receipt.json`
- the rectangular metadata TSV you named

Open `<prefix>_reference_selection.tsv` and confirm each query kept up to three references. Do not trust the
file name to show what panel you got. The receipt hashes the inputs and the other outputs and records names as
base names, so keep a full-path hash list of your own if base names could collide. `validation=NEIGHBORHOOD`
in the annotation is a label the tool assigns. It is not a scientific validation.

If `<prefix>_publication_recovery.json`, a staging sibling or `.prepublish.bak` files remain after a failed run,
the next run refuses. Keep them and read them. Do not delete them just to rerun.

`GG_REF_SOURCE_CHARS` (8 to 240, default 40) limits the displayed deposited-source text. `GG_REF_LABEL_CHARS`
is range-checked but has no effect. Neither setting checks that labels are unique or that the canvas is wide enough.

### Reference databases

A 16S database built with the bundle can hold `LOCAL:` keys for your own isolates. They are not deposited
accessions, and the helper's accession check can refuse them. The helper skips only the older `AS_LOCAL_...`
form. Pass `--ref-source-db` an SQLite file that holds only deposited records, and keep the original database
unchanged.

The helper joins metadata by accession base, so it cannot show that the metadata belongs to the exact
version shown. For an exact-version join, use the
[source-label adapter](TREE_DISPLAY_RECEIPTS.md#1-add-deposited-source-labels-optional).

### Draw it

```bash
GG_TITLE="..." GG_SUB="..." GG_METHODS="..." \
Rscript tools/ggtree_placement.R "/absolute/new_view/panel_pruned.nwk" \
  "/absolute/new_view/panel_ggtree_annotation.tsv" "/absolute/new_render/placement" noloc
```

This writes `placement.pdf` and `placement.png`. It needs the R packages `ape`, `ggtree`, `ggplot2` and `treeio`.
The fourth argument picks the label style: `id`, `host`, `noloc`, `withloc`, `full` or the name of an annotation
column. An unavailable style gives a warning and falls back to `label_withloc`.

Set all three `GG_*` variables for every figure. Without them the title reads as a bacterial 16S EPA-ng
placement on a RAxML-NG GTR+G backbone with 10 bootstraps, and the title names "AS queries", whatever
your analysis was. `GG_METHODS` is optional in code. If you leave it unset, the methods caption is dropped.
No setting supplies a verified method for you.

The placement renderer joins the annotation directly. It does not check that the tip set matches or that tips
are unique. Compare counts and joins before you accept the image.

## Bind panel metadata

`tools/bind_panel_metadata.py` fills the `figure_metadata.tsv` of an existing GToTree panel. It does not
build, prune or draw a tree and does not fetch NCBI records. Its table is a different schema from the
placement and rectangular tables.

```bash
python tools/bind_panel_metadata.py \
  --panel-dir "/absolute/source/reviewed_panel" \
  --out-dir "/absolute/new_view/bound_panel" \
  --assembly-records "/absolute/source/assembly_records.tsv"
```

Inputs:

- `--assembly-records`: a TSV with columns `accession`, `organism`, `strain` and `fromtype` (an NCBI Assembly export). Accessions join by exact spelling after trimming spaces. Versions are not folded together. If an accession repeats, the last row wins. `[Type]` appears only when `fromtype` is `assembly from type material`.
- `--assay-table`: a TSV with columns `strain`, `anti_candida` and `anti_mrsa`. Only these two assay columns are read. It applies to `role=QUERY` rows only. Cells keep four states: `+`, `-` (or the Unicode minus), `n.t.` and blank. Conflicting repeated states for a strain are refused.
- `--bc3`: a table of verified isolation source and geography. It needs the columns `identifier`, `panels`, `isolation_source_verified` (or `_existing`), `geography_*` and `location_*`. A panel is selected when the source folder name appears in the row's `panels` field. A panel tip that is missing from the table, or whose source text matches no rule, is refused.
- `--corrections`: used only with `--bc3`. Columns are `panel`, `identifier`, `field`, `proposed_value` and `unresolved_issue`. Rows for the exact panel or any `LOCAL-` panel apply. The last value wins. A value that starts with WITHDRAW, UNRESOLVABLE, DO NOT or NO TRACEABLE clears the field.
- `--omitted-tips`: a receipt from `tools/omitted_tips_receipt.py` with the columns `tip`, `name` and `reason`. It is copied beside the output as `omitted_tips.tsv`. The binder refuses a receipted tip that is still in the panel.

Query strain recognition prefers an exact `AS-<digits>` identifier, then an `AS-<digits>` tip prefix, then the
identifier itself.

The binder applies the options in this order: corrections, then assays, then Assembly labels. A cell cleared by a
correction can be refilled from `--assay-table`, and a held label can be replaced by an Assembly label. The tool
does not apply the corrections again at the end, so check the final cells against your correction table.

A missing assay row keeps the earlier cells and reports `NO_ASSAY_ROW`. A missing Assembly record keeps the earlier
labels and reports `NO_ASSEMBLY_RECORD`. Neither is a failure or a measured negative.

Success is exit code 0 and a status summary on the screen. The tool writes no receipt and no hashes, so save the
summary, the exit status and a hash list of your inputs and outputs. The binder writes into the output folder
directly, with no rollback. An input table named `figure_metadata.tsv` would collide with the output name. If a
run fails, it can leave copied files or a partial table. Keep them, fix the input, and rerun into a new folder.
The binder does not check the tree tip set, label uniqueness or a finished render.

## Rectangular tree

```bash
Rscript tools/ggtree_rect_heatmap.R "/absolute/new_view/panel_pruned.nwk" \
  "/absolute/new_view/panel_rect_metadata.tsv" "/absolute/new_render/rectangular" \
  "exact_query_tip1,exact_query_tip2"
```

The metadata needs unique `tip` and `label` columns, and its tips must match the tree exactly. The R script also
needs `aplot` and `patchwork`, plus the bundle's Python tree and annotation checks, found through `SAPOTE_PYTHON`
or `python3` on your path. It writes `.annotation_audit.tsv`, `.methods.txt`, `.pdf`, `.png` and `.session.txt`.

The optional fourth argument lists the tips to highlight. The match uppercases the names and removes hyphens,
underscores and spaces, so two different IDs can share one highlight key. List the exact tips and check which
ones were highlighted. Without that argument, only a `role=query` column in the metadata marks queries, and the
placement helper's rectangular table has no such column. Pass the roster yourself.

For a hash-bound display receipt, read [Tree display receipts](TREE_DISPLAY_RECEIPTS.md). A failed guard or
binding is not visual acceptance, and images can exist even when the final binding fails. To copy a finished
rectangular display for a collaborator, follow
[the export contract](TREE_DISPLAY_RECEIPTS.md#optional-editable-copy-of-a-finished-figure). Editing the copy or
refreshing its hashes does not make a new valid display.

## Check the image

Open the PDF or PNG. Look for clipping, label collisions and unreadable text after any change to canvas size or label
length. Name the outgroup, the analysis source, the display changes and any missing metadata in the caption.

The analysis tree and any pruned or collapsed display tree have separate roles. Keep the analysis tree and a
record of every transformation. You can leave a visible "missing" marker off a label only while the hold and its
source stay on record.

## Outgroups and claims

Pick the outgroup yourself and record why. Do not accept a genus as an outgroup just because it is rare in the panel.
Missing or conflicting outgroup information is a hold. `tools/phylo_outgroup_gate.py <alignment> [<alignment> ...]`
reports outgroup and ingroup pairwise identity with missing data stated. The registry shipped with the bundle is a
snapshot for reference. Use a registry you govern for project decisions.

A passing mechanical check does not accept a rooting, a species call, a compound identity or an activity. Report
the aligned length next to any identity value. Keep sequence placement apart from scientific interpretation.

## Fill in missing reference metadata

`tools/resolve_reference_metadata.py` looks up metadata for chosen accessions and linked BioSamples. It uses the
network, so run it only where you are allowed to. Read each output row's `verification_status`,
`strain_match_basis` and `unresolved_issue`. Rows can show a refused identity or missing data and still exit 0, and
`--continue-on-error` exits 0 even when some rows are `ERROR`. `--out` overwrites its file, so use a new path. Leave
unresolved rows as they are. Do not fill the values by hand.
