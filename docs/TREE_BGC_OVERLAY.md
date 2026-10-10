# Tree annotation Figure Factory consumer

`tools/tree_bgc_overlay.py` is the publication-gated renderer for existing MLSA and
GToTree/IQ-TREE outputs. It is not a third phylogeny engine and does not run alignment, tree
inference, relabeling, ANI, BGC, domain, or Mode B analysis.

The accepted tree channels are deliberately separate:

- `MLSA_PROTEIN5` — the five protein-coding loci built by `build_mlsa.py`;
- `MLSA_16S_SEPARATE` — the separately extracted 16S evidence channel; and
- `CORE_GENOME_GTOTTREE_IQTREE` — the GToTree core-gene alignment followed by recorded IQ-TREE
  inference.

The renderer never forces agreement between these topologies. Visual proximity does not establish
product identity, activity, horizontal transfer, ancestry direction, or topology equivalence.

## Hash-bound interface

A `sapote.tree-figure-factory.v1` configuration binds exactly one file for every role below:

| Role | Required content |
|---|---|
| `tree` | final canonical Newick tree |
| `alignment` | the exact alignment used for that tree |
| `tree_workflow_receipt` | JSON carrying matching `tree_channel` and `tool` |
| `model_receipt` | JSON carrying the selected `model` |
| `seed_receipt` | JSON carrying the exact `seed` |
| `outgroup_roster` | TSV with exactly one included `newick_label` |
| `final_tip_roster` | TSV: `newick_label`, `state`, `reason`; state is `INCLUDED` or `OMITTED` |
| `tip_crosswalk` | TSV: `newick_label`, `strain`, `display_label`, `role`, `genus` |
| `annotation_matrix` | adapter-owned TSV: `strain`, `channel`, `feature`, `value`, `state` |

Every locator is relative to a configured data root and every input carries an exact lowercase
SHA-256. Crosswalk labels and strains are each one-to-one; duplicates refuse. Crosswalk rows cover
the complete final roster, while tree tips must equal the `INCLUDED` roster exactly. There is no
prefix inference and no silent tip dropping. `OMITTED` rows travel in a typed omission receipt.

The accepted strain-aggregate annotation channels are `ANI`, `BGC`, `DOMAIN`, `MODE_B`,
`ASSEMBLY` and `BIOASSAY`. For assay values, use the
[admitted Figure Factory selection](BIOASSAY_FIGURE_FACTORY.md#tree-and-mode-b-boundary),
retain target/material/time/dose/aggregation receipts, and supply an exact tree-tip
crosswalk. Drawing the supplied BIOASSAY value does not admit raw assay data, pool
experiments or attribute activity to a locus. It owns all domain semantics and exact-locus validation; the renderer does not
reconstruct inventories or judgments. A locus-specific future adapter must carry the complete
`strain / full node-or-contig / region / BGC alias` identity and fail if any part is unavailable.

## Build the explicit configuration

Invoke the renderer from the selected bundle environment after the input tree and
annotations are prepared:

```bash
python tools/tree_bgc_overlay.py --config /path/to/tree_figure.json
```

The JSON uses `schema_version`, not `schema`. Required top-level fields are:

| Field | Required value or shape |
|---|---|
| `schema_version` | `sapote.tree-figure-factory.v1` |
| `tree_channel` | One of the three exact channel names above; retain the shipped `GTOTTREE` spelling |
| `annotation_scope` | `STRAIN_AGGREGATE_ONLY` |
| `external_data_root` | Explicit existing data root for all bound input locators |
| `output_dir` | New output directory; relative paths resolve from the config file, not the input root |
| `inputs` | Nine objects, exactly one for each role above; each contains `role`, `logical_locator`, `sha256` |
| `methods` | Nonempty `tool`, `model`, `seed`, `outgroup`, `support`, `source_release`, `software_versions` |

Each `logical_locator` is a relative file path contained in `external_data_root`.
Each `sha256` binds actual bytes, not an example digest. The workflow/model/seed
receipts must agree with the corresponding `methods` values. The renderer checks
those supplied fields; it does not reconstruct or independently verify the inference.

Crosswalk roles are exactly `STUDY`, `REFERENCE`, `OUTGROUP` or `EXTERNAL_BENCHMARK`.
This differs from the lowercase `query/reference/outgroup` roles used by other
tree consumers; perform an explicit schema adaptation instead of copying a table
unchanged. A crosswalk row needs all five columns and a distinct strain value.

Annotation keys are unique `(strain, channel, feature)` tuples. `OBSERVED` requires
a finite numeric value. `MISSING`, `NOT_MEASURED` and `NOT_APPLICABLE` require a blank
value. An annotation strain outside the included tree roster refuses. These rules
check transport and typed missingness; the upstream adapter owns biological semantics.

The figures extra is needed for matplotlib rendering. A fresh output is required;
existing output directories are refused. Keep the configuration, source receipts
and emitted `tree_bgc_overlay_receipt.json` with the artwork, then inspect the actual
figure at its intended reading width before claiming visual review.

## Output contract

The renderer transactionally writes:

- live-text, vector-geometry SVG and native 300-DPI PNG at both single- and double-column widths;
- deterministic recorded topology, branch lengths, support labels, and explicit display labels;
- accessible, channel-distinct annotation cells without cross-channel normalization or pooling;
- exact plot-data and omitted-tip TSV receipts;
- a dynamic caption/method JSON binding tree, alignment, tool, model, seed, outgroup, roster,
  crosswalk, and annotation hashes;
- separate owner-notes metadata that is not printed as a scientific caption; and
- a complete output/hash receipt.

At each declared publication width, every visible annotation-track x-axis tick label is measured
after the final layout pass and must be disjoint from the annotation axes data rectangle. A label
that touches or enters the data region is a hard refusal even when no two labels collide.

Canonical IQ-TREE Newick with quoted labels is accepted. Comments or extended annotation syntax are
refused so unsupported Newick cannot be misrendered. Any later PDF compilation must preserve the SVG
as vector artwork or pass the native-pixel fallback gate, then verify physical-width text legibility.

This renderer is candidate engineering only. A green render does not sign off the tree, reconcile
MLSA with core-genome topology, accept annotations scientifically, select a product, or authorize a
release.
