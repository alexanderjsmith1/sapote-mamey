# Draw a tree with BGC and assay strips

`tools/tree_bgc_overlay.py` draws a finished phylogenetic tree with one colored strip of values per strain beside it. The strips can hold ANI, BGC counts, domain counts, Mode B calls, assembly numbers or assay values. The tool only draws. It does not build a tree, align sequences, or run ANI, BGC, domain or Mode B analysis. See the [glossary](GLOSSARY.md) for terms.

It accepts three kinds of tree, and keeps them apart:

- `MLSA_PROTEIN5`: five protein-coding genes, built by `build_mlsa.py`.
- `MLSA_16S_SEPARATE`: a separate 16S tree.
- `CORE_GENOME_GTOTTREE_IQTREE`: a GToTree core-gene alignment, then IQ-TREE. The spelling `GTOTTREE` is exact.

It never forces two trees to agree. Closeness on the page does not show product identity, activity, horizontal transfer, direction of ancestry, or that two topologies match.

## What you need

- A finished tree in plain Newick with a semicolon at the end. Quoted labels are fine. Comments in square brackets are refused.
- The alignment that built the tree.
- Three small JSON receipts: tree workflow, model, seed.
- Four TSV files: the outgroup, the tip roster, the tip crosswalk, and the annotation matrix (formats below).
- The figures extra for plotting: `pip install ".[figures]"` from the program folder. See [install](INSTALL.md).

## Input files

Every file has a role. The config names each file once.

| Role | Content |
|---|---|
| `tree` | final Newick tree |
| `alignment` | the alignment used for that tree |
| `tree_workflow_receipt` | JSON with `tree_channel` and `tool` |
| `model_receipt` | JSON with `model` |
| `seed_receipt` | JSON with `seed` |
| `outgroup_roster` | TSV with a `newick_label` column and exactly one row, a tip that is in the tree |
| `final_tip_roster` | TSV: `newick_label`, `state`, `reason`. `state` is `INCLUDED` or `OMITTED`. Every row needs a reason. |
| `tip_crosswalk` | TSV: `newick_label`, `strain`, `display_label`, `role`, `genus` |
| `annotation_matrix` | TSV: `strain`, `channel`, `feature`, `value`, `state` |

Rules the tool enforces:

- The tree tips must equal the `INCLUDED` rows exactly. Nothing is inferred from name prefixes and no tip is dropped silently. `OMITTED` rows are written to a separate omission file.
- The crosswalk has one row for every roster row. Each `newick_label` and each `strain` appears once.
- Crosswalk `role` is `STUDY`, `REFERENCE`, `OUTGROUP` or `EXTERNAL_BENCHMARK`, in capitals. Exactly one row is `OUTGROUP`, and it is the outgroup roster tip. Other tree tools use lowercase roles. To convert a table from [display receipts](TREE_DISPLAY_RECEIPTS.md), map `query` to `STUDY`, `reference` to `REFERENCE` and `outgroup` to `OUTGROUP`.
- `channel` is one of `ANI`, `BGC`, `DOMAIN`, `MODE_B`, `ASSEMBLY`, `BIOASSAY`. Each `(strain, channel, feature)` appears once, and the strain must be in the crosswalk.
- `state` is `OBSERVED` (a finite number in `value`), or `MISSING`, `NOT_MEASURED`, `NOT_APPLICABLE` (blank `value`). A strain with no row for a feature is drawn as `MISSING`. The tool keeps these four states apart and never turns one into another. In the figure, an `OBSERVED` cell is colored by value; `MISSING` is a gray cell marked `?`; `NOT_MEASURED` is a white cell with a gray border marked `×`; `NOT_APPLICABLE` is a pale cell marked `–`. The key is printed under the tree. The plot-data table holds the same state names.

For assay values, use the [admitted selection](BIOASSAY_FIGURE_FACTORY.md#tree-and-mode-b-boundary) and give an exact tip crosswalk. Drawing a value does not admit raw assay data, pool experiments, or tie activity to a locus. A locus-level strip would have to carry the full `strain / full node-or-contig / region / BGC alias` identity. The tool does not build that.

## Write the config

Save this as `tree_figure.json`. The example has four tips, named `tipA`, `tipB`, `tipC` and `tipOut`. Replace the values with yours.

```json
{
  "schema_version": "sapote.tree-figure-factory.v1",
  "tree_channel": "MLSA_PROTEIN5",
  "annotation_scope": "STRAIN_AGGREGATE_ONLY",
  "external_data_root": "/path/to/data",
  "output_dir": "out",
  "figure_question": "How many BGC regions does each strain carry?",
  "inputs": [
    {"role": "tree", "logical_locator": "tree.nwk", "sha256": "<64 hex digits>"},
    {"role": "alignment", "logical_locator": "alignment.fasta", "sha256": "<64 hex digits>"},
    {"role": "tree_workflow_receipt", "logical_locator": "tree_workflow.json", "sha256": "<64 hex digits>"},
    {"role": "model_receipt", "logical_locator": "model.json", "sha256": "<64 hex digits>"},
    {"role": "seed_receipt", "logical_locator": "seed.json", "sha256": "<64 hex digits>"},
    {"role": "outgroup_roster", "logical_locator": "outgroup.tsv", "sha256": "<64 hex digits>"},
    {"role": "final_tip_roster", "logical_locator": "roster.tsv", "sha256": "<64 hex digits>"},
    {"role": "tip_crosswalk", "logical_locator": "crosswalk.tsv", "sha256": "<64 hex digits>"},
    {"role": "annotation_matrix", "logical_locator": "annotations.tsv", "sha256": "<64 hex digits>"}
  ],
  "methods": {
    "tool": "IQ-TREE",
    "model": "LG+G",
    "seed": "12345",
    "outgroup": "tipOut",
    "support": "ultrafast bootstrap",
    "source_release": "EXAMPLE release",
    "software_versions": "IQ-TREE 2.x"
  }
}
```

Field notes:

- The key is `schema_version`, not `schema`. `figure_question` is required and must not be empty.
- `external_data_root` is an absolute path to the folder that holds all nine files. Each `logical_locator` is a path inside that folder.
- `output_dir` must not exist yet. A relative path resolves from the folder that holds the config file.
- Fill each `sha256` from the file itself, in lowercase: `shasum -a 256 tree.nwk`. A wrong digest is refused.
- `tool`, `model` and `seed` in `methods` must equal the values in the three receipts. The example receipts are `{"tree_channel": "MLSA_PROTEIN5", "tool": "IQ-TREE"}`, `{"model": "LG+G"}` and `{"seed": 12345}`. The tool checks that these fields agree. It does not rerun the inference.

## Run it

```bash
python tools/tree_bgc_overlay.py --config /path/to/tree_figure.json
```

Success: exit code 0. The tool prints one line of JSON, the run receipt, and creates the `output_dir` folder. The receipt shows `"status": "PASS_ENGINEERING_CANDIDATE"`. That means the build finished, not that anyone accepted the science.

Failure: exit code 2. Nothing is written to `output_dir`. One line goes to standard error, starting `tree_bgc_overlay: REFUSED:` and naming the failed check, for example a digest mismatch or a tip missing from the roster.

## What you get

In `output_dir`:

- `tree_bgc_overlay_single_column` and `tree_bgc_overlay_double_column`, each as SVG and 300-DPI PNG.
- `tree_bgc_overlay_plotdata.tsv`, the plotted values, and `tree_bgc_overlay_omitted_tips.tsv`.
- `tree_bgc_overlay_caption_methods.json`, a caption and methods record that cites the hashes of every input.
- `tree_bgc_overlay_owner_notes.json`, notes that stay out of the printed caption.
- `tree_bgc_overlay_receipt.json`, which lists the hash of every file above.

The figure shows your tree's topology and branch lengths and your labels. It never pools channels. The tool refuses any tick label that touches the strip area. Open each figure at its intended print width and check the labels yourself. Keep the config and the receipts with the figure.
